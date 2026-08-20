"""Visual and integration contracts for the canonical Markee v2 wordmark."""

from __future__ import annotations

import json
import re
from io import BytesIO
from pathlib import Path
from xml.etree import ElementTree as ET

import cairosvg
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
BRAND = ROOT / "assets" / "brand-v2"
LOGOS = BRAND / "logos"
SVG_NS = "http://www.w3.org/2000/svg"
WORDMARKS = (
    "markee-wordmark-dark.svg",
    "markee-wordmark-light.svg",
    "markee-wordmark-mono-white.svg",
    "markee-wordmark-mono-black.svg",
)


def _render_alpha_bbox(svg: bytes, width: int = 1482, height: int = 240) -> tuple[int, int, int, int]:
    png = cairosvg.svg2png(bytestring=svg, output_width=width, output_height=height)
    image = Image.open(BytesIO(png)).convert("RGBA")
    bbox = image.getchannel("A").getbbox()
    assert bbox is not None, "rendered SVG must contain visible pixels"
    return bbox


def _glyph_bboxes(svg_path: Path) -> list[tuple[int, int, int, int]]:
    root = ET.parse(svg_path).getroot()
    group = root.find(f"{{{SVG_NS}}}g")
    assert group is not None
    paths = group.findall(f"{{{SVG_NS}}}path")
    assert len(paths) == 6, "the canonical lettering must contain exactly m-a-r-k-e-e"

    bboxes = []
    for path in paths:
        isolated = ET.Element(
            f"{{{SVG_NS}}}svg",
            {"viewBox": root.attrib["viewBox"], "xmlns": SVG_NS},
        )
        isolated_group = ET.SubElement(
            isolated, f"{{{SVG_NS}}}g", {"transform": group.attrib["transform"]}
        )
        isolated_group.append(path)
        bboxes.append(_render_alpha_bbox(ET.tostring(isolated)))
    return bboxes


def test_wordmark_raster_geometry_has_six_ordered_non_overlapping_glyphs() -> None:
    """Rasterized glyphs must read left-to-right without overlap or fragmentation."""
    for filename in WORDMARKS:
        bboxes = _glyph_bboxes(LOGOS / filename)
        widths = [right - left for left, _, right, _ in bboxes]
        assert min(widths) >= 25, f"{filename}: fragmented/narrow glyph: {bboxes}"
        for index, (current, following) in enumerate(zip(bboxes, bboxes[1:])):
            overlap = current[2] - following[0]
            assert overlap <= 1, (
                f"{filename}: glyphs {index}/{index + 1} overlap by {overlap}px: {bboxes}"
            )
            assert following[0] > current[0], f"{filename}: advances are not increasing"


def test_wordmark_renders_at_required_sizes_on_transparent_canvas() -> None:
    for filename in WORDMARKS:
        source = (LOGOS / filename).read_bytes()
        for height in (24, 32, 132):
            width = round(height * 1481.95 / 240)
            bbox = _render_alpha_bbox(source, width=width, height=height)
            assert bbox[0] >= 0 and bbox[2] <= width
            assert bbox[1] >= 0 and bbox[3] <= height
            assert bbox[2] - bbox[0] >= width * 0.85


def test_wordmark_structure_colours_and_metadata_are_canonical() -> None:
    expected = {
        "markee-wordmark-dark.svg": ("#E8E8E8", "#35D0E0"),
        "markee-wordmark-light.svg": ("#08090A", "#35D0E0"),
        "markee-wordmark-mono-white.svg": ("#FFFFFF", "#FFFFFF"),
        "markee-wordmark-mono-black.svg": ("#08090A", "#08090A"),
    }
    for filename, (main, accent) in expected.items():
        root = ET.parse(LOGOS / filename).getroot()
        assert root.attrib["viewBox"] == "0 0 1482 240"
        assert not root.findall(f".//{{{SVG_NS}}}text")
        paths = root.findall(f".//{{{SVG_NS}}}path")
        assert len(paths) == 6
        assert [p.attrib["fill"].upper() for p in paths[:-1]] == [main] * 5
        assert paths[-1].attrib["fill"].upper() == accent
        raw = (LOGOS / filename).read_text()
        assert "href=" not in raw and "<image" not in raw

    metadata = json.loads((LOGOS / "wordmark-meta.json").read_text())
    assert metadata["font_family"] == "Sora"
    assert metadata["font_weight"] == 700
    assert metadata["glyphs"] == list("markee")
    assert len(metadata["positions"]) == 6
    assert metadata["positions"] == sorted(metadata["positions"])


def test_brand_package_internal_references_exist() -> None:
    required = {
        "README.md",
        "docs/BRAND_MANUAL.md",
        "docs/DESIGN.md",
        "tokens/tokens.json",
        "tokens/css-variables.css",
        "logos/markee-brand-sheet.svg",
        "logos/wordmark-meta.json",
        *{f"logos/{name}" for name in WORDMARKS},
    }
    actual = {str(path.relative_to(BRAND)) for path in BRAND.rglob("*") if path.is_file()}
    assert required <= actual

    referenced = set()
    for doc in (BRAND / "README.md", BRAND / "docs" / "BRAND_MANUAL.md"):
        text = doc.read_text()
        referenced.update(re.findall(r"(?:docs|tokens|logos)/[A-Za-z0-9_./{}-]+", text))
    literal_refs = {
        ref.rstrip(".,):`")
        for ref in referenced
        if "{" not in ref and not ref.endswith("-")
    }
    missing = sorted(ref for ref in literal_refs if not (BRAND / ref).exists())
    assert not missing, f"missing package references: {missing}"


def test_frontend_preserves_routes_motion_and_billing_while_using_brand_v2() -> None:
    landing = (ROOT / "frontend" / "landing" / "index.html").read_text()
    landing_js = (ROOT / "frontend" / "landing" / "script.js").read_text()
    dashboard_html = (ROOT / "frontend" / "dashboard" / "index.html").read_text()
    dashboard_js = (ROOT / "frontend" / "dashboard" / "app.js").read_text()

    assert "/frontend/" not in landing + dashboard_html
    assert "/app/login" not in landing + dashboard_html + dashboard_js
    assert "/static/assets/brand-v2/logos/markee-wordmark-dark.svg" in landing
    assert "/assets/brand-v2/logos/markee-wordmark-dark.svg" in dashboard_js
    for contract in ("gsap", "Lenis", "three", "webglCanvas", "preloader", "cursorRing"):
        assert contract in landing + landing_js
    for contract in ("PLAN_META", "/billing/plans", "/billing/checkout"):
        assert contract in dashboard_js
