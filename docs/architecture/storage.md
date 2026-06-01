# Storage

Three primitives, deliberately separate :

- **Volume** — single-attach block storage (RWO). Default backend is
  [Longhorn](https://www.cncf.io/projects/longhorn/) (CNCF graduated,
  Apache 2.0) : replicated block, snapshots, backups. Host-device
  passthrough or a file image stay as escape hatches for raw
  bandwidth without replication. Surfaces inside the guest as
  virtio-blk regardless of backend.
- **Share** — multi-attach POSIX filesystem (RWX), provided by a storage
  plugin ([CubeFS](https://www.cncf.io/projects/cubefs/) by default ;
  Ceph or others available).
- **Bucket** — S3 object storage, provided by a storage plugin (CubeFS,
  Garage, Ceph RGW, or VersityGW as an S3 gateway in front of a POSIX
  backend).

The pattern is symmetric : **Longhorn** is to block what **CubeFS** is
to shares + buckets — a CNCF-graduated, replicated, vendor-neutral
backend that the platform installs out of the box.

## Block volumes — Longhorn default

The default block backend is Longhorn, replicated across the host
pool. The data plane lives in
[`weft-block`](https://github.com/openweft/weft-block) — a
fork-and-adapt of [`longhorn-engine`](https://github.com/longhorn/longhorn-engine)
with a Go-native control plane and an NBD frontend (the original
iSCSI path is dropped). Builds linux/arm64 with `CGO=0`. The
controller + replicas + Go-native qcow2 layer (`pkg/qcow` swapped for
the pure-Go `go-diskimages/qcow2`) match the upstream Apache 2.0
license, and `weft-block` plugs into `weft-agent` as a `go-plugin`
`VolumeDriver` (`Name=block`, `Local=false`).

```
$ weft volume create pg-data --type block --size 100Gi --project team-alpha
$ weft volume create pg-fast --type block --source /dev/nvme1n1 --project team-alpha  # passthrough escape hatch
$ weft volume create pg-img  --type file --size 50Gi --project team-alpha             # file image escape hatch
```

All three surface as virtio-blk inside the guest. Snapshots and
backups are Longhorn-native ; the passthrough / file paths offer
neither — they exist for workloads that explicitly trade replication
for bandwidth.

## Block volumes — reflink CoW

Cloning a VM's disk uses copy-on-write on every host filesystem that
exposes one :

- **Linux** — `ioctl(FICLONE)`. Validated end-to-end on Debian arm64 +
  btrfs (`strace FICLONE = 0` confirmed). Works on btrfs, xfs (mounted
  with reflink), bcachefs, and ZFS-on-Linux.
- **macOS** — `clonefile(2)` on APFS. Same O(1) copy semantics ;
  weft-driver-vz invokes it when cloning rootfs images on developer
  laptops and Apple-Silicon hosts where APFS is the only on-disk
  filesystem.
- **Fallback** — when the kernel returns `EOPNOTSUPP` (ext4, FAT,
  cross-volume copies), the path degrades to a regular byte copy
  rather than failing.

See [`weft/cowclone/`](https://github.com/openweft/weft/tree/main/cowclone)
and the `imagestore.NewReflink` wiring on the agent side.

## Storage plugins

The dashboard surfaces a marketplace of storage backends with overlapping
contributions (cubefs ↔ ceph ↔ garage for buckets, etc.). Installing one
opens the gate for the resources it contributes (`shares`, `buckets`) ;
two plugins serving the same resource is supported but typically
meaningful only in specific patterns (e.g. versitygw S3 surface on top
of a CubeFS POSIX backend).

| Plugin            | License    | Contributes      | Notes                                       |
| ----------------- | ---------- | ---------------- | ------------------------------------------- |
| longhorn-block    | Apache 2.0 | volumes (block)  | Default block backend ; CNCF graduated      |
| cubefs-storage    | Apache 2.0 | shares, buckets  | Default share + bucket backend ; CNCF graduated |
| ceph-storage      | LGPL-2.1   | shares, buckets  | Heavier ops, more mature                    |
| garage-buckets    | AGPL-3     | buckets          | Lightweight S3 in Rust                      |
| versitygw-buckets | Apache 2.0 | buckets          | S3 gateway over a POSIX backend             |
| zot-registry      | Apache 2.0 | registries       | Default OCI registry                        |
| harbor-registry   | Apache 2.0 | registries       | RBAC + scanning when needed                 |
