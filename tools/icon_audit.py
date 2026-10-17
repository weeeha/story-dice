#!/usr/bin/env python3
"""Check that every face's artwork will print and read, from the built inlay STLs.

    tools/build.sh --ink && python3 tools/icon_audit.py

For each face of each die it takes the artwork from out/stl/<variant>/<die>_ink.stl
(exactly what gets printed), lays it flat and checks:

- detail: ink strokes and gaps narrower than the nozzle (0.2 mm labelled,
  0.4 mm icons). A disk the width of the nozzle is swept over the artwork;
  strokes it can't fit inside close up, gaps it can't fit inside fill in.
- edges: artwork that runs off the flat face into the rounded edge.

Writes out/audit/<variant>.png, one tile per face with its outline: red marks
strokes that won't print, blue marks gaps that will fill in. Prints the faces
that need a look and exits 1 if there are any. Requires numpy and Pillow.
"""
import os
import re
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
NOZZLE = {"labelled": 0.2, "icons": 0.4}   # mm, as in the README
RR, DEPTH = 1.0, 0.6                       # story_die() defaults
PX = 25.0                                  # analysis resolution, px per mm
WIN = 32.0                                 # face window, mm (fits the d8 triangle)
DETAIL_LIMIT = 0.03                        # flag a face losing more than 3% of its ink
EDGE_LIMIT = 0.1                           # flag more than 0.1 mm2 of ink off the face
TILE, PAD, CAP = 220, 8, 40


def shapes():
    src = open(os.path.join(ROOT, "scad", "shapes.scad")).read()
    out = {}
    for m in re.finditer(r'\["(\w+)",\s*(\[\[.*?\]\]),\s*(\[\[.*?\]\]),\s*([-\d., ]+)\]', src, re.S):
        nums = [float(x) for x in m.group(4).split(",")]
        out[m.group(1)] = dict(V=np.array(eval(m.group(2)), float), F=np.array(eval(m.group(3)), float),
                               K=nums[0], glyph=nums[1], tsize=nums[2], iy=nums[3], ty=nums[4])
    return out


def kit():
    src = open(os.path.join(ROOT, "scad", "kit.scad")).read()
    dice = []
    for m in re.finditer(r'\["(\w+)", "(\w+)", \["(#\w+)", "(#\w+)"\], \[(.*?)\]\]', src, re.S):
        faces = re.findall(r'\["([a-z0-9-]+)", "([A-Z0-9 ]*)"', m.group(5))
        dice.append(dict(die=m.group(1), shape=m.group(2), body=m.group(3), ink=m.group(4), faces=faces))
    return dice


def stl(path):
    with open(path) as f:
        pts = [line.split()[1:4] for line in f if line.lstrip().startswith("vertex")]
    return np.array(pts, float).reshape(-1, 3, 3)


def disk(d):
    r = d * PX / 2
    n = 2 * int(np.ceil(r)) + 1
    y, x = np.mgrid[:n, :n] - n // 2
    return (x * x + y * y <= r * r).astype(float)


def conv(a, k):
    s = (a.shape[0] + k.shape[0] - 1, a.shape[1] + k.shape[1] - 1)
    r = np.fft.irfft2(np.fft.rfft2(a, s) * np.fft.rfft2(k, s), s)
    o = k.shape[0] // 2
    return r[o:o + a.shape[0], o:o + a.shape[1]]


def erode(a, k): return conv(1.0 - a, k) < 0.5
def dilate(a, k): return conv(a.astype(float), k) > 0.5


def rgb(h): return tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))


def font(size):
    for p in ("/System/Library/Fonts/Supplemental/Arial Bold.ttf",
              "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf",
              "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"):
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def audit(variant, S, die):
    """One record and one tile per face of one die."""
    F, K, V = S["F"], S["K"], S["V"] * S["K"]
    tri = stl(os.path.join(ROOT, "out", "stl", variant, die["die"] + "_ink.stl"))
    n_all, d_all = F[:, 0:3], F[:, 6] * K + RR
    dist = tri.mean(axis=1) @ n_all.T - d_all          # depth below each face plane
    owner = dist.argmax(axis=1)
    cr = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    area = np.linalg.norm(cr, axis=1) / 2
    tn = cr / (2 * area[:, None] + 1e-12)
    N, k = int(WIN * PX), disk(NOZZLE[variant])
    # rows above `split` hold the icon, below it the label (labelled set only)
    split = N if variant == "icons" else int(N / 2 - ((S["iy"] - S["glyph"] / 2) + (S["ty"] + S["tsize"] / 2)) / 2 * PX)
    out = []
    for i, (icon, label) in enumerate(die["faces"]):
        n, u = n_all[i], F[i, 3:6]
        r = np.cross(u, n)
        mine = (owner == i) & (dist[:, i] > -DEPTH - 0.2)
        top = mine & (tn @ n > 0.1)
        off = top & (tn @ n < 0.9945)                  # tilted more than 6 degrees: off the flat face
        edge = float((area[off] * (tn[off] @ n)).sum())
        to_px = lambda p: (N / 2 + (p @ r) * PX, N / 2 - (p @ u) * PX)
        img = Image.new("L", (N, N), 0)
        draw = ImageDraw.Draw(img)
        for t in tri[top]:
            draw.polygon([to_px(p) for p in t], fill=255)
        A = np.array(img) > 127
        thin_ink = A & ~dilate(erode(A.astype(float), k), k)
        thin_gap = erode(dilate(A, k).astype(float), k) & ~A

        def lost(rows):
            ink = A[rows].sum()
            return float((thin_ink[rows].sum() + thin_gap[rows].sum()) / ink) if ink else 0.0

        rec = dict(die=die["die"], label=label, icon=icon, edge=edge,
                   icon_detail=lost(slice(0, split)),
                   label_detail=lost(slice(split, N)) if split < N else 0.0)
        out.append(rec)

        tile = np.empty((N, N, 3), np.uint8)
        tile[:] = rgb(die["body"])
        tile[A] = rgb(die["ink"])
        tile[thin_ink] = (255, 0, 60)
        tile[thin_gap] = (0, 170, 255)
        im = Image.fromarray(tile)
        face_v = V[np.abs(V @ n - F[i, 6] * K) < 1e-3]
        c = face_v.mean(axis=0)
        order = np.argsort(np.arctan2((face_v - c) @ u, (face_v - c) @ r))
        ImageDraw.Draw(im).polygon([to_px(p - n * (p @ n) + n * F[i, 6] * K) for p in face_v[order]],
                                   outline=(120, 120, 120), width=4)
        rec["tile"] = im.resize((TILE, TILE), Image.LANCZOS)
    return out


def sheet(variant, rows, path):
    cols = max(len(r) for r in rows)
    im = Image.new("RGB", (PAD + cols * (TILE + PAD), PAD + len(rows) * (TILE + CAP + PAD)), (24, 22, 20))
    d, f = ImageDraw.Draw(im), font(13)
    for y, recs in enumerate(rows):
        for x, rec in enumerate(recs):
            px, py = PAD + x * (TILE + PAD), PAD + y * (TILE + CAP + PAD)
            im.paste(rec["tile"], (px, py))
            bad = rec["edge"] > EDGE_LIMIT or max(rec["icon_detail"], rec["label_detail"]) > DETAIL_LIMIT
            d.text((px + 2, py + TILE + 4), f'{rec["label"]} · {rec["icon"]}', fill=(236, 227, 212), font=f)
            d.text((px + 2, py + TILE + 21),
                   f'detail {100 * max(rec["icon_detail"], rec["label_detail"]):.1f}%  edge {rec["edge"]:.2f} mm²',
                   fill=(255, 110, 110) if bad else (160, 150, 140), font=f)
    im.save(path, optimize=True)
    print("wrote", os.path.relpath(path, ROOT), im.size)


def main():
    S, dice = shapes(), kit()
    os.makedirs(os.path.join(ROOT, "out", "audit"), exist_ok=True)
    flagged = []
    for variant in ("labelled", "icons"):
        rows = []
        for die in dice:
            if not os.path.exists(os.path.join(ROOT, "out", "stl", variant, die["die"] + "_ink.stl")):
                sys.exit(f"missing out/stl/{variant}/{die['die']}_ink.stl; run tools/build.sh --ink first")
            recs = audit(variant, S[die["shape"]], die)
            rows.append(recs)
            for r in recs:
                why = []
                if r["icon_detail"] > DETAIL_LIMIT:
                    why.append(f'icon loses {100 * r["icon_detail"]:.1f}% at {NOZZLE[variant]} mm')
                if r["label_detail"] > DETAIL_LIMIT:
                    why.append(f'label loses {100 * r["label_detail"]:.1f}% at {NOZZLE[variant]} mm')
                if r["edge"] > EDGE_LIMIT:
                    why.append(f'{r["edge"]:.2f} mm² runs off the face')
                if why:
                    flagged.append(f'{variant:8} {r["die"]:11} {r["label"]:8} {r["icon"]:18} ' + "; ".join(why))
        sheet(variant, rows, os.path.join(ROOT, "out", "audit", f"{variant}.png"))
    print(f"{len(flagged)} face(s) to look at" + (":" if flagged else ""))
    print("\n".join(flagged))
    sys.exit(1 if flagged else 0)


if __name__ == "__main__":
    main()
