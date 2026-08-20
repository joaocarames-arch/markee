#!/usr/bin/env python3
"""Render Markee wordmark validation boards at required sizes."""

from io import BytesIO
from pathlib import Path

import cairosvg
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
LOGOS = ROOT / "logos"
OUTPUT = Path("/tmp/markee-max3-brand-screenshots")
OUTPUT.mkdir(parents=True, exist_ok=True)

for variant, background in (("dark", "#08090A"), ("light", "#FFFFFF")):
    source = LOGOS / f"markee-wordmark-{variant}.svg"
    board = Image.new("RGB", (1100, 520), background)
    draw = ImageDraw.Draw(board)
    foreground = "#E8E8E8" if variant == "dark" else "#08090A"
    draw.text((40, 24), f"markee v2 · {variant} · Sora Bold paths", fill=foreground)
    y = 90
    for height in (24, 32, 132):
        width = round(height * 1482 / 240)
        png = cairosvg.svg2png(
            url=str(source), output_width=width, output_height=height
        )
        image = Image.open(BytesIO(png)).convert("RGBA")
        board.paste(image, (180, y), image)
        draw.text((40, y + max(0, height // 2 - 8)), f"{height}px", fill=foreground)
        y += height + 70
    board.save(OUTPUT / f"wordmark-{variant}-24-32-132.png")
