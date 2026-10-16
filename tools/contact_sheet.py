#!/usr/bin/env python3
"""Compose the per-die PNG previews into one image for the README.

    tools/build.sh --png && python3 tools/contact_sheet.py

Writes renders/kit.png (labelled) and renders/kit-icons.png. Requires Pillow.
"""
import os

from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
DICE = [
    ("setting", "SETTING  d8"), ("character", "CHARACTER  d8"), ("object", "OBJECT  d6"),
    ("action", "ACTION  d6"), ("conflict_a", "CONFLICT  A"), ("conflict_b", "CONFLICT  B"),
    ("emotion", "EMOTION  d12"), ("want", "WANT  d10"), ("twist", "TWIST  d8"),
    ("resolution", "RESOLUTION  d6"),
]
COLS, PAD, LAB, TILE = 5, 12, 30, 400
BG, FG = (24, 22, 20), (236, 227, 212)


def font(size):
    for p in ("/System/Library/Fonts/Supplemental/Arial Bold.ttf",
              "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf",
              "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"):
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def sheet(variant, out):
    rows = (len(DICE) + COLS - 1) // COLS
    im = Image.new("RGB", (COLS * TILE + (COLS + 1) * PAD, rows * (TILE + LAB) + (rows + 1) * PAD), BG)
    d = ImageDraw.Draw(im)
    f = font(15)
    for i, (name, title) in enumerate(DICE):
        r, c = divmod(i, COLS)
        x, y = PAD + c * (TILE + PAD), PAD + r * (TILE + LAB + PAD)
        tile = Image.open(os.path.join(ROOT, "out", "png", variant, f"{name}.png")).convert("RGB")
        im.paste(tile.resize((TILE, TILE), Image.LANCZOS), (x, y))
        d.text((x + 4, y + TILE + 8), title, fill=FG, font=f)
    im.save(out, optimize=True)
    print("wrote", os.path.relpath(out, ROOT), im.size)


if __name__ == "__main__":
    os.makedirs(os.path.join(ROOT, "renders"), exist_ok=True)
    sheet("labelled", os.path.join(ROOT, "renders", "kit.png"))
    if os.path.isdir(os.path.join(ROOT, "out", "png", "icons")):
        sheet("icons", os.path.join(ROOT, "renders", "kit-icons.png"))
