#!/usr/bin/env bash
# Downloads Newsreader + Manrope as variable fonts (single file per family)
# from fontsource via jsDelivr. SIL OFL-1.1 licensed; commercial use permitted.

set -euo pipefail

mkdir -p static/fonts
cd static/fonts

BASE_NR="https://cdn.jsdelivr.net/npm/@fontsource-variable/newsreader/files"
BASE_MR="https://cdn.jsdelivr.net/npm/@fontsource-variable/manrope/files"

# Newsreader — display serif (variable weight + optical sizing axis)
curl -fLso newsreader-wght-normal.woff2 "$BASE_NR/newsreader-latin-wght-normal.woff2"
curl -fLso newsreader-wght-italic.woff2 "$BASE_NR/newsreader-latin-wght-italic.woff2"

# Manrope — body sans (variable weight)
curl -fLso manrope-wght-normal.woff2 "$BASE_MR/manrope-latin-wght-normal.woff2"

# Remove old static-weight files if present (left over from Cormorant Garamond)
rm -f cormorant-garamond-*.woff2 manrope-400.woff2 manrope-500.woff2 manrope-600.woff2 manrope-700.woff2

echo "✓ Downloaded $(ls -1 *.woff2 | wc -l) variable font files to static/fonts/"
ls -lh
