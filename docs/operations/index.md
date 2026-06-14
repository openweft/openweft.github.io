# Operations

How to operate a Weft cluster — from initial bring-up to day-2 tasks.
Every infrastructure service the platform runs (etcd, dex, zot, nats,
coredns, cubefs, longhorn, weft-network, weft-webui, otel, …) is
itself a **microVM** on the same substrate that hosts tenant
workloads. There is no separate control-plane box and no
classic-VM-only service in the default stack.

- [Bring up a cluster](bring-up.md) — `weft up` from a `cluster.hcl`,
  one host or three DCs, extensible 1 → 3.
- [Infra services](infra.md) — etcd, dex, zot, nats, cubefs, longhorn,
  weft-network, weft-webui, otel ; what `weft infra bootstrap`
  actually runs.
- [Floating IPs](floating-ips.md) — allocate, map, unmap, release ;
  verifying the host-side nftables NAT ; multi-NIC and migration
  troubleshooting.
