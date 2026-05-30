# Control plane

The control plane is **three `weft agent` instances**, one per DC, forming
an etcd Raft quorum. Each instance runs as a regular microVM on the same
substrate that hosts tenant workloads — there is no separate
control-plane box.

## State

All cluster state lives in etcd : project / user catalogues, microVM
registrations, scheduling rules, dynamic per-VM config, lock leases.
Reads are served by any agent ; writes are forwarded to the Raft
leader transparently.

For local development (one host, no HA), `weft agent` embeds
`go.etcd.io/etcd/server/v3/embed` so the same binary boots a single-node
etcd alongside its own services.

## Endpoint discovery

Clients resolve the per-DC `weft agent` addresses through SRV records
served by the per-DC CoreDNS microVMs :

```
_weft._tcp.weft.internal.  IN SRV  0 33 7443 weft-a.weft.internal.
_weft._tcp.weft.internal.  IN SRV  0 33 7443 weft-b.weft.internal.
_weft._tcp.weft.internal.  IN SRV  0 33 7443 weft-c.weft.internal.
```

Same shape Consul / Nomad use — no external load balancer, no anycast,
client retries the next entry on failure.

## Authentication

OIDC tokens issued by dex carry tenant grants. Every agent caches dex's
JWKs locally, so token validation never crosses a DC boundary.
