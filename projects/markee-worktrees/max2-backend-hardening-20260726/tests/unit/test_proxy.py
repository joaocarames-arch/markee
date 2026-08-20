"""Unit tests for the proxy / Host parsing helpers in ``app.core.proxy``.

These tests pin the *behavioural* contract of pure helpers used by the ASGI
middleware in ``app.core.proxy``. They are intentionally adversarial:

- ``is_trusted_proxy`` must accept exact IPv4, IPv6, and IPv4 CIDR membership.
  Empty or malformed entries must be rejected at parse time (caller's job to
  pass a clean list).
- ``parse_host_port`` must split an exact host or ``host:port`` pair with
  lowercase normalisation, reject C0 control characters and percent-encoded
  nonsense, and only return values whose host is in the configured allow-list.
- ``parse_trusted_hosts`` normalises a comma/space separated configuration
  string into a deduplicated, lowercased list of exact host entries, with an
  optional explicit port suffix per entry. Empty inputs return an empty list.

This is RED-first: the production code does not yet expose these names, so
the tests must fail with ``AttributeError``/``ImportError`` until
``app.core.proxy`` is implemented. We treat collection-time failures here as
"RED on import" but the *behavioural* assertions below also fail until the
helpers exist with the correct signatures.
"""
from __future__ import annotations

import pytest

from app.core.proxy import (
    is_trusted_proxy,
    parse_host_port,
    parse_trusted_hosts,
)

# ── parse_trusted_hosts ─────────────────────────────────────────────────────


class TestParseTrustedHosts:
    """Behavioural contract for ``parse_trusted_hosts``."""

    def test_empty_string_returns_empty_list(self) -> None:
        assert parse_trusted_hosts("") == []

    def test_whitespace_only_returns_empty_list(self) -> None:
        assert parse_trusted_hosts("   \t  ") == []

    def test_single_host(self) -> None:
        assert parse_trusted_hosts("markee.batata.cc") == ["markee.batata.cc"]

    def test_multiple_hosts_comma_separated(self) -> None:
        assert parse_trusted_hosts("markee.batata.cc,app.markee.batata.cc") == [
            "markee.batata.cc",
            "app.markee.batata.cc",
        ]

    def test_hosts_lowercased_and_deduped(self) -> None:
        result = parse_trusted_hosts(
            "Markee.Batata.CC,markee.batata.cc,  APP.markee.BATATA.cc "
        )
        assert result == ["markee.batata.cc", "app.markee.batata.cc"]

    def test_host_with_explicit_port_preserved(self) -> None:
        assert parse_trusted_hosts("markee.batata.cc:8443") == [
            "markee.batata.cc:8443"
        ]

    def test_mixed_explicit_and_bare_ports_preserved(self) -> None:
        # First-seen order is the documented contract; bare "127.0.0.1" must
        # NOT collide with "127.0.0.1:8000" — both kept.
        result = parse_trusted_hosts(
            "markee.batata.cc:8443,127.0.0.1:8000,127.0.0.1"
        )
        assert result == [
            "markee.batata.cc:8443",
            "127.0.0.1:8000",
            "127.0.0.1",
        ]


# ── parse_host_port ─────────────────────────────────────────────────────────


class TestParseHostPort:
    """Behavioural contract for ``parse_host_port``."""

    def test_exact_host_match(self) -> None:
        allowed = ["markee.batata.cc", "app.markee.batata.cc"]
        assert parse_host_port("markee.batata.cc", allowed) == "markee.batata.cc"

    def test_exact_host_case_insensitive(self) -> None:
        allowed = ["markee.batata.cc"]
        assert parse_host_port("Markee.Batata.CC", allowed) == "markee.batata.cc"

    def test_host_with_explicit_port_matches_explicit_port_entry(self) -> None:
        allowed = ["127.0.0.1:8000"]
        assert parse_host_port("127.0.0.1:8000", allowed) == "127.0.0.1:8000"

    def test_bare_host_does_not_match_host_with_port(self) -> None:
        """'127.0.0.1' must not satisfy an entry '127.0.0.1:8000'."""
        allowed = ["127.0.0.1:8000"]
        with pytest.raises(ValueError):
            parse_host_port("127.0.0.1", allowed)

    def test_host_with_port_does_not_match_bare_host_entry(self) -> None:
        """'127.0.0.1:8000' must not satisfy an entry '127.0.0.1'."""
        allowed = ["127.0.0.1"]
        with pytest.raises(ValueError):
            parse_host_port("127.0.0.1:8000", allowed)

    def test_unknown_host_raises(self) -> None:
        allowed = ["markee.batata.cc"]
        with pytest.raises(ValueError):
            parse_host_port("evil.example.com", allowed)

    def test_host_with_crlf_raises(self) -> None:
        """CR/LF/NUL/percent-encoded control chars must be rejected."""
        allowed = ["markee.batata.cc"]
        for bad in [
            "markee.batata.cc\r\n",
            "markee.batata.cc\n",
            "markee.batata.cc\x00",
            "markee.batata.cc%0d%0a",
        ]:
            with pytest.raises(ValueError):
                parse_host_port(bad, allowed)

    def test_userinfo_raises(self) -> None:
        """Host header must never contain a userinfo prefix."""
        allowed = ["markee.batata.cc"]
        with pytest.raises(ValueError):
            parse_host_port("attacker@markee.batata.cc", allowed)

    def test_empty_raises(self) -> None:
        with pytest.raises(ValueError):
            parse_host_port("", ["markee.batata.cc"])

    def test_host_with_arbitrary_port_against_bare_entry_raises(self) -> None:
        """An explicit arbitrary port must NOT match a bare allow-list entry.

        Otherwise ``Host: evil.example.com:666`` would satisfy
        ``TRUSTED_HOSTS=[evil.example.com]`` and smuggle a redirect through.
        """
        with pytest.raises(ValueError):
            parse_host_port("evil.example.com:666", ["evil.example.com"])


# ── is_trusted_proxy ────────────────────────────────────────────────────────


class TestIsTrustedProxy:
    """Behavioural contract for ``is_trusted_proxy``."""

    def test_exact_ipv4_match(self) -> None:
        assert is_trusted_proxy("127.0.0.1", ["127.0.0.1"]) is True

    def test_exact_ipv4_no_match(self) -> None:
        assert is_trusted_proxy("10.0.0.1", ["127.0.0.1"]) is False

    def test_cidr_match_ipv4(self) -> None:
        assert is_trusted_proxy("10.0.0.42", ["10.0.0.0/24"]) is True

    def test_cidr_no_match_ipv4(self) -> None:
        assert is_trusted_proxy("10.0.1.42", ["10.0.0.0/24"]) is False

    def test_cidr_ipv6_match(self) -> None:
        assert (
            is_trusted_proxy("2001:db8::1", ["2001:db8::/32"]) is True
        )

    def test_cidr_ipv6_no_match(self) -> None:
        assert (
            is_trusted_proxy("2001:dead::1", ["2001:db8::/32"]) is False
        )

    def test_exact_ipv6_match(self) -> None:
        assert is_trusted_proxy("::1", ["::1"]) is True

    def test_ipv4_mapped_ipv6_normalised(self) -> None:
        """``::ffff:127.0.0.1`` and ``127.0.0.1`` are treated as the same peer.

        uvicorn reports the immediate peer either way; both must compare equal
        against an allow-list entry that says ``127.0.0.1``.
        """
        assert is_trusted_proxy("::ffff:127.0.0.1", ["127.0.0.1"]) is True

    def test_empty_allow_list_never_matches(self) -> None:
        assert is_trusted_proxy("127.0.0.1", []) is False

    def test_malformed_caller_peer_never_matches(self) -> None:
        """Malformed caller peer is rejected outright, not silently trusted."""
        assert is_trusted_proxy("not-an-ip", ["127.0.0.1"]) is False
        assert is_trusted_proxy("", ["127.0.0.1"]) is False

    def test_malformed_entry_does_not_match_anything(self) -> None:
        """An entry that fails to parse must not poison the whole list.

        Behaviour: malformed entries are skipped during evaluation; the caller
        is responsible for surfacing the parse failure at config time.
        """
        assert is_trusted_proxy("127.0.0.1", ["not-an-ip"]) is False
        # But a sibling valid entry still works.
        assert is_trusted_proxy("127.0.0.1", ["not-an-ip", "127.0.0.1"]) is True

    def test_wildcard_cidr_does_not_match(self) -> None:
        """A ``0.0.0.0/0`` entry must be flagged as insecure / disallowed.

        A wildcard CIDR is functionally equivalent to ``trust everyone`` and
        must never be accepted by the helper.
        """
        assert is_trusted_proxy("8.8.8.8", ["0.0.0.0/0"]) is False

    def test_wildcard_cidr_ipv6_does_not_match(self) -> None:
        """A ``::/0`` entry must be flagged as insecure / disallowed.

        Mirrors the IPv4 ``0.0.0.0/0`` rejection. A wildcard CIDR covers the
        whole address space and is functionally equivalent to
        ``trust everyone``; the helper must refuse to match any peer against
        it, regardless of address family.
        """
        assert is_trusted_proxy("2001:db8::1", ["::/0"]) is False