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
deploys the infrastructure **microVMs** in dependency order (etcd →
dex, zot, nats, coredns → longhorn (block) + cubefs (shares + buckets)
→ weft-network / weft-webui → otel-collector / victoriametrics /
perses). Every infra service runs as a microVM — no classic VMs in the
default stack. See [Infra services](infra.md).

The networking control plane (routers / LBs / DNS zones / scheduling
rules) is now provided by the
[`weft-network`](https://github.com/openweft/weft-network) daemon —
its `Dockerfile` + hardened systemd unit live in the repo's
`deploy/` directory. The dashboard
([`weft-webui`](https://github.com/openweft/weft-webui)) dials it via
`--weft-network-socket` ; when unreachable, the Networking panels
fall back to mock state transparently so a missing daemon doesn't
take the dashboard down.

## Minimal `cluster.hcl`

Each host is one labelled HCL block. The label is the host id ; `address`
is required, `dc` defaults to the host id, `hypervisor` shortcuts to a
single-driver host (the modern multi-driver `driver { … }` form lives
below).

```hcl
cluster "weft-lab" {
  overlay { subnet = "10.9.0.0/24" }

  host "host-1" {
    address    = "192.0.2.1"
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

A 3-DC layout adds two more `host` blocks with explicit DC labels :

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

!!! info "Topology constraint"
    `cluster.Validate` accepts **either 1 or 3 hosts** today — the two
    supported HA shapes. A 2-host or 4+-host layout is rejected. The
    snippet below illustrates the heterogeneous *form* on a single
    `host` example ; replicate the block (with distinct `dc` labels)
    to land on the 3-DC shape.

```hcl
cluster "weft-mixed" {
  overlay { subnet = "10.9.0.0/24" }

  # Linux production host — KVM acceleration via QEMU.
  host "host-a" {
    address    = "192.0.2.1"
    os         = "linux"
    arch       = "amd64"
    dc         = "dc1"
    rack       = "rack-1"
    hypervisor = "qemu"
  }
  # …two more `host` blocks with dc = "dc2" / "dc3" to make a 3-DC cluster.

  # Driver source. `registry` + `version` define defaults ; per-flavour
  # overrides (vz_ref / qemu_ref) take precedence when set. Each agent
  # pulls only the driver image it actually needs.
  drivers {
    registry = "ghcr.io/openweft"
    version  = "latest"
  }

  microvm {
    kernel_ref = "ghcr.io/openweft/weft-microvm-kernel:latest"
  }
}
```

A macOS host on the same cluster mirrors the same shape with
`os = "darwin"` and `hypervisor = "vz"`. The cluster planner doesn't
care which driver runs where — the scheduler matches each microVM's
required arch against the host's declared capability.

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

`hypervisor = "qemu"` overrides the OS-default driver pick — an
`os = "darwin"` host no longer implies VZ. Only the QEMU driver image
needs to be pulled.

```hcl
cluster "weft-dev-tart" {
  overlay { subnet = "10.9.0.0/24" }

  # Apple Silicon host running weft-agent inside a Tart VM.
  # No nested virt -> Apple-VZ can't run ; fall back to QEMU/TCG.
  host "mac-tart-1" {
    address    = "192.0.2.1"
    os         = "darwin"
    arch       = "arm64"
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

The same arrangement works for a bare-metal Apple Silicon host that
the operator deliberately wants under QEMU — for instance to share a
single rootfs path layout with a Linux fleet, or to debug driver
behaviour without the Apple-VZ private framework in the loop.

!!! warning "Expect slower VM startup with TCG"
    QEMU/TCG (no KVM, no Apple-HV) emulates every instruction in
    software. A microVM that boots in ~1 s under Apple-VZ or KVM
    takes several seconds under TCG. Fine for functional testing,
    not for production capacity.

### Apple Silicon host running BOTH drivers (cross-arch builds)

A bare-metal Apple Silicon host can run **both** drivers side-by-side.
The canonical reason is multi-arch builds : VZ handles the native
arm64 guests at full Apple-HV speed, and QEMU/TCG covers the foreign
architectures (amd64 today ; riscv64 / loongarch64 when needed) for
cross-compile and multi-arch OCI image production.

The host gains one nested `driver "kind" { … }` block per driver it
runs ; each declares the guest architectures that driver can launch on
this host. The scheduler matches a microVM's required architecture
against this set when placing the workload. When `driver` blocks are
present, the legacy `hypervisor = "…"` shortcut MUST be omitted —
they're mutually exclusive.

```hcl
cluster "weft-build" {
  overlay { subnet = "10.9.0.0/24" }

  # Apple Silicon build host — native arm64 via VZ, foreign archs
  # via QEMU/TCG. The two drivers run as separate go-plugin
  # subprocesses owned by the same weft-agent ; the scheduler
  # picks one per microVM based on `arch`.
  host "build-mac-1" {
    address = "192.0.2.1"
    os      = "darwin"
    arch    = "arm64"

    driver "vz" {
      arch = ["arm64"]                          # native, accelerated
    }
    driver "qemu" {
      arch = ["amd64", "riscv64", "loongarch64"] # emulated
    }
  }

  # Both driver images are needed — this host pulls both.
  drivers {
    registry = "ghcr.io/openweft"
    version  = "latest"
  }

  microvm {
    kernel_ref = "ghcr.io/openweft/weft-microvm-kernel:latest"
  }
}
```

A typical multi-arch build pipeline then runs N parallel `weft microvm
run` calls on the same host — one per target arch — and the agent
dispatches each to the matching driver. A `--arch` flag on
`weft microvm run` is on the roadmap ; today the agent infers the
arch from the OCI image manifest.

!!! warning "Single-driver agent today"
    The HCL schema, host registry, and scheduler all support multi-driver
    hosts ; commits [`65d237896`](https://github.com/openweft/weft/commit/65d237896),
    [`e6ceb7591`](https://github.com/openweft/weft/commit/e6ceb7591),
    [`f8926164c`](https://github.com/openweft/weft/commit/f8926164c) land
    the wire. The **agent** still launches a single weft-driver-`<kind>`
    subprocess per host, so a `host` block declaring both `driver "vz"`
    and `driver "qemu"` is honoured by Validate but only the first
    matching driver is actually started today. Multi-plugin lifecycle
    is the follow-on milestone — a tracking issue lives on
    [weft#issues](https://github.com/openweft/weft/issues).

The non-native runs are slow (TCG cost — see the warning above), but
parallel on the same host they're still much cheaper than spinning up
remote builders : no SSH, no network artifact transfer, the OCI image
cache is shared between drivers via the host-local
[`weft-microvm`](https://github.com/openweft/weft-microvm) imagestore.
