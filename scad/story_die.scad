// story_die.scad: one story die = a rounded convex solid with an icon and a
// label debossed into each face. Face geometry lives in shapes.scad.
//
//   story_die("d8", icons=["buildings", ...], labels=["CITY", ...]);
//
// icons    Phosphor Fill icon names; the file is <icon_dir>/<name>-fill.svg
// labels   one word per face, "" for none; words too wide for the face are
//          condensed to fit
// labelled false = icons only, 1.45x larger and centred (prints on a 0.4 mm nozzle)
// part     "body" = the die with recessed artwork
//          "ink"  = just the 0.6 mm inlays, for a second filament colour
// colors   [body, ink] for previews only; STL export ignores colour

include <shapes.scad>

// Label fitting. Ink widths at size 1 of Liberation Sans Bold capitals and
// digits, measured in OpenSCAD, plus the average gap between letters. A label
// wider than its face's room (lw in shapes.scad) is condensed horizontally.
// Other characters count as 1.0 wide, which errs towards condensing.
LABEL_CHARS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 ";
LABEL_INK = [0.932, 0.847, 0.908, 0.852, 0.779, 0.705, 0.937, 0.816, 0.200, 0.656, 0.897, 0.713, 0.971, 0.816, 0.965, 0.786, 0.965, 0.882, 0.832, 0.818, 0.835, 0.907, 1.308, 0.902, 0.880, 0.767, 0.660, 0.646, 0.669, 0.690, 0.744, 0.691, 0.671, 0.652, 0.686, 0.673, 0.28];
LABEL_TRACK = 0.094;

function _sum(v, i = 0) = i >= len(v) ? 0 : v[i] + _sum(v, i + 1);
function label_char_w(c) = let (i = search(c, LABEL_CHARS)) len(i) > 0 ? LABEL_INK[i[0]] : 1.0;
// 5% safety: the estimate is within 5% of OpenSCAD's real widths for every label in the kit.
function label_width(s, size) =
  size * 1.05 * (_sum([for (c = s) label_char_w(c)]) + (len(s) - 1) * LABEL_TRACK);

function story_shape(name) =
  let (hit = [for (i = [0:len(SHAPES) - 1]) if (SHAPES[i][0] == name) i])
  assert(len(hit) == 1, str("unknown shape: ", name))
  SHAPES[hit[0]];

module story_die(shape, icons, labels, labelled = true, part = "body",
                 font = "Liberation Sans:style=Bold", icon_dir = "../icons",
                 rr = 1.0, depth = 0.6, icon_only_scale = 1.45,
                 colors = ["SteelBlue", "Orange"]) {
  $fn = 32;
  S = story_shape(shape);
  V = S[1]; F = S[2]; K = S[3];
  assert(len(icons) == len(F), str(shape, " has ", len(F), " faces, got ", len(icons), " icons"));
  glyph = labelled ? S[4] : S[4] * icon_only_scale;
  tsize = S[5];
  iy = labelled ? S[6] : 0;
  ty = S[7];
  lw = S[8];

  module body() hull() for (q = V) translate(q * K) sphere(r = rr);

  module cut(i) {
    n = [F[i][0], F[i][1], F[i][2]];
    u = [F[i][3], F[i][4], F[i][5]];
    d = F[i][6] * K + rr;
    r = cross(u, n);
    multmatrix([[r[0], u[0], n[0], n[0] * d],
                [r[1], u[1], n[1], n[1] * d],
                [r[2], u[2], n[2], n[2] * d],
                [0, 0, 0, 1]])
      translate([0, 0, -depth]) linear_extrude(height = depth + 0.6) {
        // offset() fuses icon parts that only touch at an edge (Phosphor's tree
        // does this); without it CGAL rejects the mesh as not closed.
        translate([0, iy, 0]) offset(delta = 0.01) resize([glyph, glyph, 0], auto = true)
          import(str(icon_dir, "/", icons[i], "-fill.svg"), center = true);
        if (labelled && labels[i] != "")
          translate([0, ty, 0]) scale([min(1, lw / label_width(labels[i], tsize)), 1])
            text(labels[i], size = tsize, font = font, halign = "center", valign = "center");
      }
  }

  // Grouping the cutters in one union() keeps CGAL from failing on dense faces.
  module cuts() union() for (i = [0:len(F) - 1]) cut(i);

  if (part == "body") difference() { color(colors[0]) body(); color(colors[1]) cuts(); }
  else if (part == "ink") color(colors[1]) intersection() { body(); cuts(); }
  else assert(false, str("part must be body or ink, got ", part));
}
