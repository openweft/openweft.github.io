# Architecture

Weft's design rests on a few load-bearing decisions :

- **Single binary, two modes.** `weft agent` runs the control daemon on each
  host ; the same binary acts as the CLI from elsewhere. No separate daemon
  to package, no second wire protocol.
- **etcd-backed state.** Cluster catalogues and dynamic config live in
  etcd ; weft-agent embeds `embed.Etcd` for dev / single-host, talks to
  an external cluster in HA.
- **Pull model across daemons.** Cross-daemon coordination is reconcile-on-watch,
  not push. The hot path of `weft-agent` is self-sufficient ;
  `weft-network` reconciles from etcd events.
- **Multi-hypervisor via go-plugin.** Drivers (`weft-driver-vz`,
  `weft-driver-qemu`, …) ship as standalone subprocesses speaking gRPC ;
  the core stays pure-Go CGO=0 even on darwin.
- **Caddy in weft-agent.** The L4/L7 data plane is Caddy embedded as a
  supervised subprocess inside `weft-agent` on every host — no separate
  proxy microVM, no plugin to install. ACME-driven auto-HTTPS.
- **Libre licensing.** Every component is libre (Apache 2.0 / BSD / LGPL /
  AGPL where unavoidable) ; SSPL / BUSL / RSAL are out by policy.

## Read next

- [Control plane](control-plane.md) — etcd quorum, leader election,
  multi-DC failover.
- [Data plane](data-plane.md) — WireGuard mesh, Caddy proxy, NAT.
- [Storage](storage.md) — block volumes (reflink CoW), CubeFS shares,
  S3 buckets via gateway or native.
