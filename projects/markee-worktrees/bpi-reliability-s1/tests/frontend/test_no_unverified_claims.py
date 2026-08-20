"""Fail-closed scans for unverified / absolute marketing claims.

The brief forbids claims that the backend does not back:

* ``24/7`` and ``24h`` as SLA promises (no on-call guarantee today).
* ``≤24h`` from publication to alert (no measurable SLA).
* ``2 minutos`` and ``SEM CARTÃO`` (no checkout, no SLA).
* ``MAIS POPULAR`` (no telemetry-driven popularity ranking).
* ``NOVALUZ`` / ``NOVA LUZZ`` (a fictional showcase brand that the
  ``engine`` panel uses to simulate a similarity report — it is not a
  real customer, the brief forbids fake stories).
* ``Come[çc]ar gratuit`` and ``Ativar vigil[âa]ncia gratuit`` (CTAs
  that promise free monitoring before billing is even wired).
* ``WIPO`` and ``Telegram`` (Telegram bot and WIPO coverage are not
  wired in the current backend — confirmed by ``tests/stg00`` kill
  switches and the task brief).

The marketing strings live in HTML. Jurisdiction identifiers
(``INPI``, ``EUIPO``) are allowed in technical contexts (``<option
value="…">``, ``data-jurisdiction`` attributes) — the cross-review
spells this out. The tests below treat those contexts as whitelisted.

Functional control labels (e.g. ``aria-label=\"Ativar vigilância
<Nome>\"`` on a real watchlist toggle) are NOT marketing claims — they
describe what the control does for assistive tech. The tests below
whitelist the ``aria-label`` attribute itself so the deny-list stays
honest about promotional copy.
"""
from __future__ import annotations

import re

import pytest

from . import _helpers as H


# Forbidden claim strings, lower-cased. We also forbid their variants
# (with diacritics, with surrounding punctuation).
FORBIDDEN_CLAIMS = [
    "24/7",                       # fake SLA
    "≤24h",
    "&le;24h",                    # HTML entity for ≤
    "2 minutos",
    "sem cartão",
    "mais popular",
    "novaluz",
    "nova luzz",
    "wipo",
    "começar gratuitamente",
    "comecar gratuitamente",
    "ativar vigilância gratuita",
    "ativar vigilancia gratuita",
    "vigilância contínua",
    "vigilancia continua",
    "comece em segundos",
]


# Functional control labels that mention the product feature but are
# *not* marketing promises. The deny-list must keep rejecting the
# promotional phrase "ativar vigilância gratuita" (no checkout wired);
# the bare "ativar vigilância" is only acceptable inside an aria-label
# that describes a real watchlist toggle (it names the control, not a
# promise). Any other occurrence still fails.
_FUNCTIONAL_ARIA_LABEL_RE = re.compile(
    r"""aria-label\s*=\s*["']([^"']*?)["']""",
    re.IGNORECASE,
)


def _strip_functional_aria_labels(body: str) -> str:
    """Remove the *value* of any ``aria-label`` so a functional control
    label survives the deny-list. The attribute name remains, so other
    checks (e.g. ``aria-label="…"`` whitespace) keep working.
    """
    return _FUNCTIONAL_ARIA_LABEL_RE.sub('aria-label=""', body)


def _strip_html_comments(body: str) -> str:
    """Remove ``<!-- … -->`` so JS-side comments do not trip the scans.

    Only comments inside committed HTML are stripped; JS / CSS comments
    use different syntax.
    """
    return re.sub(r"<!--.*?-->", "", body, flags=re.DOTALL)


def _scrub_promotional_aria_labels(body: str) -> str:
    """Remove the *value* of any ``aria-label`` that does NOT carry a
    promotional phrase. The deny-list still scans promotional phrases
    even inside ``aria-label`` strings (so a fake "ativar vigilância
    gratuita" button labelled for assistive tech still fails). Non
    promotional labels (e.g. "Ativar vigilância <watchlist>") are
    scrubbed so the bare deny-list ``"ativar vigilância"`` only fires
    on real marketing copy.
    """
    def _replace(match: re.Match) -> str:
        value = match.group(1)
        lowered = value.lower()
        for promotional in (
            "ativar vigilância gratuita",
            "ativar vigilancia gratuita",
            "gratuita",
            "gratis",
            "sem cartão",
            "sem cartao",
        ):
            if promotional in lowered:
                return match.group(0)
        return 'aria-label=""'
    return _FUNCTIONAL_ARIA_LABEL_RE.sub(_replace, body)


@pytest.mark.parametrize("claim", FORBIDDEN_CLAIMS)
def test_landing_html_does_not_contain_claim(claim):
    """A single occurrence in user-visible HTML is enough to fail."""
    body = _strip_html_comments(H.read_text(H.LANDING_HTML)).lower()
    body = _scrub_promotional_aria_labels(body)
    assert claim.lower() not in body, (
        f"landing still mentions forbidden claim {claim!r}"
    )


def test_dashboard_html_does_not_contain_claim():
    body = _strip_html_comments(H.read_text(H.DASHBOARD_HTML)).lower()
    body = _scrub_promotional_aria_labels(body)
    for claim in FORBIDDEN_CLAIMS:
        assert claim.lower() not in body, (
            f"dashboard still mentions forbidden claim {claim!r}"
        )


def test_landing_js_does_not_contain_claim():
    body = H.read_text(H.LANDING_JS).lower()
    body = _scrub_promotional_aria_labels(body)
    for claim in FORBIDDEN_CLAIMS:
        assert claim.lower() not in body, (
            f"landing/script.js still mentions forbidden claim {claim!r}"
        )


def test_dashboard_js_does_not_contain_claim():
    body = H.read_text(H.DASHBOARD_JS).lower()
    body = _scrub_promotional_aria_labels(body)
    for claim in FORBIDDEN_CLAIMS:
        assert claim.lower() not in body, (
            f"dashboard/app.js still mentions forbidden claim {claim!r}"
        )


def test_dashboard_js_keeps_functional_watch_activation_aria_label():
    """The watchlist toggle's aria-label is a real control description
    (not marketing copy). It must remain so the watchlist activation
    control is reachable via assistive tech.
    """
    body = H.read_text(H.DASHBOARD_JS)
    assert (
        'aria-label="Ativar vigilância' in body
        or "aria-label='Ativar vigilância" in body
    ), "functional 'Ativar vigilância' aria-label missing on watchlist toggle"


def test_landing_html_does_not_reference_telegram():
    """The Telegram bot is not wired; the landing must not advertise it."""
    body = _strip_html_comments(H.read_text(H.LANDING_HTML)).lower()
    assert "telegram" not in body, "landing still references Telegram"


def test_dashboard_html_does_not_reference_telegram():
    body = _strip_html_comments(H.read_text(H.DASHBOARD_HTML)).lower()
    assert "telegram" not in body, "dashboard still references Telegram"


def test_jurisdiction_identifiers_only_in_technical_context():
    """``INPI`` and ``EUIPO`` must appear in technical contexts only.

    Whitelisted technical contexts (per the cross-review):
      * ``<option value="EUIPO">…</option>``
      * ``<input type="checkbox" name="jur" value="EUIPO"> … </label>``
      * ``data-jurisdiction`` attributes

    Forbidden: any paragraph / heading / copy that addresses the user
    with ``INPI`` / ``EUIPO`` as a visible label (e.g. an auth tagline
    that reads "Monitorização de marcas no INPI e EUIPO").
    """
    body = H.read_text(H.DASHBOARD_JS)

    # Whitelisted patterns: <option value=…> and checkbox labels.
    assert re.search(r'<option value="EUIPO"', body), "EUIPO option value missing"
    assert re.search(r'<option value="INPI"', body), "INPI option value missing"
    assert re.search(r'value="EUIPO"\s*/?>', body), "EUIPO checkbox value missing"
    assert re.search(r'value="INPI"\s*/?>', body), "INPI checkbox value missing"

    # Forbidden: a paragraph / heading / general text label that puts
    # the jurisdiction identifiers between a ``>`` and a ``<`` tag
    # *outside* an option / checkbox / select construct. We whitelist
    # the technical contexts by removing them before scanning.
    scrubbed = body
    scrubbed = re.sub(r"<option [^>]*>[^<]*</option>", "", scrubbed)
    scrubbed = re.sub(
        r'<input[^>]*value="(EUIPO|INPI)"[^>]*>\s*(EUIPO|INPI)\s*</label>',
        "",
        scrubbed,
    )
    label_hits = re.findall(r">\s*(INPI|EUIPO)\s*<", scrubbed)
    assert not label_hits, (
        f"EUIPO/INPI used as visible text label outside whitelisted contexts: {label_hits}"
    )

    # And never as a sentence fragment in copy (e.g. ``… no INPI e EUIPO``).
    # We look for a literal phrase with whitespace on both sides.
    sentence_hits = [
        match.group(0)
        for match in re.finditer(
            r"(?<!\w)\s*no\s+(?:EUIPO(?:\s+e\s+INPI)?|INPI(?:\s+e\s+EUIPO)?)(?!\w)",
            body,
            re.IGNORECASE,
        )
    ]
    assert not sentence_hits, (
        f"EUIPO/INPI used in user-facing sentence: {sentence_hits}"
    )