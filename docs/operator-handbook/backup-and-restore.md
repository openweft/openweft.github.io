# Backup & restore

Two independent backup tracks because they cover different state :

- **etcd snapshots** — cluster metadata (host registry, image / network
  / volume / security-group catalogues, scheduling rules, dynamic
  per-VM config, tenant + keypair registries). One snapshot per
  cluster, taken from any agent.
- **Per-volume snapshots** — tenant disk state (raw qcow2 / reflink
  clones under the agent state dir). Per-VM, per-volume ; not
  captured by an etcd snapshot.

A clean restore on the etcd side brings the control plane back to the
snapshotted moment, but the underlying volumes have to be backed up
separately or the restore points at content that no longer exists.

## Canonical runbook — etcd

[**weft/docs/operations/etcd-backup.md →**](https://github.com/openweft/weft/blob/main/docs/operations/etcd-backup.md)

It covers :

- What lives in etcd (and what doesn't).
- `etcdctl snapshot save` against the embedded backend's endpoint —
  the discovery quirks for the unix-socket case.
- Snapshot rotation policy.
- Restore against a fresh 3-DC cluster, including the cluster-identity
  swap.
- Validation : `weft host ls` + `weft microvm ls` + `weft infra status`
  against the restored cluster.

## Cadence — minimum sustainable

| What                    | How often                | Where snapshots land                                              |
| ----------------------- | ------------------------ | ----------------------------------------------------------------- |
| etcd snapshot           | Hourly (cron / systemd timer) | Cluster's S3 bucket via CubeFS / Garage ; off-cluster mirror weekly. |
| Per-volume snapshot     | Per workload SLO         | Snapshots live alongside the volume on the host filesystem ; rsync to S3 nightly. |
| Restore drill           | Quarterly                | Lab cluster ; never restore over production without a recent snapshot. |

## Per-volume snapshots

Block volumes are stored as raw / qcow2 files (or reflink CoW images)
under the agent's state directory. Snapshotting a volume means :

1. Quiesce the tenant guest (`weft microvm pause <name>` or have the
   workload's own snapshot hook flush).
2. Take a reflink clone of the volume image. On a host with a
   reflink-capable filesystem (btrfs, xfs+reflink, bcachefs, ZFS-on-Linux,
   APFS via `clonefile(2)`) this is O(1) and zero-copy. See
   [Architecture : storage](../architecture/storage.md#block-volumes-reflink-cow).
3. Resume the guest (`weft microvm resume <name>`).
4. Rsync the snapshot to off-cluster storage.

A `weft volume snapshot` subcommand is on the roadmap to wrap this
flow ; today, the operator runs the steps by hand or via a per-host
cron / systemd timer.

## Restore order

When restoring a cluster from a cold start :

1. Bring up a fresh 3-DC cluster via `weft up -f cluster.hcl --apply`.
2. Restore the etcd snapshot (see canonical runbook).
3. Restore the per-volume snapshots to each agent's state directory.
4. `weft microvm ls --all-projects` — verify the catalogue.
5. `weft microvm start <name>` for each VM that was running at
   snapshot time.

## What's not covered

- **OCI image registry content.** The `zot` cache is rebuilt on demand
  from upstream registries ; no separate backup needed unless you've
  pushed in-cluster-only images, in which case treat zot like any
  other artifact store (volume snapshot + off-cluster mirror).
- **dex's SQLite store.** Tiny ; same volume-snapshot path.
- **Tenant share contents (CubeFS).** Backed up by CubeFS itself ;
  see the CubeFS operator docs for the snapshot story.

## Cross-references

- [Architecture : storage](../architecture/storage.md) — volume
  primitives + reflink semantics.
- [HA & DR](ha-and-dr.md) — failover drill, which complements the
  restore drill.
- Canonical etcd runbook : [weft/docs/operations/etcd-backup.md](https://github.com/openweft/weft/blob/main/docs/operations/etcd-backup.md).
