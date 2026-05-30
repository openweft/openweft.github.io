# Bring up a cluster

`weft up` provisions a day-0 cluster from a `cluster.hcl` file. One host
or three DCs, extensible 1 → 3 later without re-bootstrap. The planner
in `weft/cluster` is convergent — re-running `weft up` against an
existing cluster reconciles toward the declared state instead of
duplicating resources.

## Hypervisor access

`weft up` reaches the hypervisors over SSH to install the agent and
drive lifecycle. Pre-requisites :

- SSH key authorised on each target host.
- The host can pull the OCI artifacts referenced by `cluster.hcl`
  (kernel, driver plugins, microVM rootfs).

## Composing services

After `weft up` finishes the host bring-up, `weft infra bootstrap`
deploys the infrastructure microVMs in dependency order (etcd → dex,
zot, nats → cubefs → otel). See [Infra services](infra.md).

## Minimal `cluster.hcl`

```hcl
cluster "weft-lab" {
  hosts = ["host-1.example"]

  drivers {
    qemu = "ghcr.io/openweft/weft-driver-qemu:latest"
  }

  microvm {
    kernel_ref = "ghcr.io/openweft/weft-microvm-kernel:latest"
  }
}
```

A 3-DC layout adds two more hosts plus AZ / rack labels :

```hcl
cluster "weft-prod" {
  hosts = [
    { name = "host-a", az = "DC-A", rack = "rack-1" },
    { name = "host-b", az = "DC-B", rack = "rack-1" },
    { name = "host-c", az = "DC-C", rack = "rack-1" },
  ]
  # … drivers / microvm sections identical
}
```
