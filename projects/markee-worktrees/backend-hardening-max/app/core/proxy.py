"""Trust-boundary helpers for the production proxy surface.

These helpers are pure functions over small data, deliberately framework-free
so they can be tested without ASGI, without a request, and without the
settings cache. They encode the rules the FastAPI middleware consults at
runtime to decide whether a peer is trusted, what external scheme/host to
derive, and how to format a Location header that never leaks an internal
endpoint to the browser.

The deployment topology the helpers target is documented in
``docs/execution/STG-00_CONTAINMENT_AUDIT.md``:

* ``cloudflared`` listens on the public edge and forwards to
  ``http://127.0.0.1:8000`` for ``markee.batata.cc`` and
  ``app.markee.batata.cc``.
* ``httpHostHeader: 127.0.0.1:8000`` is the host header the proxy injects —
  the application therefore sees ``Host: 127.0.0.1:8000`` on the socket.
* The peer TCP address is the local cloudflared process, which lives on
  ``127.0.0.1`` (or ``::1``).

The trust boundary is therefore "this single socket, controlled by the
process running next to the app" — anything else is untrusted.
"""
from __future__ import annotations

import ipaddress
from typing import Iterable, Sequence


def parse_trusted_hosts(
    raw: Sequence[str] | Iterable[str],
    *,
    allow_wildcard: bool = False,
) -> tuple[tuple[str, int | None], ...]:
    """Parse a list of trusted Host rules into a tuple of (host, port|None).

    Args:
        raw: Strings accepted as ``host``, ``host:port``, or ``[ipv6]:port``.
        allow_wildcard: When True, accepts ``"*"`` (development only). When
            False (the production default), ``"*"`` is rejected.

    Returns:
        A tuple of exact-match rules. The caller compares a request's
        ``Host`` header against each rule; only a precise ``(host, port)``
        match counts as trusted.

    Raises:
        ValueError: If the list is empty, contains malformed entries, or
            includes ``"*"`` while ``allow_wildcard`` is False.
    """
    items = list(raw)
    if not items:
        raise ValueError("trusted hosts list is empty")
    out: list[tuple[str, int | None]] = []
    for entry in items:
        if not isinstance(entry, str):
            raise ValueError(f"trusted host entry must be a string, got {type(entry).__name__}")
        host = entry.strip()
        if not host:
            raise ValueError("trusted host entry is empty")
        if host == "*":
            if not allow_wildcard:
                raise ValueError("wildcard '*' is not allowed in trusted hosts")
            out.append(("*", None))
            continue
        port: int | None = None
        # IPv6 with bracket: [::1]:8000
        if host.startswith("["):
            closing = host.find("]")
            if closing == -1:
                raise ValueError(f"trusted host missing ']': {host!r}")
            host_part = host[1:closing]
            tail = host[closing + 1 :]
            if tail:
                if not tail.startswith(":"):
                    raise ValueError(f"trusted host malformed IPv6 tail: {host!r}")
                port = _parse_port(tail[1:])
        elif host.count(":") == 1:
            host_part, sep, port_str = host.partition(":")
            if sep:
                port = _parse_port(port_str)
        else:
            host_part = host
        if len(host_part) > 253:
            raise ValueError(f"trusted host exceeds 253 chars: {host_part!r}")
        if not host_part:
            raise ValueError(f"trusted host empty hostname: {entry!r}")
        out.append((host_part.lower(), port))
    return tuple(out)


def _parse_port(raw: str) -> int:
    raw = raw.strip()
    if not raw.isdigit():
        raise ValueError(f"trusted host port is not numeric: {raw!r}")
    port = int(raw)
    if not (1 <= port <= 65535):
        raise ValueError(f"trusted host port out of range: {port}")
    return port


def parse_trusted_proxies(
    raw: Sequence[str] | Iterable[str],
) -> tuple[ipaddress._BaseNetwork | ipaddress._BaseAddress, ...]:
    """Parse a list of trusted peer IPs/CIDRs.

    Accepts either a single IP (``127.0.0.1``, ``::1``) or a CIDR
    (``127.0.0.1/32``, ``::1/128``). Hostnames are rejected outright — the
    trust boundary is the concrete TCP peer, not a DNS name.

    ``0.0.0.0/0`` and ``::/0`` are rejected because they would trust every
    peer on the internet and defeat the boundary.

    Args:
        raw: Strings of trusted peer IPs/CIDRs.

    Returns:
        A tuple of ``ipaddress`` rules.

    Raises:
        ValueError: If the list is empty, contains hostnames, malformed
            CIDRs, or wildcard prefixes.
    """
    items = list(raw)
    if not items:
        raise ValueError("trusted proxies list is empty")
    out: list[ipaddress._BaseNetwork | ipaddress._BaseAddress] = []
    for entry in items:
        if not isinstance(entry, str):
            raise ValueError(f"trusted proxy entry must be a string, got {type(entry).__name__}")
        candidate = entry.strip()
        if not candidate:
            raise ValueError("trusted proxy entry is empty")
        # Single IP literal
        if "/" in candidate:
            try:
                net = ipaddress.ip_network(candidate, strict=False)
            except ValueError as exc:
                raise ValueError(f"trusted proxy CIDR is malformed: {candidate!r}") from exc
            if net.prefixlen == 0:
                raise ValueError(f"trusted proxy CIDR covers 0.0.0.0/0: {candidate!r}")
            out.append(net)
        else:
            try:
                addr = ipaddress.ip_address(candidate)
            except ValueError as exc:
                raise ValueError(
                    f"trusted proxy entry must be IP or CIDR, not hostname: {candidate!r}"
                ) from exc
            out.append(addr)
    return tuple(out)


def is_trusted_peer(
    peer: str | None,
    rules: Sequence[ipaddress._BaseNetwork | ipaddress._BaseAddress],
) -> bool:
    """Return True when ``peer`` belongs to any of the trusted rules.

    The peer is the real TCP socket address (``request.client.host``). It is
    never the ``X-Forwarded-For`` header value — that header is data, not
    trust.
    """
    if peer is None:
        return False
    try:
        addr = ipaddress.ip_address(peer)
    except ValueError:
        return False
    for rule in rules:
        if isinstance(rule, ipaddress._BaseNetwork):
            if addr in rule:
                return True
        else:  # single IP literal
            if addr == rule:
                return True
    return False


def extract_external_scheme(
    *,
    request_scheme: str,
    forwarded_proto: str | None,
    peer_is_trusted: bool,
) -> str:
    """Return the externally-visible scheme for the request.

    The trust boundary is the only authority for trusting ``X-Forwarded-Proto``.
    Without it, the value the browser sees is the loopback socket's plain
    HTTP — i.e. ``http``. An untrusted peer that tries to rewrite the scheme
    via the header must be ignored.
    """
    if peer_is_trusted and forwarded_proto:
        proto = forwarded_proto.strip().lower()
        if proto in {"http", "https"}:
            return proto
    return request_scheme


def extract_external_host(
    *,
    request_host: str,
    forwarded_host: str | None,
    peer_is_trusted: bool,
) -> str:
    """Return the externally-visible host for the request.

    Same trust boundary as :func:`extract_external_scheme`. The default
    returns ``request_host`` (the host we observed on the socket) which is
    the loopback host the cloudflared proxy uses; the public hostname is
    reconstructed by the browser from the URL it issued.
    """
    if peer_is_trusted and forwarded_host:
        return forwarded_host.strip().lower()
    return request_host


def host_matches_trusted(
    host_header: str | None,
    rules: Sequence[tuple[str, int | None]],
) -> bool:
    """Return True when the ``Host`` header matches a trusted rule exactly.

    The match is exact: ``127.0.0.1:8000`` matches ``("127.0.0.1", 8000)``
    but not ``("127.0.0.1", None)``. A bare ``127.0.0.1`` matches the
    bare-rule.
    """
    if not host_header:
        return False
    # Strip any default port tail that the client may include.
    candidate = host_header.strip().lower()
    # IPv6 with brackets
    host_part = candidate
    port: int | None = None
    if host_part.startswith("["):
        closing = host_part.find("]")
        if closing == -1:
            return False
        host_part = host_part[1:closing]
        tail = host_part[closing + 1 :]
        if tail:
            if not tail.startswith(":"):
                return False
            port_str = tail[1:]
            if not port_str.isdigit():
                return False
            port = int(port_str)
    elif host_part.count(":") == 1:
        host_part, _, port_str = host_part.partition(":")
        if port_str:
            if not port_str.isdigit():
                return False
            port = int(port_str)
    for rule_host, rule_port in rules:
        if rule_host == "*":
            return True
        if host_part == rule_host and port == rule_port:
            return True
    return False


def ensure_relative_location(location: str) -> str:
    """Force a Location header to be a relative path.

    Apps that build redirects with ``request.url_for`` automatically inherit
    the requested scheme/host. This helper strips any scheme/host prefix so
    the browser resolves the redirect against the URL it actually issued —
    the only correct behaviour when the original scheme/host depends on a
    trust boundary.
    """
    if not location:
        return location
    # scheme://host[:port]/path?query → /path?query
    if "://" in location:
        scheme_split = location.split("://", 1)
        rest = scheme_split[1]
        slash = rest.find("/")
        if slash == -1:
            return "/"
        return rest[slash:]
    return location
