# weft logo assets

SVG is the canonical source ; the PNG rasters under `png/` are
regenerated from the SVGs by `build-logos.sh`. Use the PNG only
when the consuming surface refuses SVG (GitHub uploads — org
avatar, social preview, repo icon — and a handful of legacy
scrapers).

## What to upload where

Every PNG comes in two flavours — transparent (default) + white
background (`-white` suffix). GitHub's upload surfaces look better
with the white variants : avatar + Social Preview render against a
neutral chrome that's grey-ish on dark mode and white on light mode ;
transparent edges fringe at the chip boundary on dark mode. The
transparent variants are for surfaces that paint their own background
(README badges, embeds, custom OG cards).

| Surface (GitHub)                                       | File                                                       | Why                                                                                          |
| ------------------------------------------------------ | ---------------------------------------------------------- | -------------------------------------------------------------------------------------------- |
| **Org avatar** (`openweft` / org Settings)              | `png/weft-lockup-vertical-512-white.png`                   | Vertical lockup, white bg — readable when shrunk to GitHub's 60 px chip ; displayed up to 460 px. |
| **Repo Social Preview** (each repo, Settings → Social)  | `png/weft-social-preview.png` (1280×640, white baked in)   | Matches GitHub's spec exactly ; X / Slack / Mastodon scrapers surface this thumbnail.        |
| **README header banner**                                | `png/weft-wordmark-h-2048.png` (transparent)               | High-res so retina laptops don't see fuzzy edges ; constrain via `<img width="…">` in MD. Use the `-white` variant if your README itself uses a dark backdrop. |
| **README thumbnail / favicon-equivalent**               | `png/weft-A-weave-256.png` (transparent)                   | Square mark only ; `mono` for ink-heavy contexts, `weave` for the full two-colour brand.    |

## Regenerating

```sh
cd static/logo
pkgx +gnome.org/librsvg bash ./build-logos.sh
```

librsvg is the right choice : it renders the embedded fonts
(Inter falls back to system sans-serif on the rasterizer, the SVGs
are designed with that fallback in mind), respects `<title>` /
`<desc>` for accessibility, and produces sharp output without
needing a `-density` flag.

Magick / ImageMagick works too as a fallback ; the script picks
whichever is on PATH (rsvg-convert preferred).

## Why both `weft-A-mono.svg` and `weft-A-weave.svg`

- **weave** : two-colour version. Indigo strands (`#172445`) +
  cyan-blue crossbar (`#2563eb`). Use on light backgrounds where
  the brand should pop.
- **mono** : single-ink. Use on coloured backgrounds, in print, or
  anywhere the two-colour version would clash (e.g. a dark social
  card or a tinted CI badge).

Both share the same 256×256 viewBox so they're swap-compatible at
the consumer site.

## Why `weft-social-preview.svg` is a separate source file

GitHub's Social Preview spec is 1280×640, a 1.91:1 letterbox. The
lockup-vertical's natural aspect is 4:3. Rather than rely on
runtime compositing (magick `xc:white -composite`), the social
preview has its own SVG source that bakes the white canvas + the
centered lockup at the right scale. One pure-SVG rasterization
later, you get a pixel-perfect 1280×640 PNG with no Inkscape /
Magick dependency tangle. Reproduce by editing the SVG, then
re-running `build-logos.sh`.
