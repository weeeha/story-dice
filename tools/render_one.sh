#!/usr/bin/env bash
# Render one die. Called by build.sh: render_one.sh <stl|png> <variant> <die> <body|ink>
# Fails (exit 255, which stops xargs) on any OpenSCAD error, warning or open mesh.
set -euo pipefail
kind=$1 variant=$2 die=$3 part=$4
suffix=""
if [ "$part" = ink ]; then suffix="_ink"; fi
out="out/$kind/$variant/$die$suffix.$kind"
mkdir -p "$(dirname "$out")"
args=(-o "$out" -D "die=\"$die\"" -D "variant=\"$variant\"" -D "part=\"$part\"")
if [ "$kind" = png ]; then args+=(-D from_stl=true --imgsize=800,800 --colorscheme=Tomorrow --viewall --autocenter); fi
start=$(date +%s)
if ! log=$("${OPENSCAD:-openscad}" "${args[@]}" scad/kit.scad 2>&1); then
  echo "FAIL $out"; echo "$log"; exit 255
fi
bad=$(echo "$log" | grep -v -i fontconfig | grep -iE "not closed|error|warning" || true)
if [ -n "$bad" ]; then echo "FAIL $out"; echo "$bad"; exit 255; fi
echo "ok   $out  $(( $(date +%s) - start ))s"
