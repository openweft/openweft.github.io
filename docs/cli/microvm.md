# `weft microvm`

Boot, list, log, and remove tenant microVMs. The Docker-`run` analogue,
and the **default execution path** on the platform — every new feature
lands here first. `weft instance` covers the classic-VM escape hatch
for Windows / BSD guests, network appliances distributed as VM images
(VyOS, OPNsense, …), and workloads that need their own kernel ; both
share the same drivers, scheduler and flavors.

```
$ weft microvm run IMAGE[:TAG] [-- CMD...]
$ weft microvm ls
$ weft microvm logs NAME
$ weft microvm rm NAME...
$ weft microvm pull IMAGE[:TAG]
$ weft microvm pull-kernel REF
$ weft microvm init-build INIT_BINARY
$ weft microvm pod-init-build
```

## `weft microvm run`

Boots a microVM from an OCI image (auto-pulls on cache miss). Anything
after `--` overrides the image's entrypoint+cmd.

```
$ weft microvm run alpine:3.21
$ weft microvm run alpine:3.21 -- sh -c "echo hi"
$ weft microvm run alpine:3.21 --project team-alpha -d
```

| Flag             | Meaning                                                                                                |
| ---------------- | ------------------------------------------------------------------------------------------------------ |
| `--project`      | Project namespace ; empty = agent default.                                                             |
| `-d`, `--detach` | Return once the VM is alive instead of streaming stdio.                                                |
| `--mount-tag`    | virtio-fs tag exposed inside the guest (default `rootfs0`).                                            |
| `--pod`          | Path to a pod manifest JSON — multi-container mode (crun + the pod-initrd assembled by `pod-init-build`). |

## Building the pod-initrd

The pod initramfs combines `weft-init` (PID 1 supervisor) with helper
binaries (crun, cfs-client, weft-microvm-agent) baked at `/bin/<name>` —
no go:embed, no runtime extraction.

```
$ task build-crun                   # weft-microvm-init repo
$ task build-cfs                    # ditto
$ GOOS=linux GOARCH=arm64 go build -o /tmp/weft-init ./cmd/weft-init
$ weft microvm pod-init-build \
    --init       /tmp/weft-init \
    --crun       /tmp/crun.linux.arm64 \
    --cfs-client /tmp/cfs-client.linux.arm64 \
    --agent      /tmp/weft-microvm-agent.linux.arm64
```

Output lands at `$XDG_DATA_HOME/weft-microvm/pod-initrd` by default.
