#!/usr/bin/env bash
# Downloads Newsreader + Manrope as variable fonts (single file per family)
# from fontsource via jsDelivr. SIL OFL-1.1 licensed; commercial use permitted.
#
# static/_headers serves /fonts/* with a one-year IMMUTABLE cache. The old
# fixed filenames (manrope-wght-normal.woff2 etc.) had no way to signal "this
# changed" to a browser that already cached them — a returning visitor would
# keep the old bytes for up to a year with no way to bust the cache. This
# script fingerprints each font with an 8-char sha256 of its own content
# (the same idea Hugo Pipes uses for main.min.<hash>.css/js, just applied by
# hand here) and rewrites every reference to it, so the filename itself
# changes whenever — and only whenever — the font content changes.
#
# The four places that must agree on the filename:
#   1. assets/css/main.css        (@font-face src: url(...))
#   2. layouts/_default/baseof.html (<link rel="preload" href="...">)
#   3. static/fonts/*.woff2       (the file this script writes)
#   4. static/_headers /fonts/*   (glob — matches any filename, untouched)
# This script owns 1, 2 and 3, so the only manual step left is running it;
# it does not touch static/_headers because the /fonts/* glob already
# matches any filename under that path.

set -euo pipefail

cd "$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"  # repo root, wherever this is invoked from

FONTS_DIR="static/fonts"
CSS_FILE="assets/css/main.css"
BASEOF_FILE="layouts/_default/baseof.html"

mkdir -p "$FONTS_DIR"

BASE_NR="https://cdn.jsdelivr.net/npm/@fontsource-variable/newsreader/files"
BASE_MR="https://cdn.jsdelivr.net/npm/@fontsource-variable/manrope/files"

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

# Newsreader — display serif (variable weight + optical sizing axis)
curl -fLso "$TMP/newsreader-wght-normal.woff2" "$BASE_NR/newsreader-latin-wght-normal.woff2"
curl -fLso "$TMP/newsreader-wght-italic.woff2" "$BASE_NR/newsreader-latin-wght-italic.woff2"

# Manrope — body sans (variable weight)
curl -fLso "$TMP/manrope-wght-normal.woff2" "$BASE_MR/manrope-latin-wght-normal.woff2"

# Remove old static-weight files if present (left over from Cormorant Garamond)
rm -f "$FONTS_DIR"/cormorant-garamond-*.woff2 "$FONTS_DIR"/manrope-400.woff2 \
      "$FONTS_DIR"/manrope-500.woff2 "$FONTS_DIR"/manrope-600.woff2 "$FONTS_DIR"/manrope-700.woff2

# Fingerprints one font and rewrites every /fonts/<stem>[.<hash>].woff2
# reference to the freshly computed name — in the CSS, in the preload
# links, AND on disk (dropping the previous fingerprinted copy so
# static/fonts/ never accumulates stale versions). This is the one step
# that has to run for the four places above to stay in sync: skip it and
# a file gets replaced but every reference still silently points at the
# old, dead filename.
install_font() {
  local stem="$1"  # e.g. manrope-wght-normal
  local src="$TMP/$stem.woff2"
  local hash
  hash="$(shasum -a 256 "$src" | cut -c1-8)"
  local new_name="$stem.$hash.woff2"

  rm -f "$FONTS_DIR/$stem.woff2" "$FONTS_DIR/$stem".*.woff2
  cp "$src" "$FONTS_DIR/$new_name"

  # Matches both the pre-fingerprint filename (first run) and any
  # previously fingerprinted one (later runs), so re-running this script
  # after a font update is the only step needed to keep everything in sync.
  perl -pi -e "s{/fonts/\Q$stem\E(\.[0-9a-f]{8})?\.woff2}{/fonts/$new_name}g" \
    "$CSS_FILE" "$BASEOF_FILE"

  echo "✓ $stem -> $new_name"
}

install_font "newsreader-wght-normal"
install_font "newsreader-wght-italic"
install_font "manrope-wght-normal"

echo
echo "Fonts written to $FONTS_DIR/, references updated in $CSS_FILE and $BASEOF_FILE."
echo "Review the diff, then commit the font files together with those two."
ls -lh "$FONTS_DIR"
