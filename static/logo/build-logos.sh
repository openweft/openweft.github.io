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
# $5 (optionnel) = background color CSS — vide / "none" = transparent ;
# "white" / "#ffffff" pour le fond blanc des surfaces GitHub.
if RSVG=$(pick rsvg-convert); then
  RENDER() {
    local src=$1 w=$2 h=$3 dst=$4 bg=${5:-}
    local args=(-w "$w")
    [ -n "$h" ] && args+=(-h "$h")
    [ -n "$bg" ] && args+=(--background-color "$bg")
    args+=(-o "$dst" "$src")
    "$RSVG" "${args[@]}"
  }
elif MAG=$(pick magick convert); then
  RENDER() {
    local src=$1 w=$2 h=$3 dst=$4 bg=${5:-}
    local size=$w
    [ -n "$h" ] && size="${w}x${h}"
    local mbg="none"
    [ -n "$bg" ] && mbg="$bg"
    # -resize must follow the source argument, not precede it ;
    # magick's CLI grammar is "operand then operator".
    "$MAG" -background "$mbg" -density 384 "$src" -resize "$size" -flatten "$dst"
  }
else
  echo "build-logos.sh : aucun rasterizer trouvé." >&2
  echo "  pkgx +librsvg.org bash ./build-logos.sh    # le plus propre" >&2
  echo "  pkgx +imagemagick.org bash ./build-logos.sh # fallback" >&2
  exit 1
fi

# RENDER_BOTH génère deux PNG : transparent + fond blanc. Les surfaces
# GitHub (upload avatar, social preview) préfèrent le fond blanc pour
# rendre lisible aussi bien en mode clair qu'en mode sombre — la
# version transparente reste utile pour les contextes où le composant
# pose son propre fond (badges, embeds).
RENDER_BOTH() {
  local src=$1 w=$2 h=$3 dst=$4
  RENDER "$src" "$w" "$h" "$dst"
  # weft-<base>-WxH.png  →  weft-<base>-WxH-white.png
  local white="${dst%.png}-white.png"
  RENDER "$src" "$w" "$h" "$white" white
}

# Carrés : weft-A-* (256×256 viewBox natif). Chaque taille a une
# variante transparente ET une variante fond blanc — les surfaces
# GitHub upload (avatar, social preview) veulent du blanc, les
# composants UI qui posent leur propre fond préfèrent le transparent.
for src in weft-A-mono.svg weft-A-weave.svg; do
  base=${src%.svg}
  for size in 256 512 1024; do
    echo "raster: png/${base}-${size}.png"
    RENDER_BOTH "$src" "$size" "" "png/${base}-${size}.png"
  done
done

# Wordmark horizontal : viewBox 480×128, ratio 15:4. Bandeau README.
for size in 512 1024 2048; do
  echo "raster: png/weft-wordmark-h-${size}.png"
  RENDER_BOTH weft-wordmark-h.svg "$size" "" "png/weft-wordmark-h-${size}.png"
done

# Lockup vertical : viewBox 480×360. Bon pour l'avatar org GitHub
# (qui aime du carré-ish, 460×460 affiché). Garde le ratio source.
for size in 512 1024; do
  echo "raster: png/weft-lockup-vertical-${size}.png"
  RENDER_BOTH weft-lockup-vertical.svg "$size" "" "png/weft-lockup-vertical-${size}.png"
done

# Social preview card 1280×640. GitHub Social Preview spec — uploaded
# as-is via Settings → Social preview on each repo. Sourced from a
# dedicated weft-social-preview.svg (white canvas, lockup centered)
# so the rasterization stays pure-SVG (no magick compositing — keeps
# the pkgx env single-rasterizer + uploads pixel-perfect).
echo "raster: png/weft-social-preview.png (1280×640)"
RENDER weft-social-preview.svg 1280 640 png/weft-social-preview.png

echo "done — PNG générés dans static/logo/png/"
