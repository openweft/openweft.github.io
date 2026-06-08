# Infra services

`weft infra bootstrap` brings up the infrastructure **microVMs** in
dependency order. Every service the platform installs by default
runs as a `weft microvm` — there are no classic VMs in the standard
stack ; `weft instance` is reserved for tenant workloads that need
it (Windows / BSD guests, VM-image network appliances).

```
$ weft infra bootstrap            # deploys all infra services
$ weft infra bootstrap --services etcd,dex,zot,nats
$ weft infra status               # what's running, where
$ weft infra validate             # check plans against the cluster
$ weft infra deploy <service>     # one service, force-redeploy
```

Each service has a `plan.hcl` shipped in `weft/infra/<service>/` ; the
bootstrap walks them in topological order.

## Default service set

| Service          | Image / source                       | Purpose                                                       |
| ---------------- | ------------------------------------ | ------------------------------------------------------------- |
| etcd             | `ghcr.io/openweft/weft-etcd`         | Cluster state ; Raft quorum (one per DC). 4-arch built in-house. |
| dex              | `ghcr.io/openweft/weft-dex`          | OIDC identity provider. 4-arch built in-house.                |
| zot              | `ghcr.io/openweft/weft-zot`          | Local OCI registry ; cached upstream pulls. 4-arch.           |
| nats             | `ghcr.io/openweft/weft-nats`         | Event bus + dynamic config push to guest agents. 4-arch.      |
| coredns          | `ghcr.io/openweft/weft-coredns`      | DNS for `_weft._tcp.weft.internal` SRV records. 4-arch.       |
| longhorn         | OCI image (`weft-block` data plane)  | Default block-volume backend (replicated, snapshots, backups). |
| cubefs           | OCI image                            | Default shares + buckets backend (POSIX RWX + S3).            |
| weft-network     | `ghcr.io/openweft/weft-network`      | Routers / LBs / DNS zones / scheduling rules control plane.   |
| weft-router      | `ghcr.io/openweft/weft-router`       | Per-tenant BGP speaker (GoBGP) — only when a tenant declares an ASN. |
| weft-webui       | `ghcr.io/openweft/weft-webui`        | Browser dashboard ; talks to weft-agent + weft-network. 4-arch. |
| weft-doctor      | `ghcr.io/openweft/weft-doctor`       | AI log triage v0.1 (Ollama-only, passive — NATS in, NATS out). |
| weft-loom-server | `ghcr.io/openweft/weft-loom-server`  | Collaborative editor v0.2 (CodeMirror 6 + Yjs relay) ; optional. |
| otel-collector   | OCI image                            | OpenTelemetry export pipeline.                                |
| victoriametrics  | OCI image                            | Metrics storage.                                              |
| perses           | OCI image                            | Dashboards.                                                   |

The 4-arch infra images (`weft-etcd`, `weft-dex`, `weft-nats`, `weft-zot`,
`weft-coredns`) are built from source in-house under
[`openweft/weft-*`](https://github.com/openweft) — multi-stage
Dockerfiles, distroless base, tag-gated workflows that target
**amd64 + arm64 + riscv64 + loong64** via `buildx` + qemu binfmt.

### weft-network

The networking control plane, sibling repo
[`openweft/weft-network`](https://github.com/openweft/weft-network).
Implements every RPC in [`weft-network-proto`](https://github.com/openweft/weft-network-proto)
(routers, load balancers, DNS zones, DNS records, scheduling rules)
and persists state in etcd under `/weft/network/*`. Three replicas
per cluster, etcd-elected leader owns the data-plane reconciler
(WireGuard peer config push, BGP daemon programming, Caddy config
deltas), followers serve read-only snapshots and forward writes.

Operability shape :
- listens on `unix:///run/weft-network/weft-network.sock` (or
  `tcp:host:port` for cross-host clusters)
- exposes `/metrics` on `:9100` (separate listener — scrape failures
  can't take down the control plane) — Prometheus build_info, RPC
  counters + latency histograms, etcd-connected gauge
- `/healthz` on the same metrics listener for load-balancer probes
- ships a hardened systemd unit + Dockerfile (see the repo's
  `deploy/` directory for the install playbook)

When weft-network is unreachable, the dashboard's Networking panels
degrade transparently to mock state — no hard error, no operator
intervention. Pointing `weft-webui --weft-network-socket <addr>` at
the daemon swaps mock for live.

## Status

`weft infra status` prints a table of every infra microVM with its host
placement, AZ, and last observed health. Health probes are defined in
the per-service `plan.hcl`.
