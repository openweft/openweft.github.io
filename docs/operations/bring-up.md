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

## Heterogeneous hypervisors (macOS + Linux)

Drivers are pulled per-host as OCI artifacts at agent startup
([driver plugins](../architecture/data-plane.md) live in their own
sibling repos : `weft-driver-vz` for Apple's Virtualization
framework, `weft-driver-qemu` for QEMU/KVM). The `drivers {}` block
declares every flavour the cluster might use ; each host pulls only
the driver matching its OS.

This makes mixed clusters straightforward — say two Linux racks for
production capacity, plus a couple of Apple Silicon developer
laptops contributing build agents to the same control plane :

```hcl
cluster "weft-mixed" {
  hosts = [
    # Linux production hosts — KVM acceleration via QEMU.
    { name = "host-a", os = "linux",  az = "DC-A", rack = "rack-1", driver = "qemu" },
    { name = "host-b", os = "linux",  az = "DC-A", rack = "rack-2", driver = "qemu" },
    { name = "host-c", os = "linux",  az = "DC-B", rack = "rack-1", driver = "qemu" },

    # macOS developer / build hosts — Apple's Virtualization framework.
    { name = "laptop-1", os = "darwin", az = "DC-C", rack = "desk-1", driver = "vz" },
    { name = "laptop-2", os = "darwin", az = "DC-C", rack = "desk-2", driver = "vz" },
  ]

  # Declare both driver images — each host pulls only the one its
  # `driver` field points at. Local-first cache, then GHCR ; weft
  # keys the cache by digest so re-pulls are free.
  drivers {
    qemu = "ghcr.io/openweft/weft-driver-qemu:latest"
    vz   = "ghcr.io/openweft/weft-driver-vz:latest"
  }

  microvm {
    kernel_ref = "ghcr.io/openweft/weft-microvm-kernel:latest"
  }
}
```

The scheduler honours the proximity hierarchy (`AZ ⊃ Rack ⊃ Host`)
without caring which driver lives on which host — a `placement {
host = "different" }` rule still spreads replicas across as many
hosts as possible, regardless of hypervisor flavour. Tenant
workloads see the same guest substrate either way : same kernel
([`weft-microvm-kernel`](https://github.com/openweft/weft-microvm-kernel)),
same in-guest agent
([`weft-microvm-agent`](https://github.com/openweft/weft-microvm-agent)),
same WireGuard mesh.

!!! note "macOS caveat — no nested virt"
    Inside a macOS VM (Tart, Parallels …) the Apple-VZ driver can't
    boot a guest — Apple doesn't expose nested virt. Use the QEMU
    driver in that case ; QEMU/TCG boots a real Linux microVM
    without acceleration, which is enough for local testing
    (`weft agent --hypervisor=qemu`).

### Apple Silicon host running the QEMU driver

A common variant of the heterogeneous setup : an Apple Silicon host
that runs **QEMU** rather than Apple-VZ. Two situations call for it :

- **Dev inside a macOS VM.** When `weft agent` runs inside a Tart /
  Parallels / UTM guest on an Apple Silicon laptop, Apple-VZ can't
  boot a child VM (no nested virt). The QEMU driver works because
  QEMU/TCG runs as a userspace emulator — slower than KVM, but enough
  to exercise the full microVM lifecycle locally without
  acceleration.
- **Cross-driver parity in CI.** Forcing every host (Linux *and*
  Apple Silicon) onto the same driver keeps test runs reproducible :
  the same QEMU command line is what CI executed.

`driver = "qemu"` overrides the OS-default driver pick — `os = "darwin"`
no longer implies `driver = "vz"`. Only the QEMU driver image needs
to be pulled.

```hcl
cluster "weft-dev-tart" {
  hosts = [
    # Apple Silicon host running weft-agent inside a Tart VM.
    # No nested virt -> Apple-VZ can't run ; fall back to QEMU/TCG.
    { name = "mac-tart-1", os = "darwin", arch = "arm64", driver = "qemu" },
  ]

  # Only the QEMU driver is needed — no point pulling weft-driver-vz
  # since no host targets it.
  drivers {
    qemu = "ghcr.io/openweft/weft-driver-qemu:latest"
  }

  microvm {
    kernel_ref = "ghcr.io/openweft/weft-microvm-kernel:latest"
  }
}
```

The same arrangement works for a bare-metal Apple Silicon host that
the operator deliberately wants under QEMU — for instance to share a
single rootfs path layout with a Linux fleet, or to debug driver
behaviour without the Apple-VZ private framework in the loop.

!!! warning "Expect slower VM startup with TCG"
    QEMU/TCG (no KVM, no Apple-HV) emulates every instruction in
    software. A microVM that boots in ~1 s under Apple-VZ or KVM
    takes several seconds under TCG. Fine for functional testing,
    not for production capacity.
