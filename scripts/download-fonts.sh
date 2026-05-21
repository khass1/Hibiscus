#!/usr/bin/env bash
# Downloads Cormorant Garamond + Manrope woff2 files for self-hosting.
# Run from repo root after the latest patch is extracted.
#
# Source: fontsource.org packages via jsDelivr CDN (mirrors Google Fonts,
# OFL-1.1 licensed for both fonts, commercial use permitted).

set -euo pipefail

mkdir -p static/fonts
cd static/fonts

BASE_CG="https://cdn.jsdelivr.net/npm/@fontsource/cormorant-garamond/files"
BASE_MR="https://cdn.jsdelivr.net/npm/@fontsource/manrope/files"

# Cormorant Garamond — display serif
curl -fLso cormorant-garamond-300.woff2          "$BASE_CG/cormorant-garamond-latin-300-normal.woff2"
curl -fLso cormorant-garamond-400.woff2          "$BASE_CG/cormorant-garamond-latin-400-normal.woff2"
curl -fLso cormorant-garamond-400-italic.woff2   "$BASE_CG/cormorant-garamond-latin-400-italic.woff2"
curl -fLso cormorant-garamond-500.woff2          "$BASE_CG/cormorant-garamond-latin-500-normal.woff2"
curl -fLso cormorant-garamond-500-italic.woff2   "$BASE_CG/cormorant-garamond-latin-500-italic.woff2"
curl -fLso cormorant-garamond-600.woff2          "$BASE_CG/cormorant-garamond-latin-600-normal.woff2"

# Manrope — body sans
curl -fLso manrope-400.woff2 "$BASE_MR/manrope-latin-400-normal.woff2"
curl -fLso manrope-500.woff2 "$BASE_MR/manrope-latin-500-normal.woff2"
curl -fLso manrope-600.woff2 "$BASE_MR/manrope-latin-600-normal.woff2"
curl -fLso manrope-700.woff2 "$BASE_MR/manrope-latin-700-normal.woff2"

echo "✓ Downloaded $(ls -1 *.woff2 | wc -l) font files to static/fonts/"
ls -lh
