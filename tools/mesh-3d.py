#!/usr/bin/env python3
"""mesh-3d.svg generator.

Produces an isometric (axonometric, α = 30°) SVG of the Weft mesh :
three datacenters spread across a ground plane (ellipses), each
holding three racks ; each rack holds four servers ; each server
hosts three microVMs. Dashed cyan arcs trace the WireGuard mesh
between datacenters, plus thinner threads between individual
microVMs to suggest the all-to-all overlay.

Regenerate after tweaking scene parameters :

    python3 tools/mesh-3d.py > static/img/mesh-3d.svg
"""
from __future__ import annotations
import math
import random

# ----- projection ---------------------------------------------------------

ALPHA = math.radians(30)
COS_A = math.cos(ALPHA)   # ≈ 0.8660
SIN_A = math.sin(ALPHA)   # 0.5
S     = 23                # screen pixels per world unit
CX, CY = 600, 380         # screen-space offset for world origin

def proj(x: float, y: float, z: float) -> tuple[float, float]:
    """Isometric projection (x right-back, y left-back, z up)."""
    return (CX + (x - y) * S * COS_A,
            CY + (x + y) * S * SIN_A - z * S)

def f(p: tuple[float, float]) -> str:
    return f"{p[0]:.1f},{p[1]:.1f}"

# ----- scene data ---------------------------------------------------------

DCS = [
    {"id": "dc-a", "label": "DC-A", "x": -10, "y": -2},
    {"id": "dc-b", "label": "DC-B", "x":   2, "y": -10},
    {"id": "dc-c", "label": "DC-C", "x":   8, "y":   8},
]

# Six racks per DC, laid out as two rows of three aligned on the
# datacenter floor — back row at y_back, front row at y_front, both
# sharing the three column x positions. Painter's algorithm sorts by
# (x+y) so the back row draws first.
_COL_X = (-3.25, -0.75, 1.75)        # rack origins along x (back-left corner)
_Y_BACK  = -2.4                      # back-row y_origin
_Y_FRONT = 0.5                       # front-row y_origin (1.0-unit aisle between)
RACK_OFFSETS = [(cx, _Y_BACK)  for cx in _COL_X] + \
               [(cx, _Y_FRONT) for cx in _COL_X]
RW, RD, RH = 1.5, 1.9, 3.9           # rack dimensions in world units
RACK_PLINTH = 0.38                   # short pedestal under each rack
SERVERS_PER_RACK = 4
MVMS_PER_SERVER  = 3
GROUND_R = 5.6                       # DC ground-ellipse radius (world)

# Multi-tenant palette. Each tenant microVM gets one of these as its
# colour ; the eye reads the mix as "different customers / projects
# sharing the platform". Infra microVMs (etcd, nats, dex, zot, weft,
# weft-network, envoy, otel-collector, victoriametrics, perses) keep
# their distinct indigo tone so they're never confused with a tenant
# workload.
TENANTS = [
    ("tenant-a", "#38bdf8"),  # sky-blue
    ("tenant-b", "#fbbf24"),  # amber
    ("tenant-c", "#f472b6"),  # rose
    ("tenant-d", "#34d399"),  # emerald
    ("tenant-e", "#c084fc"),  # violet
]
BLINK_PHASES = 8                     # number of distinct pulse offsets

# CI runners run AS microVMs on the platform and drive the weft API
# (per project) to spawn ephemeral CI-job microVMs. Each forge gets a
# brand-tinted runner microVM ; the spawned jobs share one lime tone.
RUNNER_FORGES = ["runner-gitlab", "runner-github", "runner-forgejo"]

# Official forge marks (Simple Icons, CC0 — used to flag integration).
LOGO_GITHUB  = "M12 .297c-6.63 0-12 5.373-12 12 0 5.303 3.438 9.8 8.205 11.385.6.113.82-.258.82-.577 0-.285-.01-1.04-.015-2.04-3.338.724-4.042-1.61-4.042-1.61C4.422 18.07 3.633 17.7 3.633 17.7c-1.087-.744.084-.729.084-.729 1.205.084 1.838 1.236 1.838 1.236 1.07 1.835 2.809 1.305 3.495.998.108-.776.417-1.305.76-1.605-2.665-.3-5.466-1.332-5.466-5.93 0-1.31.465-2.38 1.235-3.22-.135-.303-.54-1.523.105-3.176 0 0 1.005-.322 3.3 1.23.96-.267 1.98-.399 3-.405 1.02.006 2.04.138 3 .405 2.28-1.552 3.285-1.23 3.285-1.23.645 1.653.24 2.873.12 3.176.765.84 1.23 1.91 1.23 3.22 0 4.61-2.805 5.625-5.475 5.92.42.36.81 1.096.81 2.22 0 1.606-.015 2.896-.015 3.286 0 .315.21.69.825.57C20.565 22.092 24 17.592 24 12.297c0-6.627-5.373-12-12-12"
LOGO_GITLAB  = "m23.6004 9.5927-.0337-.0862L20.3.9814a.851.851 0 0 0-.3362-.405.8748.8748 0 0 0-.9997.0539.8748.8748 0 0 0-.29.4399l-2.2055 6.748H7.5375l-2.2057-6.748a.8573.8573 0 0 0-.29-.4412.8748.8748 0 0 0-.9997-.0537.8585.8585 0 0 0-.3362.4049L.4332 9.5015l-.0325.0862a6.0657 6.0657 0 0 0 2.0119 7.0105l.0113.0087.03.0213 4.976 3.7264 2.462 1.8633 1.4995 1.1321a1.0085 1.0085 0 0 0 1.2197 0l1.4995-1.1321 2.4619-1.8633 5.006-3.7489.0125-.01a6.0682 6.0682 0 0 0 2.0094-7.003z"
LOGO_FORGEJO = "M16.7773 0c1.6018 0 2.9004 1.2986 2.9004 2.9005s-1.2986 2.9004-2.9004 2.9004c-1.0854 0-2.0315-.596-2.5288-1.4787H12.91c-2.3322 0-4.2272 1.8718-4.2649 4.195l-.0007 2.1175a7.0759 7.0759 0 0 1 4.148-1.4205l.1176-.001 1.3385.0002c.4973-.8827 1.4434-1.4788 2.5288-1.4788 1.6018 0 2.9004 1.2986 2.9004 2.9005s-1.2986 2.9004-2.9004 2.9004c-1.0854 0-2.0315-.596-2.5288-1.4787H12.91c-2.3322 0-4.2272 1.8718-4.2649 4.195l-.0007 2.319c.8827.4973 1.4788 1.4434 1.4788 2.5287 0 1.602-1.2986 2.9005-2.9005 2.9005-1.6018 0-2.9004-1.2986-2.9004-2.9005 0-1.0853.596-2.0314 1.4788-2.5287l-.0002-9.9831c0-3.887 3.1195-7.0453 6.9915-7.108l.1176-.001h1.3385C14.7458.5962 15.692 0 16.7773 0ZM7.2227 19.9052c-.6596 0-1.1943.5347-1.1943 1.1943s.5347 1.1943 1.1943 1.1943 1.1944-.5347 1.1944-1.1943-.5348-1.1943-1.1944-1.1943Zm9.5546-10.4644c-.6596 0-1.1944.5347-1.1944 1.1943s.5348 1.1943 1.1944 1.1943c.6596 0 1.1943-.5347 1.1943-1.1943s-.5347-1.1943-1.1943-1.1943Zm0-7.7346c-.6596 0-1.1944.5347-1.1944 1.1943s.5348 1.1943 1.1944 1.1943c.6596 0 1.1943-.5347 1.1943-1.1943s-.5347-1.1943-1.1943-1.1943Z"
LOGO_JUPYTER = "M7.157 22.201A1.784 1.799 0 0 1 5.374 24a1.784 1.799 0 0 1-1.784-1.799 1.784 1.799 0 0 1 1.784-1.799 1.784 1.799 0 0 1 1.783 1.799zM20.582 1.427a1.415 1.427 0 0 1-1.415 1.428 1.415 1.427 0 0 1-1.416-1.428A1.415 1.427 0 0 1 19.167 0a1.415 1.427 0 0 1 1.415 1.427zM4.992 3.336A1.047 1.056 0 0 1 3.946 4.39a1.047 1.056 0 0 1-1.047-1.055A1.047 1.056 0 0 1 3.946 2.28a1.047 1.056 0 0 1 1.046 1.056zm7.336 1.517c3.769 0 7.06 1.38 8.768 3.424a9.363 9.363 0 0 0-3.393-4.547 9.238 9.238 0 0 0-5.377-1.728A9.238 9.238 0 0 0 6.95 3.73a9.363 9.363 0 0 0-3.394 4.547c1.713-2.04 5.004-3.424 8.772-3.424zm.001 13.295c-3.768 0-7.06-1.381-8.768-3.425a9.363 9.363 0 0 0 3.394 4.547A9.238 9.238 0 0 0 12.33 21a9.238 9.238 0 0 0 5.377-1.729 9.363 9.363 0 0 0 3.393-4.547c-1.712 2.044-5.003 3.425-8.772 3.425Z"

def mvm_kind(di, ri, si, mi):
    """Deterministic classification of a microVM from its indices
    (dc, rack, server, slot). Returns its CSS colour class.
      - top server of every rack  → infra (etcd, nats, dex, zot, weft, weft-network, envoy, otel-collector, victoriametrics, perses)
      - one slot per DC           → CI runner microVM (forge-tinted)
      - a couple of slots per DC  → ephemeral CI-job microVM
      - everything else           → a tenant colour"""
    if si == SERVERS_PER_RACK - 1:
        return "mvm-infra"
    if ri == 0 and si == SERVERS_PER_RACK - 2:
        # Every DC hosts one runner per forge (slots 0/1/2) so each forge
        # has runners in all three DCs — HA if a DC drops out.
        return RUNNER_FORGES[mi % len(RUNNER_FORGES)]
    if ri == 1 and si == SERVERS_PER_RACK - 2:
        # CubeFS — distributed storage cluster (S3 + POSIX volumes), CNCF
        # graduated. A few nodes per DC (master / meta / data).
        return "svc-cubefs"
    if ri == 5 and si == 1:
        return "mvm-notebook"  # per-user JupyterHub notebook microVMs
    if ri in (2, 4) and si == 0 and mi == MVMS_PER_SERVER - 1:
        return "mvm-ci"
    palette = [t[0] for t in TENANTS]
    return palette[(di * 17 + ri * 7 + si * 3 + mi) % len(palette)]

def mvm_phase(di, ri, si, mi):
    return (di * 13 + ri * 5 + si * 3 + mi) % BLINK_PHASES

# ----- output buffer -------------------------------------------------------

out: list[str] = []

def emit(*lines: str) -> None:
    out.extend(lines)

# ----- header --------------------------------------------------------------

emit(
'<svg viewBox="0 0 1200 800" xmlns="http://www.w3.org/2000/svg" '
'role="img" aria-label="Weft 3D mesh">',
'<defs>',
'  <linearGradient id="g-bg" x1="0" y1="0" x2="0" y2="1">',
'    <stop offset="0" stop-color="#ccd6ec"/>',
'    <stop offset="1" stop-color="#aebdd6"/>',
'  </linearGradient>',
'  <radialGradient id="g-dc" cx="50%" cy="50%" r="50%">',
'    <stop offset="0"   stop-color="rgba(37,99,235,0.18)"/>',
'    <stop offset="0.7" stop-color="rgba(37,99,235,0.06)"/>',
'    <stop offset="1"   stop-color="rgba(37,99,235,0.00)"/>',
'  </radialGradient>',
'  <linearGradient id="g-rack-top" x1="0" y1="0" x2="0.6" y2="1">',
'    <stop offset="0"   stop-color="#8497c9"/>',
'    <stop offset="0.5" stop-color="#5b6da3"/>',
'    <stop offset="1"   stop-color="#41527f"/>',
'  </linearGradient>',
'  <linearGradient id="g-rack-front" x1="0" y1="0" x2="0" y2="1">',
'    <stop offset="0" stop-color="#43548a"/>',
'    <stop offset="1" stop-color="#27365f"/>',
'  </linearGradient>',
'  <linearGradient id="g-rack-side" x1="0" y1="0" x2="0" y2="1">',
'    <stop offset="0" stop-color="#283861"/>',
'    <stop offset="1" stop-color="#172445"/>',
'  </linearGradient>',
'  <linearGradient id="g-plinth-front" x1="0" y1="0" x2="0" y2="1">',
'    <stop offset="0" stop-color="#2a3a64"/>',
'    <stop offset="1" stop-color="#1a2748"/>',
'  </linearGradient>',
'  <linearGradient id="g-plinth-side" x1="0" y1="0" x2="0" y2="1">',
'    <stop offset="0" stop-color="#1c2a4e"/>',
'    <stop offset="1" stop-color="#101c38"/>',
'  </linearGradient>',
'  <linearGradient id="g-server-panel" x1="0" y1="0" x2="0" y2="1">',
'    <stop offset="0" stop-color="#202f54"/>',
'    <stop offset="1" stop-color="#142142"/>',
'  </linearGradient>',
'  <linearGradient id="g-display" x1="0" y1="0" x2="0" y2="1">',
'    <stop offset="0" stop-color="#67e8f9"/>',
'    <stop offset="1" stop-color="#0891b2"/>',
'  </linearGradient>',
f'  <symbol id="logo-github" viewBox="0 0 24 24"><path d="{LOGO_GITHUB}"/></symbol>',
f'  <symbol id="logo-gitlab" viewBox="0 0 24 24"><path d="{LOGO_GITLAB}"/></symbol>',
f'  <symbol id="logo-forgejo" viewBox="0 0 24 24"><path d="{LOGO_FORGEJO}"/></symbol>',
f'  <symbol id="logo-jupyter" viewBox="0 0 24 24"><path d="{LOGO_JUPYTER}"/></symbol>',
'  <filter id="glow" x="-50%" y="-50%" width="200%" height="200%">',
'    <feGaussianBlur stdDeviation="2.4"/>',
'  </filter>',
'</defs>',
'<style>',
'  .bg          { fill: url(#g-bg); }',
'  .grid        { stroke: rgba(37,99,235,0.10); stroke-width: 1; fill: none; }',
'  .dc-ground   { fill: url(#g-dc); stroke: rgba(37,99,235,0.50); stroke-width: 1.4; stroke-dasharray: 4 6; }',
'  .dc-shadow   { fill: rgba(37,99,235,0.10); }',
'  .rack-top    { fill: url(#g-rack-top);   stroke: #9aacd8; stroke-width: 0.7; }',
'  .rack-front  { fill: url(#g-rack-front); stroke: #56689c; stroke-width: 0.7; }',
'  .rack-side   { fill: url(#g-rack-side);  stroke: #2f3f68; stroke-width: 0.7; }',
'  .plinth-front{ fill: url(#g-plinth-front); stroke: #3a4a78; stroke-width: 0.6; }',
'  .plinth-side { fill: url(#g-plinth-side);  stroke: #25345c; stroke-width: 0.6; }',
'  .plinth-top  { fill: #354574; stroke: #4a5c92; stroke-width: 0.5; }',
'  .rack-edge   { stroke: rgba(200,222,255,0.90); stroke-width: 1.5; fill: none; stroke-linecap: round; }',
'  .rack-rail   { stroke: rgba(160,190,240,0.30); stroke-width: 0.6; fill: none; }',
'  .server-panel    { fill: url(#g-server-panel); stroke: rgba(160,190,240,0.45); stroke-width: 0.5; }',
'  .server-edge-top { stroke: rgba(190,212,250,0.55); stroke-width: 0.6; fill: none; }',
'  .server-bracket  { fill: rgba(160,190,240,0.60); }',
'  .tenant-a    { fill: #0ea5d8; }',   # sky-blue (deepened for light bg)
'  .tenant-b    { fill: #f59e0b; }',   # amber
'  .tenant-c    { fill: #ec4899; }',   # rose
'  .tenant-d    { fill: #10b981; }',   # emerald
'  .tenant-e    { fill: #a855f7; }',   # violet
'  .mvm-infra   { fill: #6366f1; }',
'  /* CI runner microVMs — brand-tinted, outlined so they read as special. */',
'  .runner-gitlab  { fill: #fc6d26; stroke: #fff7ed; stroke-width: 0.5; }',
'  .runner-github  { fill: #c9d1d9; stroke: #ffffff; stroke-width: 0.5; }',
'  .runner-forgejo { fill: #fb923c; stroke: #fff7ed; stroke-width: 0.5; }',
'  /* Ephemeral CI-job microVMs — lime, fast pulse (churn). */',
'  .mvm-ci      { fill: #a3e635; }',
'  /* Per-user JupyterHub notebook microVMs — Jupyter orange. */',
'  .mvm-notebook { fill: #f37726; }',
'  /* CubeFS distributed-storage microVMs — S3 + POSIX volumes (CNCF). */',
'  .svc-cubefs  { fill: #2dd4bf; }',
'  .dc-label    { fill: #1e3a8a; font-family: ui-sans-serif, system-ui, sans-serif; font-size: 15px; font-weight: 700; letter-spacing: 0.22em; text-anchor: middle; }',
'  .wg-link     { fill: none; stroke: rgba(37,99,235,0.38); stroke-width: 0.7; stroke-dasharray: 2 4; stroke-linecap: round; }',
'  .wg-link-hi  { fill: none; stroke: rgba(8,145,178,0.85); stroke-width: 1.3; stroke-dasharray: 3 4; stroke-linecap: round; filter: url(#glow); }',
'  /* Client → weft API (dev laptops + CI runners driving the control plane). */',
'  .client-link { fill: none; stroke: #475569; stroke-width: 1.5; stroke-linecap: round; }',
'  /* weft → spawned CI-job microVM. */',
'  .spawn-link  { fill: none; stroke: rgba(101,163,13,0.75); stroke-width: 1.1; stroke-dasharray: 2 3; stroke-linecap: round; }',
'  .laptop-deck   { fill: #5a6b94; stroke: #7587b3; stroke-width: 0.5; }',
'  .laptop-front  { fill: #3a4a72; stroke: #2a3858; stroke-width: 0.5; }',
'  .laptop-side   { fill: #2b3859; stroke: #1c2742; stroke-width: 0.5; }',
'  .laptop-screen { fill: #16203c; stroke: #44558a; stroke-width: 0.6; }',
'  .laptop-display{ fill: url(#g-display); }',
'  /* External forge services (GitHub / GitLab / Forgejo) + their runners. */',
'  .forge-tile  { fill: #ffffff; stroke: rgba(37,99,235,0.30); stroke-width: 1; }',
'  .logo-github  { fill: #181717; }',
'  .logo-gitlab  { fill: #fc6d26; }',
'  .logo-forgejo { fill: #fb923c; }',
'  .logo-jupyter { fill: #f37726; }',
'  .forge-label { fill: #1e3a8a; font-family: ui-sans-serif, system-ui, sans-serif; font-size: 11px; font-weight: 600; text-anchor: middle; }',
'  .forge-link  { fill: none; stroke-width: 1.2; stroke-dasharray: 5 4; stroke-linecap: round; }',
'  .forge-link.gitlab  { stroke: rgba(252,109,38,0.75); }',
'  .forge-link.github  { stroke: rgba(60,70,85,0.65); }',
'  .forge-link.forgejo { stroke: rgba(251,146,60,0.80); }',
'  .forge-link.jupyter { stroke: rgba(243,119,38,0.75); }',
'  .legend-bg   { fill: rgba(255,255,255,0.92); stroke: rgba(37,99,235,0.25); }',
'  .legend-text { fill: #1e3a8a; font-family: ui-sans-serif, system-ui, sans-serif; font-size: 11px; font-weight: 500; }',
'  @keyframes pulse  { 0%,100% { opacity: 1 } 50% { opacity: 0.25 } }',
'  @keyframes flow   { to { stroke-dashoffset: -110 } }',
'  /* Every microVM picks one of these phases so they blink out of sync. */',
'  .tenant-a, .tenant-b, .tenant-c, .tenant-d, .tenant-e, .mvm-infra,',
'  .runner-gitlab, .runner-github, .runner-forgejo, .svc-cubefs, .mvm-notebook {',
'    animation-name: pulse; animation-timing-function: ease-in-out; animation-iteration-count: infinite;',
'  }',
'  /* CI jobs churn faster than steady workloads. */',
'  .mvm-ci { animation: pulse 1.1s ease-in-out infinite; }',
'  .phase-0 { animation-duration: 2.4s; animation-delay: -0.0s; }',
'  .phase-1 { animation-duration: 2.7s; animation-delay: -0.4s; }',
'  .phase-2 { animation-duration: 3.1s; animation-delay: -0.9s; }',
'  .phase-3 { animation-duration: 2.5s; animation-delay: -1.3s; }',
'  .phase-4 { animation-duration: 2.9s; animation-delay: -1.7s; }',
'  .phase-5 { animation-duration: 3.3s; animation-delay: -2.1s; }',
'  .phase-6 { animation-duration: 2.6s; animation-delay: -2.4s; }',
'  .phase-7 { animation-duration: 3.0s; animation-delay: -2.8s; }',
'  .wg-link, .wg-link-hi, .spawn-link { animation: flow 8s linear infinite; }',
'  @media (prefers-reduced-motion: reduce) {',
'    .tenant-a, .tenant-b, .tenant-c, .tenant-d, .tenant-e, .mvm-infra,',
'    .runner-gitlab, .runner-github, .runner-forgejo, .mvm-ci, .svc-cubefs, .mvm-notebook,',
'    .wg-link, .wg-link-hi, .spawn-link { animation: none }',
'  }',
'</style>',
'<rect class="bg" x="0" y="0" width="1200" height="800"/>',
)

# ----- ground grid (faint) -------------------------------------------------

GRID_RANGE = 18
emit('<g class="grid">')
for i in range(-GRID_RANGE, GRID_RANGE + 1, 2):
    a = proj(i, -GRID_RANGE, 0); b = proj(i, GRID_RANGE, 0)
    emit(f'  <line x1="{a[0]:.1f}" y1="{a[1]:.1f}" x2="{b[0]:.1f}" y2="{b[1]:.1f}"/>')
    a = proj(-GRID_RANGE, i, 0); b = proj(GRID_RANGE, i, 0)
    emit(f'  <line x1="{a[0]:.1f}" y1="{a[1]:.1f}" x2="{b[0]:.1f}" y2="{b[1]:.1f}"/>')
emit('</g>')

# ----- DC ground shadows + ellipses ---------------------------------------

_GROUND_RX = GROUND_R * S * COS_A * math.sqrt(2)
_GROUND_RY = GROUND_R * S * SIN_A * math.sqrt(2)
for dc in DCS:
    cx, cy = proj(dc["x"], dc["y"], 0)
    # A horizontal circle of radius R projects to an axis-aligned ellipse
    # with semi-axes R·S·cos(30°)·√2 and R·S·sin(30°)·√2 (the √2 factor
    # is easy to miss — without it, the ellipse only passes through the
    # 4 cardinal points and clips the rest of the disc).
    emit(f'<ellipse class="dc-shadow"  cx="{cx:.1f}" cy="{cy+3:.1f}" rx="{_GROUND_RX:.1f}" ry="{_GROUND_RY:.1f}"/>')
    emit(f'<ellipse class="dc-ground"  cx="{cx:.1f}" cy="{cy:.1f}"   rx="{_GROUND_RX:.1f}" ry="{_GROUND_RY:.1f}"/>')

# ----- rack drawing -------------------------------------------------------

def draw_rack(ox: float, oy: float, dc_idx: int, rack_idx: int) -> list[str]:
    """Visible faces of a rack at world origin (ox, oy, 0), with a plinth,
    server slabs that protrude from the +y (visible front) face, and
    microVM slots on the server fronts. dc_idx / rack_idx drive the
    deterministic per-microVM colour (see mvm_kind / mvm_phase).

    Projection convention : viewer at (+x, +y, +z) → visible faces are
    +x (right side on screen), +y (front in screen — *lower-left* of
    the rack), and +z (top). The rack-front polygon therefore uses
    corners at y = oy + RD, NOT y = oy."""
    parts: list[str] = []
    P = RACK_PLINTH

    # Plinth (slightly wider pedestal beneath the rack)
    pe = 0.16
    pp000 = proj(ox - pe,        oy - pe,        0)
    pp100 = proj(ox + RW + pe,   oy - pe,        0)
    pp010 = proj(ox - pe,        oy + RD + pe,   0)
    pp110 = proj(ox + RW + pe,   oy + RD + pe,   0)
    pp00P = proj(ox - pe,        oy - pe,        P)
    pp10P = proj(ox + RW + pe,   oy - pe,        P)
    pp01P = proj(ox - pe,        oy + RD + pe,   P)
    pp11P = proj(ox + RW + pe,   oy + RD + pe,   P)
    # Plinth visible faces : +x (right), +y (front), +z (top)
    parts.append(f'<polygon class="plinth-side"  points="{f(pp100)} {f(pp110)} {f(pp11P)} {f(pp10P)}"/>')
    parts.append(f'<polygon class="plinth-front" points="{f(pp010)} {f(pp110)} {f(pp11P)} {f(pp01P)}"/>')
    parts.append(f'<polygon class="plinth-top"   points="{f(pp00P)} {f(pp10P)} {f(pp11P)} {f(pp01P)}"/>')

    # Rack body (sits on top of the plinth, so z starts at P)
    p000 = proj(ox,    oy,    P);  p100 = proj(ox+RW, oy,    P)
    p010 = proj(ox,    oy+RD, P);  p110 = proj(ox+RW, oy+RD, P)
    p001 = proj(ox,    oy,    RH); p101 = proj(ox+RW, oy,    RH)
    p011 = proj(ox,    oy+RD, RH); p111 = proj(ox+RW, oy+RD, RH)

    # Rack body visible faces : +x (right), +z (top), +y (front).
    # Front drawn last so server slabs + rails stack on it.
    parts.append(f'<polygon class="rack-side"  points="{f(p100)} {f(p110)} {f(p111)} {f(p101)}"/>')
    parts.append(f'<polygon class="rack-top"   points="{f(p001)} {f(p101)} {f(p111)} {f(p011)}"/>')
    parts.append(f'<polygon class="rack-front" points="{f(p010)} {f(p110)} {f(p111)} {f(p011)}"/>')

    # Rack-mount rails : vertical guide lines on the +y front face
    rail_inset_x = 0.10
    for rx in (ox + rail_inset_x, ox + RW - rail_inset_x):
        a = proj(rx, oy + RD, P + 0.10)
        b = proj(rx, oy + RD, RH - 0.10)
        parts.append(f'<line class="rack-rail" x1="{a[0]:.1f}" y1="{a[1]:.1f}" x2="{b[0]:.1f}" y2="{b[1]:.1f}"/>')

    # Servers : flat rack-mount panels flush against the +y face. Their
    # shape (1U / 2U rectangle) shows on the rack front, no 3D protrusion.
    # microVMs sit as bright LEDs on each panel.
    margin_z = 0.30
    usable_h = RH - P - 2 * margin_z
    slot_h   = usable_h / SERVERS_PER_RACK
    band_h   = slot_h * 0.74
    gap_h    = slot_h - band_h
    z_base   = P + margin_z
    yf       = oy + RD                # flush with the rack +y front face
    for si in range(SERVERS_PER_RACK):
        z_bot = z_base + si * slot_h + gap_h / 2
        z_top = z_bot + band_h
        x0 = ox + 0.10
        x1 = ox + RW - 0.10
        s00 = proj(x0, yf, z_bot); s10 = proj(x1, yf, z_bot)
        s11 = proj(x1, yf, z_top); s01 = proj(x0, yf, z_top)
        # Server front panel (dark recessed rectangle on the rack face)
        parts.append(f'<polygon class="server-panel" points="{f(s00)} {f(s10)} {f(s11)} {f(s01)}"/>')
        # Top edge highlight of each panel — gives the 1U "lit edge" feel
        parts.append(f'<line class="server-edge-top" x1="{s01[0]:.1f}" y1="{s01[1]:.1f}" '
                     f'x2="{s11[0]:.1f}" y2="{s11[1]:.1f}"/>')
        # Mount brackets : tiny squares at the left + right of each panel
        # (the "ears" that bolt onto the rack rails)
        bw = 0.04
        for bx in (x0 - bw, x1):
            b00 = proj(bx,       yf, z_bot + band_h * 0.20)
            b10 = proj(bx + bw,  yf, z_bot + band_h * 0.20)
            b11 = proj(bx + bw,  yf, z_bot + band_h * 0.80)
            b01 = proj(bx,       yf, z_bot + band_h * 0.80)
            parts.append(f'<polygon class="server-bracket" points="{f(b00)} {f(b10)} {f(b11)} {f(b01)}"/>')

        # microVMs : flat coloured LEDs on the server panel. Colour +
        # blink phase come from the deterministic mvm_kind / mvm_phase so
        # the diagram matches the links drawn later.
        for mi in range(MVMS_PER_SERVER):
            t  = (mi + 0.5) / MVMS_PER_SERVER
            mx = x0 + t * (x1 - x0)
            mw = (x1 - x0) * 0.16
            mh = band_h * 0.58
            mzb = z_bot + (band_h - mh) / 2
            mzt = mzb + mh
            m00 = proj(mx - mw/2, yf, mzb)
            m10 = proj(mx + mw/2, yf, mzb)
            m11 = proj(mx + mw/2, yf, mzt)
            m01 = proj(mx - mw/2, yf, mzt)
            colour_cls = mvm_kind(dc_idx, rack_idx, si, mi)
            phase_cls = f"phase-{mvm_phase(dc_idx, rack_idx, si, mi)}"
            parts.append(f'<polygon class="{colour_cls} {phase_cls}" '
                         f'points="{f(m00)} {f(m10)} {f(m11)} {f(m01)}"/>')

    # Visible top edges of the rack body : top-front (between +z and +y)
    # and top-side (between +z and +x). Drawn last so they sit on top.
    parts.append(f'<line class="rack-edge" x1="{p011[0]:.1f}" y1="{p011[1]:.1f}" '
                 f'x2="{p111[0]:.1f}" y2="{p111[1]:.1f}"/>')
    parts.append(f'<line class="rack-edge" x1="{p101[0]:.1f}" y1="{p101[1]:.1f}" '
                 f'x2="{p111[0]:.1f}" y2="{p111[1]:.1f}"/>')
    return parts

# Painter's algorithm : sort racks by depth (smaller x+y → further → draw first)
all_racks: list[tuple[float, float, float, int, int]] = []
for di, dc in enumerate(DCS):
    for ri, (lox, loy) in enumerate(RACK_OFFSETS):
        ox, oy = dc["x"] + lox, dc["y"] + loy
        all_racks.append((ox + oy, ox, oy, di, ri))
all_racks.sort(key=lambda t: t[0])
for _, ox, oy, di, ri in all_racks:
    emit(*draw_rack(ox, oy, di, ri))

# ----- WireGuard mesh -----------------------------------------------------

# Collect every microVM's world position (centred on its slot on the rack
# front face). Geometry mirrors draw_rack() so endpoints line up exactly
# with the rendered microVM cubes. Bucket by role (via mvm_kind) so the
# links drawn below connect the right things :
#   - infra   → control-plane mesh + weft API anchor
#   - tenant  → tenant overlay mesh
#   - runner  → CI runner microVMs (drive the weft API)
#   - ci      → ephemeral CI-job microVMs (spawned by weft)
infra_positions:  dict[str, list[tuple[float, float, float]]] = {dc["id"]: [] for dc in DCS}
tenant_positions: dict[str, list[tuple[float, float, float]]] = {dc["id"]: [] for dc in DCS}
ci_positions:     dict[str, list[tuple[float, float, float]]] = {dc["id"]: [] for dc in DCS}
notebook_positions: dict[str, list[tuple[float, float, float]]] = {dc["id"]: [] for dc in DCS}
runner_list: list[tuple[str, tuple[float, float, float], str]] = []   # (dc_id, pos, forge)
weft_anchor: dict[str, tuple[float, float, float]] = {}          # dc_id -> infra pos
_margin_z = 0.30
_usable_h = RH - RACK_PLINTH - 2 * _margin_z
_slot_h   = _usable_h / SERVERS_PER_RACK
_band_h   = _slot_h * 0.74
_gap_h    = _slot_h - _band_h
_z_base   = RACK_PLINTH + _margin_z
for di, dc in enumerate(DCS):
    for ri, (lox, loy) in enumerate(RACK_OFFSETS):
        ox = dc["x"] + lox
        oy = dc["y"] + loy
        for si in range(SERVERS_PER_RACK):
            z_mid = _z_base + si * _slot_h + _gap_h / 2 + _band_h / 2
            for mi in range(MVMS_PER_SERVER):
                t  = (mi + 0.5) / MVMS_PER_SERVER
                x0 = ox + 0.10
                x1 = ox + RW - 0.10
                mx = x0 + t * (x1 - x0)
                pos = (mx, oy + RD, z_mid)   # flush on the rack +y face
                kind = mvm_kind(di, ri, si, mi)
                if kind == "mvm-infra":
                    infra_positions[dc["id"]].append(pos)
                    # pick one infra microVM as the DC's weft API anchor
                    if ri == 0 and mi == MVMS_PER_SERVER // 2:
                        weft_anchor[dc["id"]] = pos
                elif kind in RUNNER_FORGES:
                    runner_list.append((dc["id"], pos, kind))
                elif kind == "mvm-ci":
                    ci_positions[dc["id"]].append(pos)
                elif kind == "mvm-notebook":
                    notebook_positions[dc["id"]].append(pos)
                elif kind == "svc-cubefs":
                    pass   # CubeFS storage : drawn, not a mesh endpoint here
                else:
                    tenant_positions[dc["id"]].append(pos)

def arc(p1, p2, lift, css_class):
    mx = (p1[0] + p2[0]) / 2
    my = (p1[1] + p2[1]) / 2
    return (f'<path class="{css_class}" '
            f'd="M {p1[0]:.1f} {p1[1]:.1f} '
            f'Q {mx:.1f} {my - lift:.1f} {p2[0]:.1f} {p2[1]:.1f}"/>')

def mesh_links(pool, count, css_class, seed):
    """Emit `count` inter-DC arcs between random microVMs drawn from `pool`
    (a dict of DC id → list of world positions). Deterministic per seed."""
    rng = random.Random(seed)
    dc_ids = [dc["id"] for dc in DCS]
    for _ in range(count):
        a, b = rng.sample(dc_ids, 2)
        s1 = proj(*rng.choice(pool[a]))
        s2 = proj(*rng.choice(pool[b]))
        dist = math.hypot(s2[0] - s1[0], s2[1] - s1[1])
        lift = max(35, dist * 0.32)
        emit(arc(s1, s2, lift, css_class))

# Faint pale links : the tenant overlay — any workload microVM can reach
# any other across DCs. Drawn first so they sit behind the infra backbone.
mesh_links(tenant_positions, 30, "wg-link", 20260526)
# Bright links : the control-plane / infra backbone — the etcd / nats /
# dex / weft microVMs that hold the platform together across DCs.
mesh_links(infra_positions, 12, "wg-link-hi", 20260530)

# ----- CI : runners drive the weft API, weft spawns CI-job microVMs --------

# Spawn links (faint lime) : weft → each ephemeral CI-job microVM it just
# booted, on the same substrate as everything else.
for dc in DCS:
    wp = weft_anchor[dc["id"]]
    for cp in ci_positions[dc["id"]]:
        emit(arc(proj(*wp), proj(*cp), 20, "spawn-link"))

# API-drive links (slate) : each CI runner microVM calls its DC's weft
# API (per project) to request those CI microVMs.
for dc_id, rp, _forge in runner_list:
    emit(arc(proj(*rp), proj(*weft_anchor[dc_id]), 26, "client-link"))

# ----- external dev laptops -------------------------------------------------

LAP_W, LAP_D, LAP_H = 1.7, 1.2, 0.12      # laptop base
LAP_SH, LAP_TILT    = 1.25, 0.55          # screen height + back-tilt

def lap_screen_pt(lx, ly, u, v):
    """Point on the laptop screen plane : u across width, v hinge→top."""
    return proj(lx + 0.05 + u * (LAP_W - 0.10), ly - v * LAP_TILT, LAP_H + v * LAP_SH)

def draw_laptop(lx, ly):
    W, D, H = LAP_W, LAP_D, LAP_H
    b010 = proj(lx, ly+D, 0); b110 = proj(lx+W, ly+D, 0)
    b011 = proj(lx, ly+D, H); b111 = proj(lx+W, ly+D, H)
    b100 = proj(lx+W, ly, 0); b101 = proj(lx+W, ly, H); b001 = proj(lx, ly, H)
    emit(f'<polygon class="laptop-side"  points="{f(b100)} {f(b110)} {f(b111)} {f(b101)}"/>')
    emit(f'<polygon class="laptop-front" points="{f(b010)} {f(b110)} {f(b111)} {f(b011)}"/>')
    emit(f'<polygon class="laptop-deck"  points="{f(b001)} {f(b101)} {f(b111)} {f(b011)}"/>')
    sb = [lap_screen_pt(lx,ly,0,0), lap_screen_pt(lx,ly,1,0), lap_screen_pt(lx,ly,1,1), lap_screen_pt(lx,ly,0,1)]
    emit(f'<polygon class="laptop-screen" points="{f(sb[0])} {f(sb[1])} {f(sb[2])} {f(sb[3])}"/>')
    dp = [lap_screen_pt(lx,ly,0.10,0.16), lap_screen_pt(lx,ly,0.90,0.16),
          lap_screen_pt(lx,ly,0.90,0.86), lap_screen_pt(lx,ly,0.10,0.86)]
    emit(f'<polygon class="laptop-display" points="{f(dp[0])} {f(dp[1])} {f(dp[2])} {f(dp[3])}"/>')

# Two dev laptops in the side margins. Each opens a gRPC session to the
# nearest DC's weft API (client-link), drawn before the laptop so the
# device sits on top of the wire.
LAPTOPS = [(-16.8, 4.5), (15.5, -0.5)]
for lx, ly in LAPTOPS:
    nearest = min(DCS, key=lambda d: (d["x"] - lx) ** 2 + (d["y"] - ly) ** 2)
    s1 = lap_screen_pt(lx, ly, 0.5, 1.0)
    s2 = proj(*weft_anchor[nearest["id"]])
    dist = math.hypot(s2[0] - s1[0], s2[1] - s1[1])
    emit(arc(s1, s2, max(55, dist * 0.26), "client-link"))
for lx, ly in LAPTOPS:
    draw_laptop(lx, ly)

# ----- external forge services (GitHub / GitLab / Forgejo) -----------------
# Flat 2D badges in the top margin — these live on the internet, outside
# the iso world. Each forge feeds the CI runner microVM that polls it ;
# that runner then drives the weft API. Brand marks : Simple Icons (CC0).
def draw_forge(cx, cy, logo, label):
    emit(f'<g transform="translate({cx},{cy})">',
         '  <rect class="forge-tile" x="-19" y="-19" width="38" height="38" rx="9"/>',
         f'  <use href="#{logo}" x="-12" y="-12" width="24" height="24" class="{logo}"/>',
         f'  <text class="forge-label" y="33">{label}</text>',
         '</g>')

# (screen x, screen y, logo id/class, label, runner forge kind, link class)
FORGES = [
    (255,  66, "logo-gitlab",  "GitLab",  "runner-gitlab",  "gitlab"),
    (610,  50, "logo-forgejo", "Forgejo", "runner-forgejo", "forgejo"),
    (1015, 96, "logo-github",  "GitHub",  "runner-github",  "github"),
]
runners_by_forge: dict[str, list[tuple[float, float, float]]] = {}
for _dc, pos, forge in runner_list:
    runners_by_forge.setdefault(forge, []).append(pos)
# Links forge → each of its runner microVMs across all DCs (HA fan-out),
# drawn before the badges so the tiles sit on top of the wires.
for cx, cy, logo, label, forge_kind, link_cls in FORGES:
    for rp in runners_by_forge[forge_kind]:
        s2 = proj(*rp)
        emit(f'<path class="forge-link {link_cls}" d="M {cx:.1f} {cy + 19:.1f} '
             f'Q {(cx + s2[0]) / 2:.1f} {(cy + s2[1]) / 2 - 25:.1f} {s2[0]:.1f} {s2[1]:.1f}"/>')
for cx, cy, logo, label, forge_kind, link_cls in FORGES:
    draw_forge(cx, cy, logo, label)

# ----- JupyterHub consumer -------------------------------------------------
# An external JupyterHub spawns per-user notebook microVMs through the weft
# API, kept HA across all three DCs (one link per DC, to a notebook there).
JUP_X, JUP_Y = 120, 432
for dc in DCS:
    nbs = notebook_positions[dc["id"]]
    if nbs:
        s2 = proj(*nbs[0])
        emit(f'<path class="forge-link jupyter" d="M {JUP_X:.1f} {JUP_Y + 19:.1f} '
             f'Q {(JUP_X + s2[0]) / 2:.1f} {(JUP_Y + s2[1]) / 2 - 25:.1f} {s2[0]:.1f} {s2[1]:.1f}"/>')
draw_forge(JUP_X, JUP_Y, "logo-jupyter", "JupyterHub")

# ----- labels --------------------------------------------------------------

for dc in DCS:
    cx, cy = proj(dc["x"], dc["y"], 0)
    emit(f'<text class="dc-label" x="{cx:.1f}" y="{cy + _GROUND_RY + 26:.1f}">{dc["label"]}</text>')

# ----- legend (bottom, 3 columns × up to 4 rows) ---------------------------
# Row centres at y = -24 / -8 / +8 / +24 ; swatches 10px (y = centre-5),
# arc samples at the row centre, text baseline at centre+4.

emit(
'<g transform="translate(40, 752)">',
'  <rect class="legend-bg" x="-12" y="-36" width="900" height="74" rx="7"/>',
# --- column 1 : microVM colours ---
'  <rect class="tenant-a" x="6"  y="-29" width="10" height="10"/>',
'  <rect class="tenant-b" x="20" y="-29" width="10" height="10"/>',
'  <rect class="tenant-c" x="34" y="-29" width="10" height="10"/>',
'  <rect class="tenant-d" x="48" y="-29" width="10" height="10"/>',
'  <rect class="tenant-e" x="62" y="-29" width="10" height="10"/>',
'  <text class="legend-text" x="80" y="-20">Tenant microVMs (multi-tenant)</text>',
'  <rect class="mvm-infra" x="6" y="-13" width="10" height="10"/>',
'  <text class="legend-text" x="22" y="-4">Infra microVM (etcd, nats, dex, zot, weft, envoy, otel…)</text>',
'  <rect class="runner-gitlab"  x="6"  y="3" width="10" height="10"/>',
'  <rect class="runner-github"  x="20" y="3" width="10" height="10"/>',
'  <rect class="runner-forgejo" x="34" y="3" width="10" height="10"/>',
'  <text class="legend-text" x="50" y="12">CI runner microVMs (GitLab / GitHub / Forgejo)</text>',
'  <rect class="svc-cubefs" x="6" y="19" width="10" height="10"/>',
'  <text class="legend-text" x="22" y="28">CubeFS storage microVMs (S3 + POSIX)</text>',
# --- column 2 : CI job + WireGuard mesh ---
'  <rect class="mvm-ci" x="336" y="-29" width="10" height="10"/>',
'  <text class="legend-text" x="352" y="-20">CI-job microVM (ephemeral)</text>',
'  <path class="wg-link-hi" d="M 336 -6 Q 350 -14 364 -6"/>',
'  <text class="legend-text" x="372" y="-4">Control-plane mesh (infra)</text>',
'  <path class="wg-link" d="M 336 12 Q 350 4 364 12"/>',
'  <text class="legend-text" x="372" y="12">Tenant overlay (workloads)</text>',
'  <rect class="mvm-notebook" x="336" y="19" width="10" height="10"/>',
'  <text class="legend-text" x="352" y="28">Notebook microVM (JupyterHub, per-user)</text>',
# --- column 3 : client / CI links + device ---
'  <path class="client-link" d="M 612 -24 Q 626 -30 640 -24"/>',
'  <text class="legend-text" x="648" y="-20">Client API → weft (gRPC over SRV)</text>',
'  <path class="spawn-link" d="M 612 -6 Q 626 -14 640 -6"/>',
'  <text class="legend-text" x="648" y="-4">CI spawn (weft → job microVM)</text>',
'  <rect class="laptop-deck" x="612" y="7" width="10" height="10"/>',
'  <text class="legend-text" x="628" y="12">Dev laptop (external client)</text>',
'  <path class="forge-link gitlab" d="M 612 25 Q 626 19 640 25"/>',
'  <text class="legend-text" x="648" y="28">External forge → CI runners in all 3 DCs (HA)</text>',
'</g>',
)

emit('</svg>')
print('\n'.join(out))
