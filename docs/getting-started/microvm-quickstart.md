# microVM quickstart

The first VM, two ways : straight from the `weft microvm` CLI, and via
the Terraform provider. Pick whichever matches how you actually drive
infrastructure ; the result is the same scheduled workload.

Both paths assume a working cluster — see
[single-host](single-host.md) or [3-DC bring-up](three-dc.md) if you
don't have one yet.

## Side-by-side — alpine in 5 seconds

=== "weft microvm (CLI)"

    ```
    $ weft microvm run alpine:3.21
    ```

    Auto-pulls the OCI image on cache miss, creates the registration in
    etcd, schedules onto an eligible host, and streams stdio back to
    your terminal. Detach with `-d` if you want it to keep running.

=== "Terraform"

    ```hcl
    terraform {
      required_providers {
        weft = {
          source  = "openweft/weft"
          version = "~> 0.1"
        }
      }
    }

    provider "weft" {
      socket = "unix:///run/weft/agent.sock"
    }

    resource "weft_microvm" "demo" {
      name  = "alpine-demo"
      image = "alpine:3.21"
    }
    ```

    Then :

    ```
    $ terraform init
    $ terraform apply
    ```

## What just happened

1. `weft` resolved `alpine:3.21` against the cluster's image cache.
   Cache miss → pull from the upstream registry into the local
   [`weft-microvm`](https://github.com/openweft/weft-microvm) imagestore.
2. The scheduler picked a host matching the image's required arch
   (and any placement rules).
3. The host's driver plugin (`weft-driver-vz` or `weft-driver-qemu`)
   created a microVM with the right kernel, mounted the rootfs over
   virtio-fs (or 9p with QEMU on macOS hosts), and booted it.
4. `weft-microvm-agent` came up inside the guest, joined the WireGuard
   mesh, and started reporting events back over NATS.

## Useful follow-ups

```
$ weft microvm ls                       # list VMs in the default project
$ weft microvm logs alpine-demo         # tail the guest's serial
$ weft events --vm alpine-demo          # live event stream from NATS
$ weft microvm rm alpine-demo           # stop + remove
```

## With an entrypoint override

```
$ weft microvm run alpine:3.21 -- sh -c 'echo hi from $(hostname)'
hi from alpine-demo
```

Everything after `--` overrides the image's entrypoint+cmd, same as
Docker.

## Detached mode

```
$ weft microvm run alpine:3.21 \
    --project team-alpha \
    -d \
    -- sh -c 'while sleep 5; do date; done'
```

`-d` returns once the VM is alive and writes its registration to
stdout. The guest keeps running until you `weft microvm rm` it.

## Inside a project

`--project` namespaces the VM under a tenant. RBAC checks against
`weft project` membership ; see
[`docs/operations/rbac.md`](https://github.com/openweft/weft/blob/main/docs/operations/rbac.md)
for the model. The Terraform provider takes the same field :

```hcl
resource "weft_microvm" "demo" {
  name    = "alpine-demo"
  image   = "alpine:3.21"
  project = "team-alpha"
}
```

## When to use which path

| Use the CLI when                              | Use Terraform when                                  |
| --------------------------------------------- | --------------------------------------------------- |
| Iterating during development.                 | Standing up a long-lived workload set.              |
| One-off troubleshooting microVMs.             | Multi-resource deployments (VMs + networks + LBs).  |
| Streaming logs / events to your terminal.     | Driving from CI / GitOps pipelines.                 |
| Shell scripts that boot + tear down a guest.  | Cross-tool composability (k8s, vault, …).           |

## Pod mode (multi-container)

For pod-style workloads (multiple containers sharing a microVM, crun as
the runtime), see the
[`weft microvm`](../cli/microvm.md#building-the-pod-initrd) reference.
The pod-initrd is built once with `weft microvm pod-init-build` and
referenced by `weft microvm run --pod <manifest.json>`.

## Next

- [Operator handbook : observability](../operator-handbook/observability.md) — wire metrics + traces.
- [Reference : Terraform provider](../reference/terraform-provider.md) — full resource list.
- [Reference : CLI](../reference/cli.md) — every subcommand at a glance.
