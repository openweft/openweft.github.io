# Single-host bring-up

The fastest path from "fresh Debian arm64 VM" to "weft cluster I can
schedule against". One host, one DC, embedded etcd. About 3 minutes of
real work plus image pulls.

Production deployments should jump straight to the
[3-DC bring-up](three-dc.md) — single-host is the dev / lab shape.

## Prerequisites

- A Linux host (Debian 12 / Ubuntu 22.04+ tested ; arm64 or amd64).
- SSH key authorised on the host, root or a sudoer account.
- Outbound network to `ghcr.io` (driver plugins, kernel, base images).
- KVM available (`/dev/kvm` readable by the user that will run weft-agent).
- A laptop / workstation with the `weft` CLI on `$PATH`. Releases at
  [openweft/weft/releases](https://github.com/openweft/weft/releases).

## Step 1 — provision the host

Use the reference cloud-init `#cloud-config` shipped in the `weft` repo.
It installs the required packages, drops `/etc/weft/agent.env`, and
arms a systemd unit so weft-agent comes up on first boot.

The canonical walkthrough lives at
[openweft/weft : docs/operations/cloud-init.md](https://github.com/openweft/weft/blob/main/docs/operations/cloud-init.md).
Two paths from there :

- **Cloud VM**. Paste the template as user-data on AWS / GCP / Hetzner ;
  first boot lands a host that `weft up --apply` can drive.
- **Bare metal / Tart / Parallels**. Run `cloud-init` from a seed ISO,
  or skip cloud-init entirely and run the equivalent `apt install` +
  `useradd weft` + systemd unit by hand.

## Step 2 — write a `cluster.hcl`

```hcl
cluster "weft-dev" {
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

Replace `address` with the host's reachable IP. The `host` label is the
host id ; `hypervisor = "qemu"` picks the
[`weft-driver-qemu`](https://github.com/openweft/weft-driver-qemu)
plugin — the right choice on Linux and on macOS-VM-without-nested-virt
setups. On Apple Silicon bare metal, use `hypervisor = "vz"` for native
acceleration.

## Step 3 — `weft up`

```
$ weft up -f cluster.hcl --apply
```

The planner :

1. SSHes into each declared host, copies the agent binary, drops the
   systemd unit, starts `weft-agent`.
2. Waits for each agent to register against the embedded etcd (single
   host = single-node etcd, served by the same `weft agent` process).
3. Runs `weft infra bootstrap` to deploy the infra microVMs (etcd
   already up, then dex, zot, nats, coredns, cubefs, weft-network,
   weft-webui, otel-collector). See
   [Infra services](../operations/infra.md).

Re-running `weft up` is idempotent ; it reconciles against the declared
state rather than re-bootstrapping.

## Step 4 — verify

```
$ weft host ls                    # one entry, status=ready
$ weft infra status               # all services with last-observed health
$ weft microvm ls                 # empty list (no tenant VMs yet)
```

Tear down with :

```
$ weft down -f cluster.hcl --apply
```

## Step 5 — schedule the first VM

See the [microVM quickstart](microvm-quickstart.md) — same machine,
runs an alpine guest in ~5 seconds.

## Troubleshooting

| Symptom                                | First check                                                                                    |
| -------------------------------------- | ---------------------------------------------------------------------------------------------- |
| `weft up` SSH timeout                  | Key auth on the host ; `ssh user@host true` works ?                                            |
| `dial unix /run/weft/agent.sock`       | Systemd unit running ? `systemctl status weft-agent` on the host.                              |
| Driver pull fails                      | Host can reach `ghcr.io` ? `curl -sI https://ghcr.io` from the host.                           |
| etcd never reaches `ready`             | Embedded etcd may have stale data in `<state-dir>/etcd` ; wipe + restart for dev.              |
| Caddy refuses to start                 | Run `weft agent --proxy=off` to bypass ; see [proxy runbook](../operator-handbook/proxy.md).   |

## Next

- [3-DC bring-up](three-dc.md) — moves this same shape to production HA.
- [microVM quickstart](microvm-quickstart.md) — schedule a first workload.
- [Operator handbook](../operator-handbook/index.md) — day-2 operations.
