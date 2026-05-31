# Data plane

## WireGuard mesh

Every microVM peers with every other microVM across the WAN via WireGuard.
Tenant workloads, infrastructure microVMs, and storage nodes share one
flat address space regardless of which AZ they land in. `weft-network`
owns the desired state ; `weft-microvm-agent` inside each guest applies it
via netlink.

## L4 / L7 — Caddy in weft-agent

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

## NAT and egress

VyOS or FRR handles BGP egress when a tenant needs a public ASN.
WireGuard handles mesh-to-mesh peering between cluster overlays.
