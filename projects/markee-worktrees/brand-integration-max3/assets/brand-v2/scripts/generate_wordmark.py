#!/usr/bin/env python3
"""Regenerate the canonical Markee wordmarks from the official Sora Bold font."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.ttLib import TTFont

BRAND = Path(__file__).resolve().parents[1]
FONT_PATH = BRAND / "source" / "Sora-Bold.ttf"
LOGO_DIR = BRAND / "logos"
WORD = "markee"
TARGET_X_HEIGHT = 200
PADDING = 20
KERNING = {"ke": -25, "ee": -10}
SOURCE_URL = "https://fonts.gstatic.com/s/sora/v17/xMQOuFFYT72X5wkB_18qmnndmSe1mX-K.ttf"
VARIANTS = {
    "markee-wordmark-dark.svg": ("#E8E8E8", "#35D0E0"),
    "markee-wordmark-light.svg": ("#08090A", "#35D0E0"),
    "markee-wordmark-mono-white.svg": ("#FFFFFF", "#FFFFFF"),
    "markee-wordmark-mono-black.svg": ("#08090A", "#08090A"),
}


def main() -> None:
    font = TTFont(FONT_PATH)
    cmap = font.getBestCmap()
    glyph_set = font.getGlyphSet()
    os2 = font["OS/2"]
    scale = TARGET_X_HEIGHT / os2.sxHeight

    glyphs = []
    advances = {}
    side_bearings = {}
    glyf = font["glyf"]
    positions = []
    cursor = 0

    for index, char in enumerate(WORD):
        if index:
            cursor += KERNING.get(WORD[index - 1 : index + 1], 0)
        positions.append(cursor)
        glyph_name = cmap[ord(char)]
        pen = SVGPathPen(glyph_set)
        glyph_set[glyph_name].draw(pen)
        glyphs.append(pen.getCommands())
        advance = int(glyph_set[glyph_name].width)
        advances[char] = advance
        glyph = glyf[glyph_name]
        side_bearings[char] = [int(glyph.xMin), int(advance - glyph.xMax)]
        cursor += advance

    width = round(cursor * scale + 2 * PADDING)
    height = TARGET_X_HEIGHT + 2 * PADDING
    assert (width, height) == (1482, 240)

    for filename, (main_fill, accent_fill) in VARIANTS.items():
        lines = [
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
            f'width="{width}" height="{height}" role="img" aria-label="markee">',
            f'  <g transform="translate({PADDING} {PADDING + TARGET_X_HEIGHT}) '
            f'scale({scale:.15f} {-scale:.15f})">',
        ]
        for index, (char, position, path_data) in enumerate(zip(WORD, positions, glyphs)):
            fill = accent_fill if index == len(WORD) - 1 else main_fill
            lines.append(
                f'    <path data-glyph="{char}" data-index="{index}" '
                f'd="{path_data}" transform="translate({position} 0)" fill="{fill}"/>'
            )
        lines.extend(("  </g>", "</svg>", ""))
        (LOGO_DIR / filename).write_text("\n".join(lines), encoding="utf-8")

    metadata = {
        "schema_version": 2,
        "wordmark": WORD,
        "glyphs": list(WORD),
        "font_family": "Sora",
        "font_file": FONT_PATH.name,
        "font_weight": 700,
        "font_version": "2.000",
        "font_source": "Google Fonts",
        "font_source_url": SOURCE_URL,
        "font_license": "OFL-1.1",
        "font_sha256": hashlib.sha256(FONT_PATH.read_bytes()).hexdigest(),
        "units_per_em": font["head"].unitsPerEm,
        "cap_height": os2.sCapHeight,
        "x_height": os2.sxHeight,
        "ascender": os2.sTypoAscender,
        "descender": os2.sTypoDescender,
        "target_x_height": TARGET_X_HEIGHT,
        "scale": scale,
        "padding": PADDING,
        "view_box": [0, 0, width, height],
        "advances": advances,
        "kerning": KERNING,
        "positions": positions,
        "side_bearings": side_bearings,
        "variants": VARIANTS,
    }
    (LOGO_DIR / "wordmark-meta.json").write_text(
        json.dumps(metadata, indent=2) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
