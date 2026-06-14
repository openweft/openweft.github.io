# Floating IPs

Floating IPs (FIPs) are public-routable addresses allocated from an
edge network and bound to a private VM. The lifecycle mirrors the
OpenStack model — `allocate` reserves the address, `map` attaches it
to a VM, `unmap` detaches, `release` returns it to the pool — and
the host-side NAT is reconciled by `weft-agent` from
`floating_ip.*` events on the platform bus. See
[Data plane → Floating IPs](../architecture/data-plane.md#floating-ips-host-side-nftables-nat)
for the design rationale.

This guide is the operator how-to : real commands, real outputs,
and the failure modes you'll meet on the way.

## Allocate a floating IP

Pull the next free address from an edge network's CIDR. The
network must already exist (created by the cluster operator as
part of the `weft-network` bring-up) and have available addresses
in its pool.

```
$ weft floating-ip allocate --project proj-acme --network public-edge
allocated  4d2c1e9a-…-b71f  203.0.113.42  public-edge  available
```

The output columns are : `UUID`, `address`, `network`, `status`.
A freshly allocated FIP is `available` — it owns the address but
no traffic flows yet. `--project` defaults to the caller's default
project when omitted ; `--network` is required.

The registry skips the network and broadcast addresses, the
declared gateway, and every IP already taken by a port. If the
pool is exhausted the call fails with a clear error and no
address is consumed.

## Map to a VM

Attach an allocated FIP to a VM by name. The target VM must be
in the same project as the FIP and have at least one port with
an assigned private IP.

```
$ weft floating-ip map 4d2c1e9a-…-b71f --target web-1
mapped  4d2c1e9a-…-b71f  203.0.113.42  vm/web-1  active
```

Server-side, the registry flips the FIP to `status=active` and
publishes a `floating_ip.mapped` event on the platform bus. The
per-host Watcher in `weft/floatingipnat` picks up the event,
recomputes the local VM → FIP mappings, and asks the nftables
Reconciler to install the matching DNAT + SNAT rules on the host
that actually runs `web-1`. No agent restart, no manual
plumbing.

Map is **idempotent on the same target** : re-running
`weft floating-ip map <uuid> --target web-1` against an already-
active mapping is a no-op (no event, no nftables churn).
Targeting a *different* VM while the FIP is still active is
rejected — unmap first.

The `--kind` flag accepts `vm` (default) and `lb`. `lb` is
reserved in the registry and proto for the future load-balancer
binding ; **it is not wired through the data plane today**. Use
`vm` for production work.

## Verify the NAT is live

NAT installation happens on the **host that runs the target VM**,
not the host you ran the CLI from. SSH to that host and inspect
the dedicated nftables table :

```
$ sudo nft list table ip weft-fip-nat
table ip weft-fip-nat {
    chain prerouting {
        type nat hook prerouting priority dstnat; policy accept;
        ip daddr 203.0.113.42 dnat to 10.9.0.17 comment "fip→vm web-1"
    }
    chain postrouting {
        type nat hook postrouting priority srcnat; policy accept;
        ip saddr 10.9.0.17 snat to 203.0.113.42 comment "vm web-1→fip"
    }
}
```

What to check :

- One `dnat` rule per active mapping in `prerouting`, one matching
  `snat` rule per active mapping in `postrouting`.
- The `comment` field carries the VM name — fast visual mapping
  from rule to tenant intent under `nft -a list ruleset`.
- The table name is always `weft-fip-nat`. The Reconciler owns
  this table exclusively ; don't add hand-rolled rules to it
  (they will be wiped on the next reconcile pass).

The Reconciler uses the same `google/nftables` (pure-Go netlink)
backend as the firewall reconciler and applies its rule set in a
single netlink batch, so an external observer never sees a
half-applied policy.

The Reconciler doesn't expose its own `/metrics` endpoint today —
operational signal flows through the same channels as the rest
of `weft-agent` :

- `weft-agent` logs (`floatingipnat: applied N mapping(s) on host
  <uuid>` on every successful reconcile, and `floatingipnat:
  apply: <error>` on failure).
- The platform bus, which carries the underlying
  `floating_ip.{allocated,mapped,unmapped,released}` events the
  Watcher reacts to.

If a mapping is in `status=active` in the registry but the
host's `weft-fip-nat` table is empty, the agent log on that host
is the first place to look.

## Unmap and reallocate

`unmap` detaches a FIP from its current target and returns it to
`available` :

```
$ weft floating-ip unmap 4d2c1e9a-…-b71f
unmapped  4d2c1e9a-…-b71f  203.0.113.42  available
```

The FIP keeps its UUID and address ; it can be re-mapped to a
different VM in the same project without going through Release
and Allocate again :

```
$ weft floating-ip map 4d2c1e9a-…-b71f --target web-2
mapped  4d2c1e9a-…-b71f  203.0.113.42  vm/web-2  active
```

Unmap is **idempotent on an already-unmapped FIP** — calling it
again is a no-op, no event published, no nftables churn. The
NAT rules on the host that *was* running the target are removed
by the same reconcile pass that reacted to `floating_ip.unmapped`.

## Release

Release returns the address to the network's free pool. The FIP
must be `available` — Release on an `active` FIP is rejected by
the registry :

```
$ weft floating-ip release 4d2c1e9a-…-b71f
Error: floating ip "4d2c1e9a-…-b71f" is active (mapped to vm "web-2") — unmap before releasing
```

Unmap first, then release :

```
$ weft floating-ip unmap   4d2c1e9a-…-b71f
$ weft floating-ip release 4d2c1e9a-…-b71f
4d2c1e9a-…-b71f
```

Release is idempotent on missing — re-running it against an
already-released FIP is a no-op.

## Troubleshooting

### "I allocated and mapped, but the Internet doesn't reach my VM"

Two paths get traffic to land on the host running the target VM :

**Host-side NAT** (always on). The Reconciler installs DNAT + SNAT
rules in `ip weft-fip-nat` on the host that runs the target VM.
This makes the FIP reachable on the LAN — enough for testing,
intra-cluster traffic, or environments where the upstream router
has a static route pointing the FIP's prefix at the host's public
interface.

**BGP-announced /32 prefixes** (active when weft-network has a
NATS-backed event bus). For tenants with a `weft-router` microVM
configured for the project's edge network (kind=egress +
backend=gobgp), every mapped FIP is announced as a /32 (or /128
for v6) prefix to the upstream peer via GoBGP, alongside the
operator-typed Prefixes. The path is :

```
weft → "floating_ip.mapped" event
     → weft-network's fips.Subscriber updates its per-network index
     → publisher.StateFor appends <addr>/32 to DesiredState.Prefixes
     → re-Publish on weft.router.<uuid>.config
     → weft-router's GoBGP AddPath → upstream ISP
```

Verify the announce arrived upstream :

```sh
# on weft-router (over the tenant overlay or via "weft microvm exec"):
gobgp neighbor <peer-ip> adj-out | grep <fip>/32
# or look at the BGP RIB on the upstream side
```

If the FIP is in the table on the host but missing from `gobgp
neighbor <peer-ip> adj-out`, check (a) `weft-network` has
`--nats <url>` set, (b) the Router's `networks` includes the FIP's
edge network, (c) the BGP session to the upstream is in the
`Established` state.

Single-host dev (`--nats` empty) skips the BGP layer entirely — FIPs
stay host-NAT only, which is the right default for local work.

### "The VM migrated to another host and the FIP didn't follow"

The Watcher subscribes to `vm.migrated` (along with `vm.created`,
`vm.deleted`, `vm.state_changed`, and the `port.*` events) and
reconciles every host's local table on every relevant event. In
the happy path you should see, within seconds of the migration :

- the **source** host's `weft-fip-nat` table dropping the
  prerouting + postrouting rules for the FIP ;
- the **destination** host installing the matching pair.

If both tables show the rule (split-brain) or neither does,
inspect the `weft-agent` logs on both hosts for
`floatingipnat: apply:` errors. The Watcher's pure
`ComputeLocalMappings` projection is deterministic given the
adapter snapshot ; persistent disagreement points at a stale
adapter view, not at NAT logic.

### "My VM has multiple NICs — which one gets the FIP ?"

In v0 the Watcher picks the **lowest-UUID port** that has an
assigned IP. The choice is deterministic per VM but not
operator-controlled. A future revision will let `MapFloatingIP`
carry an explicit port UUID so an operator can target a specific
NIC. Until then, if you need the FIP on a specific NIC, either
keep your VM single-NIC for FIP-exposed workloads or order the
port creation so the intended NIC's UUID sorts first.

## Limits and caveats

- **IPv4 only.** The Reconciler emits `ip daddr` / `ip saddr`
  rules ; IPv6 is not yet supported.
- **One mapping per FIP.** The registry enforces a single active
  target per FIP. To share an address across multiple backends,
  use a Load Balancer.
- **`target_kind = "lb"` is reserved but not wired.** The proto
  field accepts `vm` and `lb` ; only `vm` is honoured end-to-end
  today. LB binding will land alongside the load-balancer data
  plane.
- **Host-side NAT only.** As covered in troubleshooting above,
  external reachability still depends on upstream routing.

## See also

For the design rationale — why a per-host NAT reconciler over the
existing event bus, the
`Watcher.ComputeLocalMappings` purity contract, and how the
nftables table relates to the firewall reconciler — see
[Data plane → Floating IPs](../architecture/data-plane.md#floating-ips-host-side-nftables-nat).
