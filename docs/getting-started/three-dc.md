# 3-DC cluster bring-up

The production HA shape — three hosts, one per DC, etcd Raft quorum of
three. Tolerates losing any single DC ; the remaining two keep
scheduling, the data plane stays up.

`cluster.Validate` accepts **either 1 or 3 hosts**. 2 and 4+ are
rejected — those topologies have no HA story under Raft.

## Prerequisites

- Three Linux hosts, ideally in three failure-independent locations
  (separate AZs, separate physical sites, separate cloud providers —
  whichever fault domain you actually care about).
- Inter-host network : every pair of hosts must reach `:7443` (gRPC)
  and the WireGuard UDP port (default `:51820`) on every other host.
- Same cloud-init / provisioning recipe as
  [single-host](single-host.md#step-1-provision-the-host) on every host.
- The `weft` CLI on `$PATH` on your workstation.

## `cluster.hcl` for production

```hcl
cluster "weft-prod" {
  overlay { subnet = "10.9.0.0/24" }

  host "host-a" {
    address    = "192.0.2.1"
    dc         = "dc1"
    rack       = "rack-1"
    hypervisor = "qemu"
  }
  host "host-b" {
    address    = "192.0.2.2"
    dc         = "dc2"
    rack       = "rack-1"
    hypervisor = "qemu"
  }
  host "host-c" {
    address    = "192.0.2.3"
    dc         = "dc3"
    rack       = "rack-1"
    hypervisor = "qemu"
  }

  drivers {
    registry = "ghcr.io/openweft"
    version  = "latest"
  }

  microvm {
    kernel_ref = "ghcr.io/openweft/weft-microvm-kernel:latest"
  }
}
```

`dc` is the failure domain ; the scheduler honours the
`AZ ⊃ Rack ⊃ Host` proximity hierarchy when placing replicas. Explicit
DC labels are required at 3-host shape — without them the planner
can't split etcd peers across failure domains.

## Optional — `agent_config` block

For runtime config that should land on each agent (mesh seed, NATS
credentials, metrics listen, etc.), add an `agent_config` block. It is
templated per-host and pushed by `weft up` ; subsequent runs reconcile
the file in place.

```hcl
agent_config {
  metrics_listen = "0.0.0.0:9090"
  proxy {
    enabled    = true
    admin_sock = "/run/weft/caddy.sock"
  }
}
```

Anything not in this block falls back to the agent's compiled defaults.

## Bring-up

```
$ weft up -f cluster.hcl --apply
```

For a clean 3-DC bring-up the planner :

1. Concurrently SSHes into the three hosts, installs / updates the
   agent binary, lays down the systemd unit, starts the daemon.
2. Pulls the driver plugin and microVM kernel from `ghcr.io` (or your
   `drivers { registry = … }` override) on each host.
3. Waits for the three agents to form an etcd Raft cluster (quorum =
   2 of 3).
4. Runs `weft infra bootstrap` to place the infra microVMs across DCs
   (etcd × 3, coredns × 3, dex × 1, zot × 1, nats × 1, cubefs × 3,
   weft-network × 3, weft-webui × 1, otel-collector × 1).

The bring-up is convergent — interrupted mid-flight, re-run, and the
planner picks up from where the previous attempt left off.

## Verify quorum

```
$ weft host ls
$ weft infra status
$ weft admin etcd member-list      # three peers, one leader
```

The HA failover drill validates that the remaining two DCs keep
serving when one is lost. Run it before going to production and once
a quarter afterwards — see the
[HA & DR](../operator-handbook/ha-and-dr.md) page.

## Extending 1 → 3 later

A 1-host dev cluster cannot grow to 3 hosts without a re-bootstrap —
the embedded single-node etcd has a different identity than the
3-peer Raft cluster. The supported path is :

1. `weft etcd snapshot save` against the 1-host cluster
   (see [Backup & restore](../operator-handbook/backup-and-restore.md)).
2. `weft down -f single.hcl --apply` to tear the old cluster down.
3. `weft up -f three.hcl --apply` to bring up the 3-DC shape.
4. `weft etcd snapshot restore` against the new cluster.

State carries over ; the cluster identity doesn't.

## Tear down

```
$ weft down -f cluster.hcl --apply
```

Idempotent ; removes the systemd unit, the agent binary, and the
state directory on every host.

## Next

- [microVM quickstart](microvm-quickstart.md) — schedule the first VM.
- [Operator handbook](../operator-handbook/index.md) — day-2 operations.
- [HA & DR](../operator-handbook/ha-and-dr.md) — failover drill.
