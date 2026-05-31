#!/usr/bin/env -S pkgx bash
#
# Rasterise les SVG logos en PNG pour publication GitHub (org avatar,
# README banner, social preview card). Les SVG restent canoniques ;
# ces PNG sont juste pour les surfaces qui n'acceptent pas SVG (GitHub
# org avatar upload, social-preview card, Slack/Mastodon scrapers).
#
# Picks the first rasterizer available, in order :
#   rsvg-convert (librsvg)    — le plus rapide, output le plus net
#   magick (ImageMagick 7)    — fallback ; gère le compositing du
#                                social-preview 1280×640
#
# Cibles produites dans static/logo/png/ :
#
#   <base>-256.png       carré 256×256          — favicons, thumbnails
#   <base>-512.png       carré 512×512          — avatar @2x
#   <base>-1024.png      carré 1024×1024        — print / hero @4x
#   weft-wordmark-h-1024.png    wordmark wide   — README header bandeau
#   weft-lockup-vertical-512.png lockup carré   — avatar GitHub org
#   weft-social-preview.png     1280×640        — GitHub Social Preview
#                                                  (Settings → Social
#                                                  preview, 1280×640 spec)

set -euo pipefail
cd "$(dirname "$0")"
mkdir -p png

pick() {
  for t in "$@"; do command -v "$t" >/dev/null 2>&1 && { echo "$t"; return; }; done
  return 1
}

# Rasterisation à taille définie. $1 = SVG source ; $2 = largeur cible ;
# $3 = hauteur cible (vide = proportionnel au viewBox) ; $4 = PNG sortie.
if RSVG=$(pick rsvg-convert); then
  RENDER() {
    local src=$1 w=$2 h=$3 dst=$4
    if [ -n "$h" ]; then "$RSVG" -w "$w" -h "$h" -o "$dst" "$src"
    else                 "$RSVG" -w "$w"          -o "$dst" "$src"
    fi
  }
elif MAG=$(pick magick convert); then
  RENDER() {
    local src=$1 w=$2 h=$3 dst=$4
    local size=$w
    [ -n "$h" ] && size="${w}x${h}"
    # -resize must follow the source argument, not precede it ;
    # magick's CLI grammar is "operand then operator".
    "$MAG" -background none -density 384 "$src" -resize "$size" "$dst"
  }
else
  echo "build-logos.sh : aucun rasterizer trouvé." >&2
  echo "  pkgx +librsvg.org bash ./build-logos.sh    # le plus propre" >&2
  echo "  pkgx +imagemagick.org bash ./build-logos.sh # fallback" >&2
  exit 1
fi

# Carrés : weft-A-* (256×256 viewBox natif).
for src in weft-A-mono.svg weft-A-weave.svg; do
  base=${src%.svg}
  echo "raster: png/${base}-256.png" ;  RENDER "$src" 256  "" "png/${base}-256.png"
  echo "raster: png/${base}-512.png" ;  RENDER "$src" 512  "" "png/${base}-512.png"
  echo "raster: png/${base}-1024.png" ; RENDER "$src" 1024 "" "png/${base}-1024.png"
done

# Wordmark horizontal : viewBox 480×128, ratio 15:4. Bandeau README.
echo "raster: png/weft-wordmark-h-512.png"
RENDER weft-wordmark-h.svg 512  "" png/weft-wordmark-h-512.png
echo "raster: png/weft-wordmark-h-1024.png"
RENDER weft-wordmark-h.svg 1024 "" png/weft-wordmark-h-1024.png
echo "raster: png/weft-wordmark-h-2048.png"
RENDER weft-wordmark-h.svg 2048 "" png/weft-wordmark-h-2048.png

# Lockup vertical : viewBox 480×360. Bon pour l'avatar org GitHub
# (qui aime du carré-ish, 460×460 affiché). Garde le ratio source.
echo "raster: png/weft-lockup-vertical-512.png"
RENDER weft-lockup-vertical.svg 512  "" png/weft-lockup-vertical-512.png
echo "raster: png/weft-lockup-vertical-1024.png"
RENDER weft-lockup-vertical.svg 1024 "" png/weft-lockup-vertical-1024.png

# Social preview card 1280×640. GitHub Social Preview spec — uploaded
# as-is via Settings → Social preview on each repo. Sourced from a
# dedicated weft-social-preview.svg (white canvas, lockup centered)
# so the rasterization stays pure-SVG (no magick compositing — keeps
# the pkgx env single-rasterizer + uploads pixel-perfect).
echo "raster: png/weft-social-preview.png (1280×640)"
RENDER weft-social-preview.svg 1280 640 png/weft-social-preview.png

echo "done — PNG générés dans static/logo/png/"
