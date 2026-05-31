# openweft/openweft.github.io

Sources for **openweft.github.io** — the Weft project's landing page.
Built by [Hugo](https://gohugo.io) (Go-native, single-binary, matches
the project ethos).

## Layout

```text
.
├── hugo.toml                       Site config + per-page params
├── content/
│   └── _index.md                   Homepage marker (empty front matter)
├── data/
│   └── mesh.toml                   Mesh visualisation : nodes / edges / paths
├── layouts/
│   ├── _default/baseof.html        Outer HTML shell
│   ├── index.html                  Homepage body
│   └── partials/
│       ├── nav.html                Topnav with brand + menu
│       ├── footer.html             Footer
│       └── mesh.html               Animated SVG (reads data/mesh.toml)
├── static/
│   └── css/main.css                Blue-dominant palette + mesh styling
└── public/                         Hugo build output (gitignored — built by CI)
```

## Build locally

```sh
# Easiest — on-demand via pkgx (no global install) :
pkgx hugo server -D                          # live reload at http://localhost:1313/
pkgx hugo --gc --minify                      # production build → ./public/

# Or install Hugo system-wide :
brew install hugo                            # macOS
sudo apt install hugo                        # Debian / Ubuntu
sudo dnf install hugo                        # Fedora
```

Tested with Hugo 0.161 (the version pkgx ships at the time of
writing). The GitHub Actions workflow pins a specific minor
version — see `.github/workflows/hugo.yml`.

## Edit the mesh

The animated SVG reads its nodes / edges / paths from
[`data/mesh.toml`](data/mesh.toml). To rebalance the visualisation :

- `nodes` — circles at `(x, y)`. `kind = "cp" | "agent"` picks the
  CSS palette ; `halo_r` + `core_r` size the halo + the centre.
  Optional `label` renders text above the node.
- `edges` — straight lines. `highlight = true` draws the line brighter
  and thicker — used for the inter-CP triangle to convey the etcd quorum.
- `paths` — moving spheres. `d` is the SVG path data (`"M x y L x y …"`) ;
  `dur` + optional `begin` control timing ; `fill` should be a CSS
  variable name (`"var(--accent-2)"` etc.) so theme changes propagate.

## Edit the content

- Hero meta (title, tagline, status badge, menu) lives in
  [`hugo.toml`](hugo.toml) under `[params]`.
- Section bodies (What you can do today, Design, Components, Status)
  are inlined in [`layouts/index.html`](layouts/index.html). When we
  add more pages it'll be worth splitting these into `content/*.md`
  and rendering via Hugo's content pipeline.

## Deploy

Pushed to GitHub Pages by `.github/workflows/hugo.yml` on every push
to `main`. The workflow runs `hugo --gc --minify` and deploys
`public/` via the official `actions/deploy-pages`.

To use this as the org's default landing page (so
`https://openweft.github.io/` serves it directly), rename the
repository to `openweft.github.io` ; that convention takes precedence
over per-repo paths.

## Why Hugo

- **Pure Go binary** — one executable, no node_modules, no Python.
- **HashiCorp-style ergonomics** — one tool, one config file.
- **TOML config + Go templates** — same engine the rest of the
  codebase already uses (`html/template`).
- **Mature** — scales from one page today to a full docs site later
  without changing tools.
