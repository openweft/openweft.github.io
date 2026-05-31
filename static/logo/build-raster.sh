#!/usr/bin/env -S pkgx bash
#
# Convertit les favicons SVG en PNG/ICO pour les user-agents qui ne
# supportent pas l'image/svg+xml (iOS <16, vieux IE/Edge). Tout-SVG
# couvre déjà 95%+ des cas — ce script n'est utile que si tu veux
# verrouiller la compat ancienne ou exposer les PNG aux scrapers
# (Slack/Mastodon/OG cards).
#
# Choisit le premier outil dispo, dans l'ordre :
#   rsvg-convert (librsvg)    — le plus rapide, output net
#   inkscape --export-type=png
#   magick (ImageMagick 7)    — verbeux mais quasi-universel
#   convert (ImageMagick 6)
#
# Sorties à côté des SVG : favicon.ico (16,32,48), favicon-192.png,
# favicon-512.png, apple-touch-icon.png (180×180).

set -euo pipefail
cd "$(dirname "$0")/.."   # cd dans static/

pick() {
  for t in "$@"; do command -v "$t" >/dev/null 2>&1 && { echo "$t"; return; }; done
  return 1
}

if RSVG=$(pick rsvg-convert); then
  RENDER() { "$RSVG" -w "$2" -h "$2" -o "$3" "$1"; }
elif INK=$(pick inkscape); then
  RENDER() { "$INK" --export-type=png --export-filename="$3" -w "$2" -h "$2" "$1" >/dev/null; }
elif MAG=$(pick magick convert); then
  RENDER() { "$MAG" -background none -density 384 -resize "${2}x${2}" "$1" "$3"; }
else
  echo "build-raster.sh: aucun rasterizer trouvé (rsvg-convert / inkscape / magick)." >&2
  echo "  pkgx install librsvg.org   # le plus léger" >&2
  echo "  brew install librsvg       # fallback brew" >&2
  exit 1
fi

echo "raster: favicon-192.png"; RENDER favicon.svg 192 favicon-192.png
echo "raster: favicon-512.png"; RENDER favicon.svg 512 favicon-512.png
echo "raster: apple-touch-icon.png"; RENDER apple-touch-icon.svg 180 apple-touch-icon.png

# ICO multi-tailles : besoin de magick pour packer les 3 tailles en
# un fichier .ico. Si seul rsvg/inkscape est dispo, on saute ICO et on
# laisse le SVG faire le boulot pour les navigateurs récents.
if MAG=$(pick magick convert); then
  echo "raster: favicon.ico (16+32+48)"
  for s in 16 32 48; do RENDER favicon.svg "$s" /tmp/weft-fav-"$s".png; done
  "$MAG" /tmp/weft-fav-16.png /tmp/weft-fav-32.png /tmp/weft-fav-48.png favicon.ico
  rm -f /tmp/weft-fav-{16,32,48}.png
else
  echo "raster: favicon.ico skipped (besoin de ImageMagick pour empaqueter multi-tailles)"
fi

echo "done — fichiers générés dans static/"
