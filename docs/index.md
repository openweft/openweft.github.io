# Weft documentation

Weft is an open, Go-native cloud platform — multi-hypervisor, multi-tenant,
multi-AZ. One binary plays both server and client. Runs on a laptop, scales
to a 3-DC cluster.

This site collects the operator and developer documentation. The landing
page at [openweft.github.io](https://openweft.github.io/) covers the
project overview ; everything below assumes you want to run, integrate
with, or contribute to Weft.

## Where to start

- [Bring up a cluster](operations/bring-up.md) — from one host to three DCs.
- [Architecture overview](architecture/index.md) — control plane, data plane,
  storage, and the libre licensing stance.
- [CLI reference](cli/index.md) — `weft agent`, `weft microvm`, `weft project`,
  and the rest.
- [API reference](api/index.md) — gRPC contract, REST surface for the
  dashboard, OpenAPI schema.

## Project status

Weft is in **early development**. The codebase is on GitHub under
[github.com/openweft](https://github.com/openweft). Issues and discussions
live on the [`weft`](https://github.com/openweft/weft) repository.
