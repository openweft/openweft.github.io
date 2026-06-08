# Weft documentation

Weft is an open, Go-native cloud platform — **microVM-first, multi-hypervisor,
multi-tenant, multi-AZ**. One binary plays both server and client. Runs on
a laptop, scales to a 3-DC cluster.

This site collects the operator and developer documentation. The landing
page at [openweft.github.io](https://openweft.github.io/) covers the
project overview ; everything below assumes you want to run, integrate
with, or contribute to Weft.

## What weft is

- A single Go binary, `weft`, that runs as a long-lived control daemon
  (`weft agent`) on every host and as a CLI client from anywhere else.
  Pure-Go, `CGO_ENABLED=0` on every platform including darwin — the cgo
  Apple-VZ code lives in the driver plugin, not in `weft`.
- A scheduler that places workloads as **microVMs** (firecracker-style
  boot times, real hardware isolation) on top of pluggable hypervisor
  drivers loaded as external `go-plugin` subprocesses. **Four backends**
  today : `weft-driver-vz` (Apple Virtualization on macOS), `weft-driver-qemu`
  (QEMU/KVM on Linux, QEMU/TCG for dev), `weft-driver-vmd` (OpenBSD `vmd`),
  and `weft-driver-dcs` (Huawei FusionCompute). `weft microvm` is the default
  execution path ; `weft instance` (classic VM) is the escape hatch for
  Windows / BSD guests, network appliances, and custom kernels.
- An L4/L7 data plane built around **Caddy embedded in `weft-agent`** (one
  supervised subprocess per host, L7 via Caddy, L4 via the `caddy-l4` plugin,
  ACME auto-HTTPS built-in), a **WireGuard mesh overlay** (cryptographic
  isolation per tenant ; no VXLAN, no L2 broadcast), and a storage layer
  with **Longhorn** as the replicated block default (`weft-block` is the
  Weft-native data plane fork) plus **CubeFS** for POSIX RWX shares and S3
  buckets.
- An **etcd-backed control plane** with HCL-driven cluster bring-up
  (`weft up --apply` against a `cluster.hcl`), declarative dynamic config
  (`agent_config` blocks pushed over NATS), and a typed gRPC contract
  (`weft-proto` v0.10.0) every component speaks. `weft agent` embeds
  `go.etcd.io/etcd/server/v3/embed` for single-host / dev ; production
  talks to a 3-DC external etcd cluster.

## Who this is for

- **Operators** running weft in production. Start with
  [Getting started](getting-started/single-host.md) and the
  [Operator handbook](operator-handbook/index.md).
- **Developers** integrating weft as a platform. Start with the
  [Terraform provider](reference/terraform-provider.md), the
  [API reference](api/index.md), and the
  [CLI reference](cli/index.md).
- **Contributors** improving weft itself. Start with the
  [Architecture overview](architecture/index.md) and
  [Contributing](contributing/coding-conventions.md).

## High-level shape

```
                +-------------------+
                |  cluster.hcl      |
                | (weft up)         |
                +---------+---------+
                          |
              SSH install + bootstrap
                          v
   +------------+    +------------+    +------------+
   | host-a/DC1 |    | host-b/DC2 |    | host-c/DC3 |
   |  weft-     |    |  weft-     |    |  weft-     |
   |  agent     |<-->|  agent     |<-->|  agent     |
   |  + etcd    |    |  + etcd    |    |  + etcd    |
   |  + Caddy   |    |  + Caddy   |    |  + Caddy   |
   |  + driver  |    |  + driver  |    |  + driver  |
   +------+-----+    +------+-----+    +------+-----+
          |                 |                 |
          +------- WireGuard overlay ---------+
                          |
                  tenant microVMs
                  (weft-microvm-agent in-guest)
```

## Where to start

- [Single-host bring-up](getting-started/single-host.md) — laptop or one VM.
- [3-DC bring-up](getting-started/three-dc.md) — production shape.
- [microVM quickstart](getting-started/microvm-quickstart.md) — first VM.
- [Operator handbook](operator-handbook/index.md) — day-2 operations.
- [Reference](reference/terraform-provider.md) — provider, runners, CLI, API.

## Canonical runbooks

Long-form runbooks live in the `weft` repo under
[`docs/operations/`](https://github.com/openweft/weft/tree/main/docs/operations) ;
this site cross-links to them from the [operator handbook](operator-handbook/index.md)
rather than duplicating.

## Project status

Weft is in **early development**. The codebase is on GitHub under
[github.com/openweft](https://github.com/openweft). Issues and discussions
live on the [`weft`](https://github.com/openweft/weft) repository.
