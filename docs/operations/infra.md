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

| Service          | Image / source                     | Purpose                                                       |
| ---------------- | ---------------------------------- | ------------------------------------------------------------- |
| etcd             | OCI image                          | Cluster state ; Raft quorum (one per DC).                     |
| dex              | OCI image                          | OIDC identity provider.                                       |
| zot              | OCI image                          | Local OCI registry ; cached upstream pulls.                   |
| nats             | OCI image                          | Event bus + dynamic config push to guest agents.              |
| coredns          | OCI image                          | DNS for `_weft._tcp.weft.internal` SRV records.               |
| longhorn         | OCI image                          | Default block-volume backend (replicated, snapshots, backups). |
| cubefs           | OCI image                          | Default shares + buckets backend (POSIX RWX + S3).            |
| weft-network     | `ghcr.io/openweft/weft-network`    | Routers / LBs / DNS zones / scheduling rules control plane.   |
| weft-router      | `ghcr.io/openweft/weft-router`     | Per-tenant BGP speaker (GoBGP) — only when a tenant declares an ASN. |
| weft-webui       | `ghcr.io/openweft/weft-webui`      | Browser dashboard ; talks to weft-agent + weft-network.       |
| otel-collector   | OCI image                          | OpenTelemetry export pipeline.                                |
| victoriametrics  | OCI image                          | Metrics storage.                                              |
| perses           | OCI image                          | Dashboards.                                                   |

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
