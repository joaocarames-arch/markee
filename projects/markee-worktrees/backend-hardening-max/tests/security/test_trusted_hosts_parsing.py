"""Pure parsing tests for the trust-boundary helpers.

These cover the input surface the production configuration must accept/reject
without touching the FastAPI app or any middleware stack. They are intentionally
narrow: they prove that a single, well-typed helper turns a list of strings
into a stable, validated tuple of (host, port) rules with no fallback to "*"
and no silent acceptance of malformed entries.

No FastAPI import, no scope/peer, no monkeypatched settings cache; just the
helper we want to introduce into ``app.core.config``.
"""
from __future__ import annotations

import pytest

# The helpers live in app.core.config once we introduce them. The test imports
# eagerly so a NameError/ImportError is itself a failing test (red).
from app.core.config import (  # noqa: F401 - intentional red import
    parse_trusted_hosts,
    parse_trusted_proxies,
)


# ── parse_trusted_hosts ──────────────────────────────────────────────────────


class TestParseTrustedHosts:
    """Strings → tuple[(host, port|None)] with exact host:port semantics."""

    def test_accepts_public_hostnames(self) -> None:
        rules = parse_trusted_hosts(
            ["markee.batata.cc", "app.markee.batata.cc"]
        )
        assert ("markee.batata.cc", None) in rules
        assert ("app.markee.batata.cc", None) in rules

    def test_accepts_loopback_with_explicit_port(self) -> None:
        rules = parse_trusted_hosts(["127.0.0.1:8000"])
        assert ("127.0.0.1", 8000) in rules

    def test_preserves_ipv6_brackets(self) -> None:
        rules = parse_trusted_hosts(["[::1]:8000"])
        assert ("::1", 8000) in rules

    def test_rejects_wildcard_in_production(self) -> None:
        with pytest.raises(ValueError, match="wildcard"):
            parse_trusted_hosts(["*"], allow_wildcard=False)

    def test_rejects_empty_list(self) -> None:
        with pytest.raises(ValueError, match="empty"):
            parse_trusted_hosts([])

    def test_rejects_oversized_host(self) -> None:
        with pytest.raises(ValueError, match="host"):
            parse_trusted_hosts(["a" * 254])

    def test_rejects_port_out_of_range(self) -> None:
        with pytest.raises(ValueError, match="port"):
            parse_trusted_hosts(["127.0.0.1:99999"])
        with pytest.raises(ValueError, match="port"):
            parse_trusted_hosts(["127.0.0.1:0"])

    def test_rejects_malformed_host_port(self) -> None:
        with pytest.raises(ValueError):
            parse_trusted_hosts(["127.0.0.1:"])
        with pytest.raises(ValueError):
            parse_trusted_hosts([":8000"])

    def test_strips_surrounding_whitespace(self) -> None:
        rules = parse_trusted_hosts(["  markee.batata.cc  "])
        assert ("markee.batata.cc", None) in rules

    def test_no_fallback_to_wildcard(self) -> None:
        # Calling the parser in production semantics must never end with "*".
        rules = parse_trusted_hosts(["markee.batata.cc"], allow_wildcard=False)
        assert not any(host == "*" for host, _ in rules)

    def test_dev_mode_may_accept_wildcard(self) -> None:
        rules = parse_trusted_hosts(["*"], allow_wildcard=True)
        assert rules == (("*", None),)


# ── parse_trusted_proxies ────────────────────────────────────────────────────


class TestParseTrustedProxies:
    """Strings → tuple[ip_network|ip_address]; loopback + cloudflared only."""

    def test_accepts_loopback_ipv4(self) -> None:
        rules = parse_trusted_proxies(["127.0.0.1/32"])
        assert rules  # non-empty

    def test_accepts_loopback_ipv6(self) -> None:
        rules = parse_trusted_proxies(["::1/128"])
        assert rules

    def test_accepts_single_ip(self) -> None:
        rules = parse_trusted_proxies(["127.0.0.1"])
        assert rules

    def test_rejects_hostname(self) -> None:
        # cloudflared is local; we never trust by hostname in this trust boundary.
        with pytest.raises(ValueError, match="CIDR"):
            parse_trusted_proxies(["localhost"])

    def test_rejects_wildcard_cidr(self) -> None:
        with pytest.raises(ValueError, match="0.0.0.0"):
            parse_trusted_proxies(["0.0.0.0/0"])

    def test_rejects_empty(self) -> None:
        with pytest.raises(ValueError, match="empty"):
            parse_trusted_proxies([])

    def test_rejects_malformed_cidr(self) -> None:
        with pytest.raises(ValueError):
            parse_trusted_proxies(["127.0.0.1/64"])

    def test_untrusted_peer_matches_nothing(self) -> None:
        rules = parse_trusted_proxies(["127.0.0.1/32"])
        # 1.2.3.4 must not be trusted.
        import ipaddress as _ip
        assert not any(_ip.ip_address("1.2.3.4") in net for net in rules)
