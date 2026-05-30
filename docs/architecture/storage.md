# Storage

Three primitives, deliberately separate :

- **Volume** — single-attach block storage (RWO). Host device passthrough
  or a file image ; surfaces inside the guest as virtio-blk.
- **Share** — multi-attach POSIX filesystem (RWX), provided by a storage
  plugin (CubeFS by default ; Ceph or others available).
- **Bucket** — S3 object storage, provided by a storage plugin (CubeFS,
  Garage, Ceph RGW, or VersityGW as an S3 gateway in front of a POSIX
  backend).

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

| Plugin            | License    | Contributes      | Notes                           |
| ----------------- | ---------- | ---------------- | ------------------------------- |
| cubefs-storage    | Apache 2.0 | shares, buckets  | Default backend ; CNCF graduated |
| ceph-storage      | LGPL-2.1   | shares, buckets  | Heavier ops, more mature         |
| garage-buckets    | AGPL-3     | buckets          | Lightweight S3 in Rust           |
| versitygw-buckets | Apache 2.0 | buckets          | S3 gateway over a POSIX backend  |
| zot-registry      | Apache 2.0 | registries       | Default OCI registry             |
| harbor-registry   | Apache 2.0 | registries       | RBAC + scanning when needed      |
