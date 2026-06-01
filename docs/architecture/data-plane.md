# Data plane

The data plane is **microVM-first**. Every host workload — tenant or
infra — is a `weft microvm` instance unless the workload genuinely
needs a classic VM (Windows / BSD guest, network appliance distributed
as a VM image, custom kernel). The classic-VM path (`weft instance`)
shares the same drivers, scheduler, flavors, volumes and shares ; only
the boot model differs.

## WireGuard mesh

Every microVM peers with every other microVM across the WAN via WireGuard.
Tenant workloads, infrastructure microVMs, and storage nodes share one
flat address space regardless of which AZ they land in. `weft-network`
owns the desired state ; `weft-microvm-agent` inside each guest applies it
via netlink.

## L4 / L7 — Caddy in weft-agent

The L4/L7 data plane is Go-native by default. L7 (HTTP) uses
[Caddy](https://caddyserver.com) (Apache 2.0, pure-Go, ACME-driven
auto-HTTPS) ; L4 (TCP/UDP) uses the same Caddy through the
[caddy-l4](https://github.com/mholt/caddy-l4) plugin — one binary, no
separate Envoy microVM.

`weft-agent` embeds a supervised Caddy subprocess on every host. The
proxy lives at `weft/agent/proxy/`. Why a subprocess rather than
importing Caddy as a library :

- **Vendor weight.** caddy/v2 pulls ~30 transitive modules (certmagic,
  acmez, libdns, quic-go, …) ; weft's vendor tree would roughly double.
- **Crash isolation.** A panic in Caddy's TLS handshake or ACME
  challenge shouldn't take down weft-agent (which owns the mesh,
  microVM lifecycle, and host registration).
- **Operational consistency.** weft-agent already supervises subprocesses
  (`weft-driver-vz` / `-qemu` via go-plugin).

[`weft-network`](https://github.com/openweft/weft-network) is the
sibling control-plane daemon that owns the LoadBalancer / Router /
DNS / SchedulingRule catalogues. It exposes the
[`NetworkControlPlane`](https://github.com/openweft/weft-network-proto)
gRPC service ; weft-agent dials it to fetch desired state, watches
etcd events for deltas, and POSTs JSON to each Caddy's admin socket
(`POST /load` on a unix socket owned by weft-agent). Sub-second
config apply ; ACME owned entirely by Caddy. weft-network exposes
`/metrics` on a separate port (default `:9100`) for Prometheus
scraping ; build_info + RPC counters + latency histograms +
etcd-connected gauge.

### Cert sharing

By default each host's Caddy mints its own certs against its filesystem
storage. For multi-host clusters, set `WEFT_PROXY_STORAGE_ETCD_ENDPOINTS`
on the weft-agent ; Caddy then uses the `caddy-storage-etcd` adapter
to share issued certs across the cluster, avoiding per-host ACME bursts.

## Routers and egress

Routers and load balancers are first-class resources : declare them in
HCL or via the dashboard, the data plane reconciles. The default
implementations are all Go-native.

- **L7 / L4** — Caddy + caddy-l4 in `weft-agent` (above).
- **Mesh peering** — WireGuard in-kernel, between cluster overlays.
- **BGP egress** — when a tenant needs a public ASN, the platform
  schedules a [`weft-router`](https://github.com/openweft/weft-router)
  microVM running [GoBGP](https://osrg.github.io/gobgp/) (Apache 2.0,
  pure-Go, BGP-4 + EVPN + flowspec — the same engine
  [Calico](https://www.tigera.io/project-calico/) and
  [Cilium](https://cilium.io/) ship). It programs the kernel FIB via
  netlink, boots in a few hundred milliseconds, footprint ~tens of MB.
- **NAT egress** — for tenants without an ASN, plain netfilter / nft
  pushed by `weft-network` directly onto the hosts. No VM at all.

### Escape hatch — VyOS / OPNsense / FRR

When a tenant needs a complex multi-protocol setup (OSPF / IS-IS /
RSVP-TE) or wants to bring their own router config, run it as a
classic VM via `weft instance` — same deal as for Windows guests and
other VM-image appliances. This is the only path on which VyOS /
OPNsense / FRR are deployed by the platform ; the Go-native router /
LB stack covers everything else.

## Block volumes — Longhorn default

The default backend for `weft volume create --type block` is
[Longhorn](https://www.cncf.io/projects/longhorn/) (CNCF graduated,
Apache 2.0) — replicated block storage with snapshots and backups
spread across the host pool, so losing a host doesn't lose the
volume. Two escape hatches stay available for specialised workloads :
`--source /dev/nvmeXn1` passes a host device straight through (raw
bandwidth, no replication), and `--type file` is a host-side image.
All three surface as virtio-blk via the `weft` Volume driver. See
[Storage](storage.md) for the symmetric pattern on shares (CubeFS).
