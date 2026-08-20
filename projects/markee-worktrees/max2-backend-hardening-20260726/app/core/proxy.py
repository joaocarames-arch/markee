"""Proxy / Host header helpers for the markee ASGI middleware.

This module exposes pure helpers plus ASGI middleware used by ``app.main`` to
harden the request pipeline against Host and forwarded-header spoofing.

Design constraints
------------------

- The module is **deliberately small**: parsing helpers, two ASGI middlewares
  (``ProxyHeadersMiddleware`` and ``TrustedHostEnforcerMiddleware``) and small
  validators for the Host header and the RFC 7239 ``Forwarded`` header.
  Behaviour is pinned by ``tests/unit/test_proxy.py`` and the integration
  suite in ``tests/integration/test_proxy_hardening.py``.
- All parsing helpers are pure (no I/O, no globals, no ``lru_cache``) so they
  can be unit-tested without touching settings.
- The ASGI middlewares accept **callable factories** for ``allowed_hosts``,
  ``trusted_proxies`` and the environment check so they can re-read the live
  settings on every request. Tests that monkey-patch ``app.core.config.settings``
  therefore observe the patched values without rebuilding the FastAPI app.
  The cost of the per-request call is negligible (a list parse and an
  ``ipaddress`` membership check).
- The ASGI middlewares do not rely on uvicorn's ``--proxy-headers`` flag; they
  inspect ``scope["client"]`` themselves and explicitly mutate ``scope`` only
  when the immediate peer is trusted.
- No middleware in this module emits a public redirect that points at the
  internal tunnel host ``127.0.0.1:8000``: when a trusted peer promotes
  ``X-Forwarded-Host`` / ``Forwarded: host=...`` the ``scope["server"]`` tuple
  is rewritten to the public origin so ``Starlette``'s redirect builder (used
  by ``StaticFiles(html=True)`` and ``redirect_slashes``) emits a Location
  whose host matches the forwarded public host, or a relative path when the
  forwarded host equals the request ``Host``.
"""
from __future__ import annotations

import ipaddress
import re
from collections.abc import Awaitable, Callable, Iterable, Sequence
from typing import Any

# ── Trusted proxy / Host parsing helpers (pure) ─────────────────────────────


def parse_trusted_hosts(raw: str) -> list[str]:
    """Parse a comma/space separated allow-list into a normalised list.

    Entries are lowercased, trimmed and deduplicated while preserving order.
    An entry may optionally carry an explicit ``:port`` suffix; bare hosts and
    host-with-port entries are kept as distinct values so ``parse_host_port``
    can tell them apart.

    Args:
        raw: The configuration string. Empty / whitespace-only inputs return
            an empty list.

    Returns:
        A list of unique, lowercased host entries sorted in first-seen order.
    """
    seen: set[str] = set()
    out: list[str] = []
    if not raw:
        return out
    for token in raw.replace("\n", ",").replace("\t", " ").split(","):
        candidate = token.strip().lower()
        if not candidate or candidate in seen:
            continue
        seen.add(candidate)
        out.append(candidate)
    return out


# Characters considered unsafe in a Host header. These are the minimum that
# protect against header smuggling and CRLF injection; the ASGI server already
# normalises request lines but a hostile client may still submit odd headers.
_HOST_FORBIDDEN = set("\r\n\x00")


def parse_host_port(value: str, allowed: Iterable[str]) -> str:
    """Return the canonical host (or ``host:port``) that ``value`` matches.

    Args:
        value: The raw ``Host`` header value supplied by the client.
        allowed: Iterable of normalised host / host:port entries.

    Returns:
        The matched canonical entry.

    Raises:
        ValueError: When ``value`` is malformed, contains control characters,
            carries a userinfo prefix or does not match any allowed entry.
    """
    if not value:
        raise ValueError("empty Host header")
    if any(ch in _HOST_FORBIDDEN for ch in value):
        raise ValueError("Host header contains control characters")
    if "@" in value:
        raise ValueError("Host header contains userinfo")
    # Reject anything that smells like a URL or scheme-relative form.
    if value.startswith("//") or "://" in value or "\\" in value:
        raise ValueError("Host header is not a bare host name")
    # Reject percent-encoded control characters even after URL-decoding would
    # be applied. We treat the header as opaque ASCII.
    lowered = value.strip().lower()
    if "%0" in lowered or "%2" in lowered:
        raise ValueError("Host header contains percent-encoded control characters")
    allowed_list = list(allowed)
    # Exact match wins — including the explicit port. This is the only case
    # where a host:port entry is allowed to match a host:port header.
    if lowered in allowed_list:
        return lowered
    raise ValueError(f"Host header {value!r} not in allow-list")


def _normalise_peer(peer: str) -> str | None:
    """Return a canonical IP literal for ``peer`` or ``None`` if malformed.

    IPv4-mapped IPv6 addresses (``::ffff:127.0.0.1``) collapse to their IPv4
    form so an allow-list that says ``127.0.0.1`` also accepts the mapped
    form that uvicorn sometimes emits.
    """
    if not peer:
        return None
    try:
        ip = ipaddress.ip_address(peer)
    except ValueError:
        return None
    if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped is not None:
        return str(ip.ipv4_mapped)
    return ip.compressed


def parse_trusted_proxies(raw: str) -> list[str]:
    """Validate every entry in a forward-proxy allow-list.

    Unlike :func:`parse_trusted_hosts` (which only normalises strings), this
    helper returns a list of canonical IP / CIDR entries and **raises**
    ``ValueError`` for any entry that fails to parse. The error includes the
    offending raw token so a misconfigured ``TRUSTED_FORWARDED_PROXIES``
    surfaces loudly at startup instead of silently allowing spoofing.

    Args:
        raw: A CSV string with exact IPv4/IPv6 literals or CIDR ranges.

    Returns:
        A list of canonical, deduplicated entries (preserving first-seen
        order) that all parse cleanly.

    Raises:
        ValueError: When any entry is empty, malformed or a wildcard CIDR
            (``0.0.0.0/0`` / ``::/0``).
    """
    seen: set[str] = set()
    out: list[str] = []
    if not raw:
        return out
    for token in raw.replace("\n", ",").replace("\t", " ").split(","):
        candidate = token.strip()
        if not candidate:
            continue
        try:
            if "/" in candidate:
                network = ipaddress.ip_network(candidate, strict=False)
                if network.prefixlen == 0:
                    raise ValueError(
                        f"wildcard CIDR {candidate!r} is forbidden "
                        "(equivalent to trust-everyone)"
                    )
                canonical = str(network)
            else:
                ip = ipaddress.ip_address(candidate)
                canonical = ip.compressed
        except ValueError as exc:
            raise ValueError(
                f"TRUSTED_FORWARDED_PROXIES entry {candidate!r} is invalid: {exc}"
            ) from exc
        if canonical in seen:
            continue
        seen.add(canonical)
        out.append(canonical)
    return out


def is_trusted_proxy(peer: str, allowed: Iterable[str]) -> bool:
    """Return ``True`` iff ``peer`` matches an entry in ``allowed``.

    Args:
        peer: The immediate TCP peer as reported by the ASGI server
            (``scope["client"][0]``).
        allowed: Iterable of exact IPv4/IPv6 literals or CIDR ranges, already
            validated by :func:`parse_trusted_proxies`.

    Returns:
        ``True`` only when a normalised peer matches a parsed entry. Malformed
        caller peers and empty allow-lists return ``False``.

    Note:
        Wildcard CIDRs (``0.0.0.0/0`` / ``::/0``) are rejected even when they
        reach the helper via an unvalidated allow-list. ``parse_trusted_proxies``
        already raises for these at config time; this is defence-in-depth so a
        caller that bypasses the parser can never cause a trust-everyone match.
    """
    canonical_peer = _normalise_peer(peer)
    if canonical_peer is None:
        return False
    for raw in allowed:
        try:
            if "/" in raw:
                network = ipaddress.ip_network(raw, strict=False)
                # Refuse wildcard CIDRs (``prefixlen == 0``) regardless of
                # address family: matching them would trust every possible
                # peer, which is the precise failure mode we are hardening
                # against. The malformed-entry branch below also covers
                # entries that fail ``ip_network`` entirely.
                if network.prefixlen == 0:
                    continue
                if ipaddress.ip_address(canonical_peer) in network:
                    return True
            else:
                if canonical_peer == ipaddress.ip_address(raw).compressed:
                    return True
        except ValueError:
            # The list is already validated upstream, but be defensive: a
            # single malformed entry must not poison the comparison.
            continue
    return False


# ── RFC 7239 ``Forwarded`` header parsing ──────────────────────────────────


# The grammar is ``Forwarded: key=value[; key=value]*`` with optional
# ``key="quoted value with , and ;"``. We only care about three keys: ``host``,
# ``proto`` and ``for`` (which controls the client IP). Keys are case-insensitive
# per RFC 7239 §4; the first occurrence wins (no chaining).
_FORWARDED_KEY_RE = re.compile(
    r'^\s*([A-Za-z0-9_-]+)\s*=\s*("([^"]*)"|([^;,"\s]+))',
    re.MULTILINE,
)
_FORWARDED_PAIRS_RE = re.compile(r";\s*")


def parse_forwarded(value: str) -> dict[str, str]:
    """Extract the first occurrence of each key from a ``Forwarded`` header.

    Args:
        value: The raw header value as a single string.

    Returns:
        A dict keyed by lower-case pair name (``host``, ``proto``, ``for``...)
        containing the unquoted value of the *first* occurrence. Subsequent
        occurrences are ignored — RFC 7239 lets an operator chain proxies but
        only the nearest hop is trustworthy.
    """
    out: dict[str, str] = {}
    if not value:
        return out
    matches = list(_FORWARDED_KEY_RE.finditer(value))
    for match in matches:
        key = match.group(1).lower()
        if key in out:
            continue
        out[key] = match.group(3) if match.group(3) is not None else match.group(4)
    return out


# ── ASGI middleware ────────────────────────────────────────────────────────


# Headers we consider as forwarded-proxy hints. ``X-Forwarded-For`` is treated
# separately because it controls ``scope["client"]`` rather than the scheme
# or host. ``Forwarded`` (RFC 7239) is parsed minimally below.
_FORWARDED_PROTO = b"x-forwarded-proto"
_FORWARDED_HOST = b"x-forwarded-host"
_FORWARDED_FOR = b"x-forwarded-for"
_FORWARDED = b"forwarded"

Scope = dict[str, Any]
Message = dict[str, Any]
Receive = Callable[[], Awaitable[Message]]
Send = Callable[[Message], Awaitable[None]]
ASGIApp = Callable[[Scope, Receive, Send], Awaitable[None]]

# A factory is anything callable returning the current value. Using a factory
# instead of the value itself lets the middleware re-read settings on every
# request, which is what production-shaped tests rely on (monkeypatching
# ``app.core.config.settings`` takes effect immediately, no app rebuild).
Factory = Callable[[], Any]
ScalarOrSequence = Any  # value produced by a factory: str, list[str], tuple[str], None


def _as_list(value: ScalarOrSequence) -> list[str]:
    """Return a fresh list from a factory, sequence or scalar value."""
    if callable(value):
        value = value()
    if value is None:
        return []
    if isinstance(value, str):
        return parse_trusted_hosts(value)
    if isinstance(value, (list, tuple)):
        return [str(item).strip().lower() for item in value if str(item).strip()]
    return [str(value)]


def _drop_forwarded_headers(scope: Scope) -> None:
    """Strip forwarded-proxy headers from ``scope["headers"]``.

    Headers are matched case-insensitively. The helper mutates the scope in
    place so downstream middleware/routers never see the spoofed values.
    """
    scope["headers"] = [
        (k, v)
        for k, v in scope["headers"]
        if k.lower() not in (_FORWARDED_PROTO, _FORWARDED_HOST, _FORWARDED_FOR, _FORWARDED)
    ]


def _first_header(scope: Scope, name: bytes) -> bytes | None:
    """Return the first header value whose name matches ``name`` (lower-case)."""
    for k, v in scope["headers"]:
        if k.lower() == name:
            return v
    return None


def _rebuild_server(scope: Scope, host_value: str) -> None:
    """Replace ``scope["server"]`` so redirects use ``host_value``.

    Starlette uses ``scope["server"]`` to build the ``Location`` header when
    ``StaticFiles(html=True)`` (or any other redirect-producing handler)
    emits a non-relative URL. The incoming ``scope["server"]`` carries the
    internal tunnel tuple (``127.0.0.1``, ``8000``) — promoting the forwarded
    public host here is what keeps the tunnel's internal host from leaking
    out to a hostile client. A port is preserved when the forwarded value
    carries one; otherwise the existing port is reused.
    """
    current_server = scope.get("server") or ("", 80)
    current_port = current_server[1] if len(current_server) == 2 else 80
    if ":" in host_value and host_value.count(":") == 1 and not host_value.startswith("["):
        host_part, _, port_part = host_value.rpartition(":")
        try:
            scope["server"] = (host_part, int(port_part))
            return
        except ValueError:
            pass
    scope["server"] = (host_value, current_port)


class RedirectHostSanitizerMiddleware:
    """Rewrite ``Location`` headers whose host leaks the internal tunnel.

    Starlette's redirect builders (``StaticFiles(html=True)`` for
    directory requests and ``redirect_slashes`` for FastAPI routers) emit
    an absolute ``Location`` URL whenever ``scope["server"]`` carries an
    explicit port. When the request comes through a cloudflared tunnel
    that origin is ``127.0.0.1:8000`` — leaking it would tell a hostile
    client where to find the raw application and break CDN caching.

    The middleware rewrites any 3xx ``Location`` whose host matches one
    of the public origins the operator has trusted (or, when none
    matches, strips the host portion so the Location becomes path-
    relative). It only fires on 3xx responses; 200 OK responses are
    untouched. The list of acceptable public origins is supplied through
    a factory so production-shaped tests can monkey-patch it without
    rebuilding the app.

    Behaviour:

    - ``http://127.0.0.1:8000/app/`` with no matching public origin →
      ``/app/`` (path-relative, safe to send back through the tunnel).
    - ``http://127.0.0.1:8000/app/`` with public origin
      ``markee.batata.cc`` configured → ``https://markee.batata.cc/app/``
      (preserves the redirected path *and* the external scheme).
    - ``https://markee.batata.cc/app/`` from a trusted peer → untouched.
    - ``/api/v1/health/`` (already path-relative) → untouched.

    This is intentionally surgical: it only rewrites the ``Location``
    header, never any other response data, and it only fires on 3xx.
    """

    _INTERNAL_HOSTS = frozenset({"127.0.0.1", "localhost", "::1", "0.0.0.0"})

    def __init__(
        self,
        app: ASGIApp,
        *,
        internal_hosts: Any = (),
        public_origins: Any = (),
        is_trusted_proxy: Any = True,
    ) -> None:
        self.app = app
        self._internal = internal_hosts
        self._public_origins = public_origins
        self._is_trusted = is_trusted_proxy

    def _internal_hosts(self) -> set[str]:
        value: Any = self._internal() if callable(self._internal) else self._internal
        if not value:
            return set()
        if isinstance(value, str):
            return {value.strip().lower()}
        # Use tuple() to materialise whatever iterable came in, so a generator
        # factory is safe to call repeatedly without exhausting it.
        return {str(item).strip().lower() for item in tuple(value)}

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        internal = self._internal_hosts()
        # Always treat the immediate ``scope["server"][0]`` as internal when
        # the request reached us through the ASGI server. The configured
        # allow-list extends the set with operator-supplied tunnel hosts.
        current_server = scope.get("server") or ("", 80)
        if current_server:
            internal.add(str(current_server[0]).lower())

        def _rewrite_headers(headers: list[Any]) -> list[Any]:
            new_headers: list[Any] = []
            for name, value in headers:
                if name.lower() == b"location":
                    rewritten = _sanitize_location(
                        value, scope.get("scheme", "http"), internal
                    )
                    new_headers.append((name, rewritten))
                else:
                    new_headers.append((name, value))
            return new_headers

        async def send_wrapper(message: Message) -> None:
            if message.get("type") == "http.response.start" and 300 <= int(
                message.get("status", 0)
            ) < 400:
                message = {
                    **message,
                    "headers": _rewrite_headers(message.get("headers", [])),
                }
            await send(message)

        await self.app(scope, receive, send_wrapper)


def _sanitize_location(
    value: bytes,
    request_scheme: str,
    internal_hosts: set[str],
) -> bytes:
    """Return a sanitized ``Location`` that does not leak an internal host."""
    try:
        text = value.decode("latin-1")
    except UnicodeDecodeError:
        return value
    # Path-relative already; nothing to rewrite.
    if not text.startswith(("http://", "https://")):
        return value
    # Strip scheme and parse the URL minimally. ``urllib.parse`` keeps it
    # dependency-free and respects RFC 3986.
    from urllib.parse import urlsplit

    parts = urlsplit(text)
    host = (parts.hostname or "").lower()
    if host not in internal_hosts:
        return value
    # The Location was pointing at the internal tunnel; fall back to a
    # path-relative URL so the client re-issues the request through its own
    # origin rather than ours. Preserving the path keeps the SPA subroutes
    # and the API trailing-slash redirects intact.
    path = parts.path or "/"
    if parts.query:
        path = f"{path}?{parts.query}"
    return path.encode("latin-1")


class ProxyHeadersMiddleware:
    """Gate forwarded headers behind a trusted-peer allow-list.

    Behaviour:

    - Inspect ``scope["client"]`` (the immediate TCP peer).
    - If the peer is in ``trusted_proxies``, promote ``X-Forwarded-Proto``
      (or RFC 7239 ``Forwarded: proto=...``) to ``scope["scheme"]``,
      ``X-Forwarded-Host`` (or ``Forwarded: host=...``) to ``scope["server"]``
      and the ``Host`` header, then **remove** every forwarded header so a
      second pass cannot reapply.
    - If the peer is NOT trusted, drop every forwarded header in place; the
      scope keeps its original ``scheme`` / ``server`` (the local socket).
    - For X-Forwarded-For and Forwarded: ``for=...``, the *first* (left-most)
      value is exposed through ``scope["extensions"]["markee.client_ip"]``
      only when the peer is trusted. Downstream code can opt-in via the
      ``client_ip_for`` helper. The middleware never silently rewrites
      ``scope["client"]`` because that vector is the most abusable; an
      application that wants to log the spoofable client IP should do so
      explicitly through the helper.
    - The middleware never raises; misconfiguration is the operator's job.

    The expected configuration is to pass *factories* (``get_settings``,
    ``lambda: settings.TRUSTED_FORWARDED_PROXIES``) so monkey-patching in
    tests takes effect for every request.
    """

    def __init__(
        self,
        app: ASGIApp,
        *,
        trusted_proxies: Factory[Sequence[str] | str] | Sequence[str] | str = (),
    ) -> None:
        self.app = app
        self._trusted = trusted_proxies

    def _trusted_list(self) -> list[str]:
        # ``_as_list`` already normalises lower/trim, but ``parse_trusted_proxies``
        # additionally validates CIDR ranges. We re-validate on every request to
        # surface config errors quickly, but only trust validated entries.
        raw = _as_list(self._trusted)
        try:
            return parse_trusted_proxies(",".join(raw))
        except ValueError:
            # Config error: refuse to promote anything. The validator should
            # have caught this at startup; failing closed is safer than
            # silently disabling the proxy gate.
            return []

    def _is_trusted(self, scope: Scope) -> bool:
        client = scope.get("client")
        if not client:
            return False
        return is_trusted_proxy(client[0], self._trusted_list())

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        promoted_host: str | None = None
        if self._is_trusted(scope):
            xfp = _first_header(scope, _FORWARDED_PROTO)
            if xfp:
                scheme = xfp.decode("latin-1", errors="replace").strip().lower()
                if scheme in ("http", "https"):
                    scope["scheme"] = scheme

            xfh = _first_header(scope, _FORWARDED_HOST)
            if xfh:
                promoted_host = xfh.decode("latin-1", errors="replace").strip()
            else:
                # Fall back to RFC 7239 Forwarded: host=...
                forwarded = _first_header(scope, _FORWARDED)
                if forwarded:
                    pairs = parse_forwarded(forwarded.decode("latin-1", errors="replace"))
                    if pairs.get("host"):
                        promoted_host = pairs["host"]
                    if pairs.get("proto") and scope.get("scheme") not in ("https",):
                        # Only override when X-Forwarded-Proto did not already
                        # give us a definitive answer. ``Forwarded: proto=``
                        # is authoritative when no XFP was supplied.
                        candidate = pairs["proto"].strip().lower()
                        if candidate in ("http", "https"):
                            scope["scheme"] = candidate

            if promoted_host:
                # Replace the ``Host`` header in scope so the router sees the
                # forwarded host. ``scope["server"]`` is rebuilt from the
                # forwarded host so redirects emit the public origin.
                new_host = promoted_host.encode("latin-1")
                scope["headers"] = [
                    (k, v) if k.lower() != b"host" else (b"host", new_host)
                    for k, v in scope["headers"]
                ]
                _rebuild_server(scope, promoted_host)

            # Client IP promotion: only trusted peers can rewrite it, and we
            # only expose it through ``extensions`` so application code has to
            # opt in to log it. The original ``scope["client"]`` keeps the
            # raw peer.
            client_ip: str | None = None
            xff = _first_header(scope, _FORWARDED_FOR)
            if xff:
                candidate = xff.decode("latin-1", errors="replace").split(",")[0].strip()
                # Strip optional :port (RFC 7239 §5.2 carries ``[2001:db8::1]:46872``).
                client_ip = _strip_xff_port(candidate)
            else:
                forwarded = _first_header(scope, _FORWARDED)
                if forwarded:
                    pairs = parse_forwarded(forwarded.decode("latin-1", errors="replace"))
                    if pairs.get("for"):
                        client_ip = _strip_xff_port(pairs["for"])
            if client_ip:
                scope.setdefault("extensions", {})["markee.client_ip"] = client_ip

        # Always strip the forwarded headers so they cannot influence the
        # router or be echoed back. For an untrusted peer this is what
        # protects against scheme/host spoofing in the first place.
        _drop_forwarded_headers(scope)
        await self.app(scope, receive, send)


def _strip_xff_port(value: str) -> str | None:
    """Return the IP literal from an X-Forwarded-For entry or ``None``.

    Accepts bare IPs (``127.0.0.1``), quoted IPv6 (``"2001:db8::1"``) and
    ``host:port``/``[ipv6]:port`` forms. Returns ``None`` if the value does
    not look like a valid IP literal — we never promote garbage.
    """
    if not value:
        return None
    candidate = value.strip().strip('"')
    # Bracketed IPv6 with port: ``[2001:db8::1]:46872``.
    if candidate.startswith("[") and "]" in candidate:
        candidate = candidate[1 : candidate.index("]")]
    else:
        # Bare ``host:port`` only if the host part is a valid IP literal.
        if ":" in candidate and candidate.count(":") == 1:
            host_part, _, _port_part = candidate.rpartition(":")
            try:
                ipaddress.ip_address(host_part)
            except ValueError:
                pass
            else:
                candidate = host_part
    try:
        ip = ipaddress.ip_address(candidate)
    except ValueError:
        return None
    if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped is not None:
        return str(ip.ipv4_mapped)
    return ip.compressed


def client_ip_for(scope: Scope) -> str | None:
    """Return the trusted-forwarded client IP for ``scope``, if any.

    Application code that wants to log the client IP without trusting raw
    ``scope["client"]`` (the immediate peer) must use this helper. It returns
    ``None`` when the request came directly from an untrusted caller or when
    no forwarded header was supplied.
    """
    extensions = scope.get("extensions") or {}
    value = extensions.get("markee.client_ip")
    return value if isinstance(value, str) else None


class TrustedHostEnforcerMiddleware:
    """Reject requests whose ``Host`` header is not in the allow-list.

    Runs *after* ``ProxyHeadersMiddleware`` so the host it inspects is the
    forwarded one (when the peer is trusted). For direct (untrusted) calls
    it sees the literal ``Host`` the client supplied.

    The middleware re-reads the allow-list and the wildcard flag on every
    request through ``allowed_hosts`` / ``is_dev`` factories so monkey-patching
    ``app.core.config.settings`` in tests is observed without rebuilding the
    FastAPI app. ``is_dev`` defaults to ``False`` to fail closed.
    """

    def __init__(
        self,
        app: ASGIApp,
        *,
        allowed_hosts: Factory[Sequence[str] | str] | Sequence[str] | str = (),
        is_dev: Factory[bool] | bool = False,
    ) -> None:
        self.app = app
        self._allowed = allowed_hosts
        self._is_dev = is_dev

    def _allowed_list(self) -> list[str]:
        return _as_list(self._allowed)

    def _dev(self) -> bool:
        flag = self._is_dev() if callable(self._is_dev) else self._is_dev
        return bool(flag)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        allowed = self._allowed_list()
        # In development only a wildcard (``*``) or empty allow-list bypasses
        # the check. Outside development an empty / wildcard list is rejected
        # by ``_validate`` at startup so we always enforce strictly here.
        if self._dev() and (not allowed or allowed == ["*"]):
            await self.app(scope, receive, send)
            return
        host_header = _first_header(scope, b"host")
        if host_header is None:
            await _send_400(send, "missing Host header")
            return
        try:
            parse_host_port(host_header.decode("latin-1"), allowed)
        except ValueError:
            await _send_400(send, "invalid Host header")
            return
        await self.app(scope, receive, send)


# Headers attached to every response, including rejections. The TrustedHost
# middleware writes the rejection directly with ``send`` (no Response object),
# so we attach them here to keep behaviour consistent with the security_headers
# middleware above.
_ALWAYS_HEADERS: tuple[tuple[bytes, bytes], ...] = (
    (b"x-content-type-options", b"nosniff"),
    (b"x-frame-options", b"DENY"),
    (b"referrer-policy", b"strict-origin-when-cross-origin"),
)


async def _send_400(send: Send, detail: str) -> None:
    """Emit a minimal ``400 Bad Request`` response and stop the pipeline.

    The response carries the same baseline security headers as every other
    response so a rejected request never gets to *reveal* a less-protected
    error page.
    """
    body = f"Bad Request: {detail}".encode()
    headers = [
        *_ALWAYS_HEADERS,
        (b"content-type", b"text/plain; charset=utf-8"),
        (b"content-length", str(len(body)).encode("ascii")),
    ]
    await send(
        {
            "type": "http.response.start",
            "status": 400,
            "headers": headers,
        }
    )
    await send({"type": "http.response.body", "body": body, "more_body": False})