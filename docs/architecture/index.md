# Architecture

Weft's design rests on a few load-bearing decisions :

- **Single binary, two modes.** `weft agent` runs the control daemon on each
  host ; the same binary acts as the CLI from elsewhere. No separate daemon
  to package, no second wire protocol.
- **microVM-first, classic VM as escape hatch.** `weft microvm` is the
  default execution path : OCI image → fast-boot micro-VM with shared
  kernel and virtio-fs / 9p rootfs. All new platform features land
  here first. `weft instance` covers the cases microVMs can't reach —
  Windows / BSD guests, network appliances distributed as VM images
  (VyOS, OPNsense, pfSense…), workloads that need their own kernel
  (forensics, KASAN, real-time). Both modes share the same hypervisor
  drivers, scheduler, placement rules, flavors (vCPU / RAM / GPU),
  volumes and shares — only the boot model differs.
- **etcd-backed state.** Cluster catalogues and dynamic config live in
  etcd ; weft-agent embeds `embed.Etcd` for dev / single-host, talks to
  an external cluster in HA.
- **Pull model across daemons.** Cross-daemon coordination is reconcile-on-watch,
  not push. The hot path of `weft-agent` is self-sufficient ;
  `weft-network` reconciles from etcd events.
- **Multi-hypervisor via go-plugin — four backends.** Drivers ship as
  standalone subprocesses speaking gRPC ; the core stays pure-Go
  CGO=0 even on darwin. `weft-driver-vz` covers Apple Virtualization
  on macOS, `weft-driver-qemu` covers QEMU/KVM on Linux (QEMU/TCG for
  dev under Tart / nested-virt-free hosts), `weft-driver-vmd` covers
  OpenBSD `vmd(8)`, and `weft-driver-dcs` drives Huawei FusionCompute
  (UVP) via its VRM REST API. Driver images are pulled by digest from
  GHCR per host.
- **Caddy in weft-agent.** The L4/L7 data plane is Caddy embedded as a
  supervised subprocess inside `weft-agent` on every host — no separate
  proxy microVM, no plugin to install. ACME-driven auto-HTTPS. L4 via the
  same Caddy through the [caddy-l4](https://github.com/mholt/caddy-l4)
  plugin. BGP egress, when a tenant needs a public ASN, runs as a
  small `weft-router` microVM speaking
  [GoBGP](https://osrg.github.io/gobgp/) — BGP-4 + EVPN + flowspec,
  programs the kernel FIB via netlink. VyOS / FRR stay as the escape
  hatch via `weft instance` for multi-protocol setups (OSPF / IS-IS /
  RSVP-TE) or BYO config.
- **Default storage backends are CNCF-graduated and replicated.**
  [Longhorn](https://www.cncf.io/projects/longhorn/) for block
  volumes (replicated block, snapshots, backups) ;
  [CubeFS](https://www.cncf.io/projects/cubefs/) for shares and
  buckets (POSIX RWX + S3). Host-device passthrough and file images
  stay as escape hatches for raw bandwidth without replication.
- **GPU as a flavor dimension.** Flavors declare GPUs by model and
  count (`--gpu N --gpu-type nvidia-h200` or `nvidia-rtx-6000-ada`) ;
  the scheduler treats them like vCPU / RAM, picks a host with
  enough free cards, and the hypervisor driver binds them at start
  time via VFIO PCI passthrough on the QEMU/KVM driver.
- **Respawn policy on scheduling rules.** `SchedulingRule.RespawnPolicy`
  (proto v0.10.0) lets a rule declare a respawn block with backoff and
  liveness probe (HTTP / TCP) ; `weft-agent` embeds the state machine
  and a bus subscriber + status poller that detect VM death and
  respawn within the declared budget. V0.1.2 adds systemd
  `Type=notify` integration and `etcdcoord` primitives (host-liveness
  lease, prefix watcher, per-key leader election) as the foundation
  for cross-host failover.
- **Greenfield code is BSD 3-Clause** ; forks-and-adapt keep their
  upstream license (e.g. `weft-block` stays Apache 2.0 as a fork of
  `longhorn-engine`). Third-party deps : Apache 2.0 / MIT / BSD ; SSPL /
  BUSL / RSAL are out by policy.

## Read next

- [Control plane](control-plane.md) — etcd quorum, leader election,
  multi-DC failover.
- [Data plane](data-plane.md) — WireGuard mesh, Caddy proxy, NAT.
- [Storage](storage.md) — Longhorn block volumes (replicated default,
  passthrough escape hatch), CubeFS shares, S3 buckets via gateway or
  native.
