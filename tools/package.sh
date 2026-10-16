#!/usr/bin/env bash
# Zip the built STLs for a release: out/story-dice-<variant>-stl.zip
# Run tools/build.sh first.
set -euo pipefail
cd "$(dirname "$0")/.."
made=0
for v in labelled icons; do
  [ -d "out/stl/$v" ] || continue
  tmp=$(mktemp -d)
  dir="$tmp/story-dice-$v"
  mkdir -p "$dir"
  cp out/stl/"$v"/*.stl "$dir/"
  cp README.md LICENSE-MODELS.md "$dir/"
  cp icons/LICENSE "$dir/ICONS-LICENSE.txt"
  rm -f "out/story-dice-$v-stl.zip"
  (cd "$tmp" && zip -qr "story-dice-$v-stl.zip" "story-dice-$v")
  mv "$tmp/story-dice-$v-stl.zip" out/
  rm -rf "$tmp"
  made=$((made + 1))
done
[ "$made" -gt 0 ] || { echo "nothing to package; run tools/build.sh first" >&2; exit 1; }
ls -l out/*.zip
