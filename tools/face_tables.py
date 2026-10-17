#!/usr/bin/env python3
"""Compute per-face frames for the story-dice solids and write scad/shapes.scad.

Each solid is the convex hull of a small vertex set. For every hull face this
stores the outward normal n, an in-plane "up" vector u (where the top of the
artwork points) and the plane distance d at unit scale. scad/story_die.scad
places one icon and one label on each face using these frames.

Sizing: the polyhedral dice are scaled so every face has the same inscribed
radius (8 mm), which keeps icons the same size on every die. The Conflict
pair is sized by its hexagon plane distance instead.

Layout: each face carries an icon above a label. Per shape we pick which way
"up" points and, where it helps, slide the stack along up so the label sits
where the face is widest while the icon still fits. The resulting label room
(lw) is stored so the library can condense words that would cross an edge.
The icon-only set's larger icon goes where the face has the most room: centred
on symmetric faces, towards the wide end of a d10 kite.

Only needed when adding or changing a solid. The generated scad/shapes.scad is
committed, so building the dice needs OpenSCAD alone. Requires numpy.

    python3 tools/face_tables.py
"""
import itertools
import json
import math
import os

import numpy as np

PHI = (1 + 5 ** 0.5) / 2
# Ring height for a pentagonal trapezohedron with planar kite faces.
# Apex/ring ratio must be exactly (1+cos36)/(1-cos36) or the faces bend.
C10 = 1.0 / ((1 + math.cos(math.radians(36))) / (1 - math.cos(math.radians(36))))
RR = 1.0           # corner rounding: the body is a hull of spheres this radius (mm)
TARGET_RHO = 8.0   # face inscribed radius for the polyhedral dice (mm)


def unit(v):
    v = np.asarray(v, float)
    n = np.linalg.norm(v)
    return v / n if n > 1e-12 else v


def verts(s):
    if s == "d6":
        return [[x, y, z] for x in (-1, 1) for y in (-1, 1) for z in (-1, 1)]
    if s == "d8":
        return [[1, 0, 0], [-1, 0, 0], [0, 1, 0], [0, -1, 0], [0, 0, 1], [0, 0, -1]]
    if s == "d12":
        v = [[x, y, z] for x in (-1, 1) for y in (-1, 1) for z in (-1, 1)]
        v += [[0, y / PHI, z * PHI] for y in (-1, 1) for z in (-1, 1)]
        v += [[x / PHI, y * PHI, 0] for x in (-1, 1) for y in (-1, 1)]
        v += [[x * PHI, 0, z / PHI] for x in (-1, 1) for z in (-1, 1)]
        return v
    if s == "d10":
        v = [[0, 0, 1], [0, 0, -1]]
        v += [[math.cos(math.radians(72 * i)), math.sin(math.radians(72 * i)), C10] for i in range(5)]
        v += [[math.cos(math.radians(72 * i + 36)), math.sin(math.radians(72 * i + 36)), -C10] for i in range(5)]
        return v
    if s == "tt":  # truncated tetrahedron: permutations of (3,1,1), even number of minus signs
        out = []
        for sx, sy, sz in [(1, 1, 1), (1, -1, -1), (-1, 1, -1), (-1, -1, 1)]:
            for p in [(3, 1, 1), (1, 3, 1), (1, 1, 3)]:
                out.append([sx * p[0], sy * p[1], sz * p[2]])
        return out
    raise ValueError(s)


def hull_faces(V, eps=1e-5):
    """Brute force: every vertex triple whose plane has all points on one side."""
    f = {}
    for i, j, k in itertools.combinations(range(len(V)), 3):
        n = np.cross(V[j] - V[i], V[k] - V[i])
        L = np.linalg.norm(n)
        if L < 1e-9:
            continue
        n = n / L
        d = float(n @ V[i])
        if (V @ n).max() > d + eps:
            n, d = -n, -d
            if (V @ n).max() > d + eps:
                continue
        f[tuple(np.round(n, 4))] = d
    return [(np.array(k, float), v) for k, v in f.items()]


def face_frames(V):
    """One record per hull face: normal, plane distance, inradius, ordered vertices."""
    out = []
    for n, d in hull_faces(V):
        n = unit(n)
        d = float((V @ n).max())
        fv = V[(V @ n) > d - 1e-3]
        u = []
        for p in fv:
            if not any(np.linalg.norm(p - q) < 1e-6 for q in u):
                u.append(p)
        fv = np.array(u)
        c = fv.mean(axis=0)
        e1 = unit(fv[0] - c)
        e2 = np.cross(n, e1)
        ang = np.arctan2((fv - c) @ e2, (fv - c) @ e1)
        ang[np.isclose(ang, -np.pi)] = np.pi  # a vertex straight across: always +pi, never noise-dependent
        fv = fv[np.argsort(ang)]
        m = len(fv)
        ds = [float(np.linalg.norm(np.cross(fv[(i + 1) % m] - fv[i], c - fv[i])) / np.linalg.norm(fv[(i + 1) % m] - fv[i]))
              for i in range(m) if np.linalg.norm(fv[(i + 1) % m] - fv[i]) > 1e-9]
        out.append(dict(n=n, d=d, rho=min(ds), fv=fv, c=c))
    return out


def up_vector(face, rule, faces):
    """Direction the top of the artwork points, in the face plane.

    vertex      towards the first corner in angular order (d8, d12: apex up)
    edge        towards the middle of the first edge (d6: text square to the edges)
    far-vertex  towards the corner farthest from the centre (d10: the kite's long tip)
    edge-tri    towards the first edge shared with a triangle (truncated tetrahedron)
    """
    fv, c, n = face["fv"], face["c"], face["n"]
    m = len(fv)
    if rule == "vertex":
        top = fv[0]
    elif rule == "edge":
        top = (fv[0] + fv[1]) / 2
    elif rule == "far-vertex":
        top = fv[int(np.argmax(np.linalg.norm(fv - c, axis=1)))]
    elif rule == "edge-tri":
        tris = [o["fv"] for o in faces if len(o["fv"]) == 3]
        on_tri = lambda p, tri: any(np.linalg.norm(p - t) < 1e-6 for t in tri)
        top = next((fv[i] + fv[(i + 1) % m]) / 2 for i in range(m)
                   if any(on_tri(fv[i], t) and on_tri(fv[(i + 1) % m], t) for t in tris))
    else:
        raise ValueError(rule)
    v = top - c
    return unit(v - n * (v @ n))


EDGE_MARGIN = 0.6   # keep artwork this far inside the flat part of a face (mm)
GAP = 0.15 * TARGET_RHO


def face_polygon(face, up, K):
    """Flat face outline in artwork coordinates (mm): x = right, y = up, origin at the cut centre."""
    n = face["n"]
    foot = n * face["d"]
    r = np.cross(up, n)
    return [(float((p - foot) @ r * K), float((p - foot) @ up * K)) for p in face["fv"]]


def inset(poly, m):
    P = np.array(poly)
    c = P.mean(axis=0)
    lines = []
    for i in range(len(P)):
        a, b = P[i], P[(i + 1) % len(P)]
        t = (b - a) / np.linalg.norm(b - a)
        nn = np.array([t[1], -t[0]])
        if nn @ ((a + b) / 2 - c) < 0:
            nn = -nn
        lines.append((a - nn * m, t))
    out = []
    for i in range(len(P)):
        (p1, t1), (p2, t2) = lines[i - 1], lines[i]
        k = np.linalg.solve(np.array([t1, -t2]).T, p2 - p1)
        out.append(tuple(p1 + t1 * k[0]))
    return out


def room(poly, y0, y1):
    """Width of the widest x-centred box spanning y0..y1 inside a convex polygon."""
    best = 1e9
    for y in np.linspace(y0, y1, 25):
        xs = []
        for i in range(len(poly)):
            (x1, ya), (x2, yb) = poly[i], poly[(i + 1) % len(poly)]
            if (ya - y) * (yb - y) <= 0 and ya != yb:
                xs.append(x1 + (y - ya) * (x2 - x1) / (yb - ya))
        if len(xs) < 2:
            return 0.0
        best = min(best, min(max(xs), -min(xs)))
    return 2 * best


def stack(glyph, tsize, shift):
    """Icon centre and label centre for an icon-over-label stack moved `shift` along up."""
    h = glyph + GAP + tsize
    return shift + h / 2 - glyph / 2, shift + h / 2 - glyph - GAP - tsize / 2


def layout(face, up, K, glyph, tsize, shift):
    """Pick the stack position and return (iy, ty, label room in mm)."""
    poly = inset(face_polygon(face, up, K), EDGE_MARGIN)
    cap = 0.98 * tsize  # Liberation Sans Bold capitals are ~0.98 x size tall

    def label_room(sh):
        iy, ty = stack(glyph, tsize, sh)
        return room(poly, ty - cap / 2, ty + cap / 2)

    def icon_fits(sh):
        iy, _ = stack(glyph, tsize, sh)
        return room(poly, iy - glyph / 2, iy + glyph / 2) >= glyph

    if shift == "auto":  # slide the stack to give the label the most room
        options = [round(x, 1) for x in np.arange(-6, 6.01, 0.1)]
        shift = max((sh for sh in options if icon_fits(sh)), key=lambda sh: (round(label_room(sh), 1), -abs(sh)))
    iy, ty = stack(glyph, tsize, shift)
    return iy, ty, label_room(shift)


ICON_ONLY = 1.45   # the icon-only set's icons are this much larger than the labelled set's


def solo(face, up, K, glyph, shift):
    """Icon offset along up for the icon-only set: the spot with the most room."""
    if shift != "auto":
        return 0.0
    poly = inset(face_polygon(face, up, K), EDGE_MARGIN)
    g = glyph * ICON_ONLY
    options = [round(x, 1) + 0.0 for x in np.arange(-6, 6.01, 0.1)]   # + 0.0: no "-0.000"
    return max(options, key=lambda sh: (round(room(poly, sh - g / 2, sh + g / 2), 1), -abs(sh)))


def r6(x):
    return [round(float(v), 6) for v in x]


LABEL = round(0.42 * TARGET_RHO, 2)  # 3.36 mm, the same on every die

# up: see up_vector(). shift: "auto" slides the stack for label room, 0 keeps it centred.
# sides: label only faces with this many corners. plane: size by face distance instead of inradius.
SOLIDS = {
    "d6":  dict(up="edge",       glyph=TARGET_RHO, shift=0),
    "d8":  dict(up="vertex",     glyph=TARGET_RHO, shift=0),
    "d10": dict(up="far-vertex", glyph=TARGET_RHO, shift="auto"),
    "d12": dict(up="vertex",     glyph=TARGET_RHO, shift=0),
    "tt":  dict(up="edge-tri",   glyph=9.5,        shift="auto", sides=6, plane=7.497),
}


def build():
    rows = []
    for s, spec in SOLIDS.items():
        V = np.array(verts(s), float)
        fr = face_frames(V)
        faces = [f for f in fr if "sides" not in spec or len(f["fv"]) == spec["sides"]]
        if "plane" in spec:   # Conflict: sized to the July 2026 prototype's hexagon plane
            K = (spec["plane"] - RR) / faces[0]["d"]
        else:                 # constant face inradius
            K = TARGET_RHO / round(faces[0]["rho"], 6)
        ups = [up_vector(f, spec["up"], fr) for f in faces]
        iy, ty, lw = layout(faces[0], ups[0], K, spec["glyph"], LABEL, spec["shift"])
        oy = solo(faces[0], ups[0], K, spec["glyph"], spec["shift"])
        F = [[*r6(f["n"]), *r6(u), round(f["d"], 6)] for f, u in zip(faces, ups)]
        rows.append((s, verts(s), F, K, spec["glyph"], LABEL, iy, ty, lw, spec["glyph"] * ICON_ONLY, oy))
    return rows


def emit(rows, path):
    lines = [
        "// GENERATED by tools/face_tables.py. Edit that script, not this file.",
        "//",
        "// Shape record: [name, V, F, K, glyph, tsize, iy, ty, lw, og, oy]",
        "//   V      unit-scale vertices; the body is hull() of spheres at V*K",
        "//   F      one frame per labelled face: [nx, ny, nz, ux, uy, uz, d]",
        "//          n = outward normal, u = artwork up, d = plane distance at unit scale",
        "//   K      scale to millimetres",
        "//   glyph  icon size (mm); tsize label cap size (mm)",
        "//   iy, ty icon and label offsets along u (mm)",
        "//   lw     label room (mm): wider labels are condensed to fit",
        "//   og, oy icon size and offset along u for the icon-only set (mm)",
        "",
        "SHAPES = [",
    ]
    recs = []
    for s, V, F, K, glyph, tsize, iy, ty, lw, og, oy in rows:
        recs.append(
            f'  ["{s}",\n    {json.dumps(V)},\n    {json.dumps(F)},\n'
            f"    {K:.6f}, {glyph:.2f}, {tsize:.2f}, {iy:.3f}, {ty:.3f}, {lw:.2f}, {og:.2f}, {oy:.3f}]"
        )
    lines.append(",\n".join(recs))
    lines.append("];")
    with open(path, "w") as fh:
        fh.write("\n".join(lines) + "\n")


if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    rows = build()
    emit(rows, os.path.join(here, "..", "scad", "shapes.scad"))
    for s, V, F, K, glyph, tsize, iy, ty, lw, og, oy in rows:
        R = max(np.linalg.norm(np.array(V, float), axis=1))
        print(f"{s:4} faces={len(F):2}  across={2 * R * K + 2 * RR:5.1f} mm  icon={glyph:.1f}  "
              f"label={tsize}  iy={iy:+.2f} ty={ty:+.2f}  label room={lw:.1f} mm  "
              f"icon-only={og:.1f} oy={oy:+.2f}")
