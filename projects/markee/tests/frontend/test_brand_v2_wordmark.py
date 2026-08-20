"""Tests for the canonical Brand v2 wordmark SVGs.

The wordmarks are the source of truth for the visual identity:

* Sora Bold (OFL 1.1) rendered as ``<path>`` only.
* Last ``e`` glyph uses ``#35D0E0`` in the chromatic variants.
* No ``<text>``, no ``<image>``, no external ``href`` / ``xlink:href``.
* viewBox ``0 0 1481.95 240.00`` (per BRAND_MANUAL.md §2).
* SHA256 of every Brand v2 asset must match the committed canonical manifest.

These tests deliberately parse the files with stdlib only — no cairosvg,
no fontTools, no Pillow.
"""
from __future__ import annotations

import hashlib
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from . import _helpers as H


SVG_NS = "http://www.w3.org/2000/svg"
ET.register_namespace("", SVG_NS)


def _parse_svg(path: Path) -> ET.Element:
    """Parse an SVG with stdlib and return the root element."""
    return ET.fromstring(path.read_text(encoding="utf-8"))


def _fills(root: ET.Element) -> list[str]:
    """Return every ``fill`` attribute found anywhere in the SVG tree."""
    fills: list[str] = []
    for el in root.iter():
        if "fill" in el.attrib:
            fills.append(el.attrib["fill"].strip())
    return fills


# ---------------------------------------------------------------------------
# Canonical manifest (provenance)
# ---------------------------------------------------------------------------


def test_canonical_sha256_matches_committed_manifest():
    """The committed manifest is complete, self-contained and factual."""
    manifest_path = (
        H.REPO_ROOT / "evidence" / "max3-frontend-brand-v2-20260726" / "manifest.json"
    )
    assert manifest_path.is_file(), "committed Brand v2 manifest missing"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert manifest["schema_version"] == 2
    assert manifest["asset_root"] == "assets/brand-v2"
    expected: dict[str, str] = manifest["sha256"]
    relative_paths: list[str] = manifest["relative_paths"]
    assert relative_paths == list(expected), "manifest paths and hashes must align"
    assert len(relative_paths) == 11
    assert len(relative_paths) == len(set(relative_paths)), "manifest paths must be unique"
    assert all(re.fullmatch(r"[0-9a-f]{64}", digest) for digest in expected.values())
    assert all(not Path(rel).is_absolute() and ".." not in Path(rel).parts for rel in relative_paths)

    root = H.REPO_ROOT / manifest["asset_root"]
    tracked_paths = sorted(
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if path.is_file() and H.is_git_tracked(path)
    )
    assert sorted(relative_paths) == tracked_paths, "manifest must cover exactly the committed assets"

    for rel, want in expected.items():
        target = root / rel
        assert target.is_file(), f"manifest references missing file: {rel}"
        assert hashlib.sha256(target.read_bytes()).hexdigest() == want, f"sha256 drift in {rel}"

    superseded = manifest["provenance"]["superseded"]
    assert "logos/markee-wordmark-dark.svg" in superseded
    assert "live visual hotfix" in superseded["logos/markee-wordmark-dark.svg"]


# ---------------------------------------------------------------------------
# Wordmark structure
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "filename, expected_main_fill",
    [
        ("markee-wordmark-dark.svg", "#E8E8E8"),
        ("markee-wordmark-light.svg", "#08090A"),
        ("markee-wordmark-mono-white.svg", "#FFFFFF"),
        ("markee-wordmark-mono-black.svg", "#08090A"),
    ],
)
def test_wordmark_svg_is_well_formed_and_clean(filename, expected_main_fill):
    """Each wordmark SVG must be well-formed XML, declare the same
    canonical viewBox, contain only ``<path>`` / ``<g>`` nodes and use the
    expected main fill.
    """
    path = H.BRAND_V2_LOGOS / filename
    assert path.is_file(), f"wordmark missing: {filename}"
    root = _parse_svg(path)

    assert root.tag == f"{{{SVG_NS}}}svg", "root must be <svg>"

    # viewBox from BRAND_MANUAL.md §2 (with the actual computed value).
    vb = root.attrib.get("viewBox")
    assert vb == "0 0 1481.95 240.00", f"unexpected viewBox: {vb!r}"

    # No <text>, no <image>, no <use>, no external href / xlink:href.
    forbidden_tags = {f"{{{SVG_NS}}}{tag}" for tag in ("text", "image", "use")}
    seen = {el.tag for el in root.iter()}
    leaked = seen & forbidden_tags
    assert not leaked, f"forbidden tags in {filename}: {leaked}"

    for el in root.iter():
        assert "href" not in el.attrib, f"raw href attr in {filename}"
        assert (
            "{http://www.w3.org/1999/xlink}href" not in el.attrib
        ), f"xlink:href in {filename}"

    fills = _fills(root)
    # Hex colors may appear upper or lower case in the spec; canonicalise.
    norm = {f.upper() for f in fills}
    assert (
        expected_main_fill.upper() in norm
    ), f"main fill {expected_main_fill} missing from {filename}"


def test_dark_and_light_wordmarks_end_in_cyan_accent():
    """Per BRAND_MANUAL.md §5 the chromatic variants dark + light must
    have the *last* ``e`` painted in ``#35D0E0``. The canonical SVG keeps
    six ``<path>`` elements (one per glyph: m, a, r, k, e, e); the last
    one is the accent.
    """
    for filename in ("markee-wordmark-dark.svg", "markee-wordmark-light.svg"):
        path = H.BRAND_V2_LOGOS / filename
        root = _parse_svg(path)
        paths = root.findall(f".//{{{SVG_NS}}}path")
        # Six glyphs: m, a, r, k, e, e.
        assert len(paths) == 6, f"unexpected glyph count in {filename}: {len(paths)}"
        last_fill = paths[-1].attrib.get("fill", "").strip().upper()
        assert (
            last_fill == "#35D0E0"
        ), f"last glyph in {filename} must be #35D0E0, got {last_fill!r}"


def test_wordmark_glyph_offsets_are_flattened_matrix_transforms():
    """Glyph offsets must be flattened so browsers cannot double-scale spacing.

    The earlier nested transform version bunched the homepage logo because the
    offsets were interpreted inconsistently. Matrix transforms make each glyph's
    final position explicit.
    """
    expected = [
        "matrix(0.37453183520599254 0 0 -0.37453183520599254 20.00 220)",
        "matrix(0.37453183520599254 0 0 -0.37453183520599254 388.16 220)",
        "matrix(0.37453183520599254 0 0 -0.37453183520599254 610.64 220)",
        "matrix(0.37453183520599254 0 0 -0.37453183520599254 768.31 220)",
        "matrix(0.37453183520599254 0 0 -0.37453183520599254 1007.64 220)",
        "matrix(0.37453183520599254 0 0 -0.37453183520599254 1241.35 220)",
    ]
    for filename in (
        "markee-wordmark-dark.svg",
        "markee-wordmark-light.svg",
        "markee-wordmark-mono-white.svg",
        "markee-wordmark-mono-black.svg",
    ):
        root = _parse_svg(H.BRAND_V2_LOGOS / filename)
        paths = root.findall(f".//{{{SVG_NS}}}path")
        actual = [path.attrib.get("transform") for path in paths]
        assert actual == expected, f"glyph spacing drift in {filename}: {actual}"


def test_mono_wordmarks_have_no_cyan_accent():
    """The two mono variants never paint a glyph in cyan — the accent is
    forbidden in 1-tinta applications per BRAND_MANUAL.md §9.1.
    """
    for filename in ("markee-wordmark-mono-white.svg", "markee-wordmark-mono-black.svg"):
        path = H.BRAND_V2_LOGOS / filename
        root = _parse_svg(path)
        fills = {f.upper() for f in _fills(root)}
        assert (
            "#35D0E0" not in fills
        ), f"cyan accent leaked into mono wordmark {filename}"


def test_mono_white_wordmark_is_all_white():
    """The mono-white wordmark uses #FFFFFF for every glyph."""
    path = H.BRAND_V2_LOGOS / "markee-wordmark-mono-white.svg"
    root = _parse_svg(path)
    paths = root.findall(f".//{{{SVG_NS}}}path")
    fills = {p.attrib.get("fill", "").strip().upper() for p in paths}
    assert fills == {"#FFFFFF"}, f"mono-white wordmark fills must be only #FFFFFF, got {fills}"


def test_mono_black_wordmark_is_all_ink():
    """The mono-black wordmark uses #08090A (ink) for every glyph."""
    path = H.BRAND_V2_LOGOS / "markee-wordmark-mono-black.svg"
    root = _parse_svg(path)
    paths = root.findall(f".//{{{SVG_NS}}}path")
    fills = {p.attrib.get("fill", "").strip().upper() for p in paths}
    assert fills == {"#08090A"}, f"mono-black wordmark fills must be only #08090A, got {fills}"


# ---------------------------------------------------------------------------
# Wordmark meta + tokens coherence
# ---------------------------------------------------------------------------


def test_wordmark_meta_json_matches_manual():
    """The Sora Bold metrics published in wordmark-meta.json must match
    BRAND_MANUAL.md §2. A mismatch means a future agent is working from
    inconsistent provenance.
    """
    meta = json.loads(
        (H.BRAND_V2_LOGOS / "wordmark-meta.json").read_text(encoding="utf-8")
    )
    assert meta["font"] == "Sora-Bold.ttf"
    assert meta["license"].startswith("OFL-1.1"), meta["license"]
    assert meta["units_per_em"] == 1000
    assert meta["x_height"] == 534
    assert meta["cap_height"] == 730
    advances = meta["advances"]
    assert advances == {"m": 983, "a": 594, "r": 421, "k": 639, "e": 624}


def test_tokens_css_contains_no_amber_color():
    """The canonical Brand v2 CSS variables must not define any amber /
    orange color — BRAND_MANUAL.md §6.3 forbids it and the warning state
    is communicated through icon + text on neutral surfaces.
    """
    css = H.BRAND_V2_TOKENS_CSS.read_text(encoding="utf-8")
    assert "#f5a623" not in css.lower(), "amber hex #f5a623 leaked into tokens"
    assert "amber" not in css.lower(), "'amber' string leaked into tokens"
    assert "#25a8b8" in css.lower(), "accent-pressed token missing"
    assert "#35d0e0" in css.lower(), "accent token missing"


def test_tokens_json_keeps_accents_consistent():
    """The DTCG JSON must mark warning as a no-color value."""
    tokens = json.loads(H.BRAND_V2_TOKENS_JSON.read_text(encoding="utf-8"))
    assert tokens["color"]["accent"]["$value"].lower() == "#35d0e0"
    assert tokens["color"]["accent-pressed"]["$value"].lower() == "#25a8b8"
    assert tokens["color"]["warning"]["$value"] == "no-color"


def test_brand_v2_logos_have_six_glyphs_only():
    """Sanity: every chromatic wordmark encodes exactly six glyphs
    (m, a, r, k, e, e). Drift here signals silent edits to the SVG.
    """
    pattern = re.compile(r"<path\b", re.IGNORECASE)
    dark = (H.BRAND_V2_LOGOS / "markee-wordmark-dark.svg").read_text(encoding="utf-8")
    assert len(pattern.findall(dark)) == 6, "markee-wordmark-dark.svg glyph count drift"

    light = (H.BRAND_V2_LOGOS / "markee-wordmark-light.svg").read_text(encoding="utf-8")
    assert len(pattern.findall(light)) == 6, "markee-wordmark-light.svg glyph count drift"