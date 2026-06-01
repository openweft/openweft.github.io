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

## Scheduling and flavors

A **flavor** is the compute envelope — vCPU, RAM, optional **GPU(s)**,
and an optional cap on ephemeral scratch. The scheduler matches a
microVM's flavor against the host inventory in etcd and picks a host
with enough free capacity, honouring the proximity hierarchy
(`AZ ⊃ Rack ⊃ Host`) when a placement rule demands it.

GPUs are treated as just another resource dimension. Flavors declare
them by model and count :

```
$ weft flavor set ai-h200 --vcpu 32 --ram 256Gi --gpu 1 --gpu-type nvidia-h200
$ weft flavor set ws-rtx6 --vcpu 16 --ram 96Gi  --gpu 1 --gpu-type nvidia-rtx-6000-ada
```

The hardware target is **NVIDIA H200** (datacenter, MIG-capable — MIG
slices surface as just another GPU type from the scheduler's point of
view) and **RTX 6000 Ada** (workstation, whole-card bind, no MIG). The
hypervisor driver binds the cards at start time via **VFIO PCI
passthrough** on the QEMU/KVM driver. Apple-VZ doesn't expose discrete
GPUs to guests, so GPU flavors are host-feature-gated ; scheduling
them on a VZ-only host fails the placement up front rather than at
boot.
