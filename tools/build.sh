#!/usr/bin/env bash
# Build every die. Output goes to out/ (git-ignored).
#
#   tools/build.sh                  STLs, both variants   out/stl/<variant>/<die>.stl
#   tools/build.sh --png            plus PNG previews     out/png/<variant>/<die>.png (implies --ink)
#   tools/build.sh --ink            plus inlay parts      out/stl/<variant>/<die>_ink.stl
#   tools/build.sh --only want      one die
#   tools/build.sh --variant icons  one variant (labelled | icons)
#
# Env: OPENSCAD  path to the openscad binary (default: openscad on PATH)
#      JOBS      parallel renders (default: CPU count)
set -euo pipefail
cd "$(dirname "$0")/.."
export OPENSCAD=${OPENSCAD:-openscad}
JOBS=${JOBS:-$(getconf _NPROCESSORS_ONLN 2>/dev/null || echo 2)}
DICE="setting character object action conflict_a conflict_b emotion want twist resolution"
VARIANTS="labelled icons"
PNG=0
INK=0
while [ $# -gt 0 ]; do
  case "$1" in
    --png) PNG=1 ;;
    --ink) INK=1 ;;
    --only) DICE="$2"; shift ;;
    --variant) VARIANTS="$2"; shift ;;
    *) echo "unknown option: $1" >&2; exit 2 ;;
  esac
  shift
done

command -v "$OPENSCAD" >/dev/null || { echo "openscad not found; set OPENSCAD=/path/to/openscad" >&2; exit 1; }
# Previews are drawn from the finished body and ink STLs.
if [ "$PNG" = 1 ]; then INK=1; fi

for v in $VARIANTS; do
  for d in $DICE; do
    echo "stl $v $d body"
    if [ "$INK" = 1 ]; then echo "stl $v $d ink"; fi
  done
done | xargs -P "$JOBS" -L 1 tools/render_one.sh

if [ "$PNG" = 1 ]; then
  for v in $VARIANTS; do
    for d in $DICE; do echo "png $v $d body"; done
  done | xargs -P "$JOBS" -L 1 tools/render_one.sh
fi
echo "done: $(find out -name '*.stl' | wc -l | tr -d ' ') STL, $(find out -name '*.png' 2>/dev/null | wc -l | tr -d ' ') PNG"
