# HA & DR

Weft's HA story is a **3-DC etcd Raft quorum** (one peer per DC).
Quorum = 2 ; the cluster tolerates losing any one DC and keeps
scheduling + serving with the remaining two. DR (disaster recovery)
covers the case where the cluster is gone and has to be rebuilt from
backups in a fresh location.

The two concerns are linked but separately drilled.

## Canonical runbook — HA failover

[**weft/docs/operations/ha-failover.md →**](https://github.com/openweft/weft/blob/main/docs/operations/ha-failover.md)

It covers :

- Pre-flight checks on the 3-DC cluster.
- Three failure modes : host poweroff, network partition, etcd-process kill.
- Expected behaviour during the outage (what stays up, what fails,
  which gRPC calls return what).
- Recovery procedure when the DC comes back.
- Validation that the cluster reconciled cleanly.

## Cadence

Run the failover drill **every quarter** against a lab cluster, plus
once against production after every major weft upgrade. The cost of
finding out HA doesn't work during a real incident is much higher than
the 20 minutes the drill takes.

A production drill is feasible because the cluster is genuinely
HA — losing one DC during business hours is non-disruptive to tenant
workloads. But always : recent etcd snapshot first, then drill.

## What HA covers

| Failure                                   | Outcome                                                                                       |
| ----------------------------------------- | --------------------------------------------------------------------------------------------- |
| Single DC down                            | Cluster keeps scheduling ; writes go through the remaining quorum.                            |
| Single agent down (DC up)                 | etcd peer leaves, Raft re-elects, the two remaining agents serve.                             |
| Single driver-plugin subprocess crash     | Agent re-spawns it ; in-flight RPCs return `Unavailable`, retry succeeds.                     |
| Caddy crash                               | Agent supervisor re-spawns ; in-flight HTTP requests drop, ACME state preserved on disk.      |
| weft-network instance down                | Two remaining weft-network instances serve ; dashboard falls back to mock for missing data.   |
| WireGuard peer flap                       | Mesh re-converges via watch events ; tenant traffic briefly drops, no operator action.        |

## What HA does NOT cover

| Failure                                   | Mitigation                                                                                                 |
| ----------------------------------------- | ---------------------------------------------------------------------------------------------------------- |
| Two DCs down simultaneously               | Out of quorum — control plane read-only, no scheduling. Recover one DC first.                              |
| All three DCs down                        | Full DR — restore from etcd snapshot into a fresh cluster.                                                 |
| etcd state corruption                     | Restore from snapshot (see [Backup & restore](backup-and-restore.md)).                                     |
| Single-host volume loss                   | Restore per-volume snapshot from off-cluster mirror.                                                       |

## DR procedure

When the cluster is gone (deliberate teardown, catastrophic loss, or
cross-region migration) :

1. **Provision three fresh hosts** in the target location. Match the
   capacity envelope of the old cluster (same flavour mix at minimum).
2. **`weft up -f cluster.hcl --apply`** with the new cluster topology.
   `cluster.hcl` from the old cluster works as-is if `address` values
   are updated to the new hosts ; `dc` / `rack` labels can change.
3. **Restore the etcd snapshot.** See
   [Backup & restore](backup-and-restore.md). The cluster identity is
   new ; tenant catalogue / scheduling rules / dynamic config are
   restored.
4. **Restore per-volume snapshots** to each new host's agent state
   directory.
5. **Validate.** `weft host ls` shows the new hosts ; `weft microvm ls`
   shows the restored catalogue ; `weft microvm start <name>` brings
   each VM back online.

End-to-end DR time depends on per-volume data size — for small
clusters with multi-GB volumes, 30 minutes ; for multi-TB
production state, hours, dominated by volume rsync from S3.

## Cross-references

- [Backup & restore](backup-and-restore.md) — what to snapshot and how
  often.
- [3-DC bring-up](../getting-started/three-dc.md) — initial topology
  that this drill exercises.
- [Observability](observability.md) — what to watch during the drill.
- Canonical HA runbook : [weft/docs/operations/ha-failover.md](https://github.com/openweft/weft/blob/main/docs/operations/ha-failover.md).
