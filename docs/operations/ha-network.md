# High availability — network plane

The control plane and data plane of openweft's network stack are
designed to survive both a hypervisor (host) loss and a full
datacenter (DC) loss when the cluster is configured with a 3-DC
quorum substrate. This guide covers what's HA today, what to
configure, and the RTO an operator should expect on each failure
mode.

For the architectural rationale (why WireGuard mesh L3 instead of
VXLAN L2, why BGP /32 announces for floating IPs, ...) see
[Data plane](../architecture/data-plane.md). This guide is the
operator how-to — knobs, log lines, expected timings.

## What's HA out of the box

| Component | Mechanism | Survives |
|---|---|---|
| **etcd cluster** | Raft 3-node quorum | 1/3 node loss |
| **NATS cluster** | NATS clustering (3 nodes) | 1/3 node loss |
| **Longhorn (block volumes)** | 3 replicas spread across hosts | 1 host loss |
| **CubeFS (shares)** | Replicated metadata + data | 1 host loss |
| **`weft` (control plane)** | Stateless ; state in etcd | any single instance |
| **VMs (microVM + classic)** | `SchedulingRule.RespawnPolicy` + etcd watcher | any single host |
| **Firewall in-VM** | Inherits VM HA — subscriber re-applies on respawn | VM-equivalent |

## What you must configure

Two features needed explicit operator opt-in :

### 1. `weft-network` leader election (active-standby)

Run **at least two `weft-network` instances** with the same
`--etcd <endpoints>` value. The daemon now elects one leader per
cluster via the lease-backed key `/weft-network/leader` (10 s TTL,
go.etcd.io/etcd/client/v3/concurrency.Election). Only the leader
runs the reactive long-loops :

- `fips.Subscriber` — drives the BGP /32 announce set from
  `floating_ip.*` events.
- `fips.Poller` — 30 s safety net + startup seed against weft.

Followers still serve gRPC CRUD (writes land in the shared etcd
store anyway) but stay idle on the reactive side. Hard leader
crash → a follower's `Campaign` wins within one TTL window
(≤ 10 s), the new leader's poller seeds from weft before the
publisher fires its first message, BGP announce set is preserved.

**Setup** :

```bash
# DC1
weft-network --etcd https://etcd-dc1:2379,https://etcd-dc2:2379,https://etcd-dc3:2379 \
             --nats nats://nats-dc1:4222 \
             --weft-socket /run/weft/weft.sock

# DC2 + DC3 : identical except for endpoint preference if you want
# locality-first dialing.
```

**What you see in logs** :

```
INFO leader campaign starting key=/weft-network/leader identity=host-dc1.example.com ttl=10
INFO leader acquired key=/weft-network/leader identity=host-dc1.example.com
INFO weft-network became leader ; starting reactive loops
INFO fip index seeded from weft entries=42
INFO fip subscriber wired subject=weft.events.floating_ip.>
```

On a follower :

```
INFO leader campaign starting key=/weft-network/leader identity=host-dc2.example.com ttl=10
# ... blocks here until the leader steps down or its lease expires
```

**Failure cases** :

- Leader process exits cleanly (SIGTERM) : best-effort `Resign`
  fires, a follower acquires in < 100 ms.
- Leader host hard-crashes : the lease TTL has to expire before
  the etcd KV reflects "no leader" ; follower's `Campaign`
  resolves within ≤ 10 s (the configured TTL).
- etcd partition isolates the leader : `concurrency.Election`'s
  session detects the lease loss within the TTL window, `onLost`
  fires, the leader's reactive loops stop ; on the surviving
  quorum side, a follower takes over.

**Single-host dev** (no `--etcd`) : leader election is skipped,
reactive loops run inline as before. No upgrade churn.

### 2. weft-router multi-replica (active-active BGP)

Each tenant `Router` resource grows a new `replicas` field. Set it
to `2` or `3` to spawn that many `weft-router` microVMs (typically
one per DC). All replicas :

- Subscribe to the same NATS subject `weft.router.<uuid>.config`
  and receive identical `DesiredState`.
- Open BGP sessions to the same upstream peer.
- Advertise the same prefixes (operator-typed `Prefixes` +
  the live FIP /32 set).

The upstream peer load-balances inbound traffic via **BGP
multipath (ECMP)**. One replica down → upstream redistributes
within one BGP keepalive window (typically 30-180 s, configurable
on the peer side ; openweft sends keepalives every 30 s by
default).

**Setup** (via the CLI or any client built against
weft-network-proto ≥ v0.1.1) :

```bash
weft-network router create \
    --project   tenant-acme \
    --name      egress-acme \
    --kind      egress \
    --backend   gobgp \
    --networks  edge-net-acme \
    --external  "65512:198.51.100.1" \
    --prefixes  203.0.113.0/24 \
    --replicas  3
```

Server-side validation :

- `replicas == 0` → silently coerced to `1` (single-VM, backward
  compat).
- `replicas > 10` → `InvalidArgument` ; pick a number between 1
  and 10.

**Naming convention** :

- `replicas == 1` → single microVM named `weft-router-<uuid>`
  (legacy layout, no rename on upgrade).
- `replicas >= 2` → microVMs named `weft-router-<uuid>-1`,
  `weft-router-<uuid>-2`, ..., `weft-router-<uuid>-N`.

The lifecycle controller (`lifecycle.WeftClient`) loops every
name on Ensure and probes the full set (legacy + 1..10) on
Destroy — replica counts are not stored across delete, so a
bounded probe with NotFound-tolerant RPCs is the simplest way to
avoid leaking microVMs.

**Configuring BGP multipath on the upstream peer** is the
operator's responsibility — openweft cannot reach the ISP-side
config. For Cisco / Juniper / FRR the knob is typically :

```
# FRR
router bgp 65500
  neighbor 198.51.100.10 remote-as 65512
  address-family ipv4 unicast
    maximum-paths 4    # accept up to 4 equal-cost paths
```

Without multipath configured upstream, you get active-passive
instead of active-active (the BGP best-path algorithm picks one
session ; on its failure, the next-best wins after RFC 4271's
keepalive timeout).

## RTO matrix

| Failure | Component | Observed RTO |
|---|---|---|
| `weft-network` leader process crash (SIGKILL) | reactive loops | ≤ 10 s (lease TTL) + < 500 ms (seed + reconnect) |
| `weft-network` leader graceful shutdown (SIGTERM) | reactive loops | < 1 s (explicit `Resign`) |
| Host running 1/N `weft-router` replicas dies | inbound BGP path via that replica | one BGP keepalive (30 s default) + ISP path redistribution |
| Host running the only `weft-router` replica dies | inbound BGP for the tenant | until SchedulingRule.RespawnPolicy lands the replica elsewhere (≥ keepalive timeout) — set `replicas ≥ 2` to avoid this |
| Host running a VM with a mapped FIP dies | FIP traffic | until the VM respawns + the new host's `weft-agent` watches the next `vm.migrated` event (seconds) |
| DC loss with `replicas == 1` per router and the lost DC hosted the router | inbound BGP for affected tenants | full respawn window (router replicas elsewhere typically requires `replicas ≥ 2`) |
| DC loss with `replicas == 3` (one per DC) | inbound BGP | one BGP keepalive ; ECMP redistributes |

## Troubleshooting

### "I set `replicas=3` but only one microVM appeared"

Check `weft-network`'s gRPC response on CreateRouter — if `replicas`
was sent as `0` (default proto value when the field is omitted)
the server coerces to `1`. Use a client built against
weft-network-proto ≥ v0.1.1 ; check `RouterInfo.replicas` on the
response.

### "Leader election never acquires"

Check the etcd endpoints are reachable :

```sh
ETCDCTL_API=3 etcdctl --endpoints=$ENDPOINTS endpoint health
```

If the quorum is broken (e.g. 2/3 DCs down), `Campaign` blocks
indefinitely — by design ; quorum-less write would corrupt the
lease state.

### "All N `weft-router` replicas are running but only one announces"

Both replicas DO announce — the upstream peer's choice of
"best path" picks one for outbound (your reply traffic uses that
session). Inbound traffic from the public Internet lands on the
host whose BGP path the ISP's transit chose. With ECMP enabled
on the upstream, inbound is balanced. Verify on the upstream :

```sh
# FRR / Cisco neighbour view
show ip bgp 203.0.113.42/32
# Should show N paths if multipath is enabled.
```

### "Failover took longer than expected"

The dominant timer is usually the **BGP keepalive timeout** at the
upstream peer, not openweft itself. Shorten it on the peer side
(e.g. FRR `neighbor X timers 3 9` → 9 s deadline). openweft's
weft-router uses GoBGP defaults (30 s hold) which most ISPs
accept ; ask the peer to match for tighter RTO.

## See also

- [Data plane → Floating IPs (BGP /32 announce)](../architecture/data-plane.md#bgp-announced-32-prefixes-internet-routable)
- [Operations → Floating IPs](floating-ips.md) for the per-FIP lifecycle.
