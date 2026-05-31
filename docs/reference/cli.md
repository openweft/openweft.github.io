# CLI surface

The `weft` binary is HashiCorp-style : `weft agent` boots the daemon,
every other subcommand is a client. Every subcommand uses cobra (no
`flag` stdlib anywhere — convention, see [Contributing](../contributing/coding-conventions.md)).

Source for every subcommand lives under
[`cmd/weft/`](https://github.com/openweft/weft/tree/main/cmd/weft) in
the `openweft/weft` repo.

## Top-level commands

```
weft agent                         # long-lived control daemon

# Tenancy
weft project                       # tenant projects
weft user                          # user lifecycle (usually via OIDC IdP)

# Workloads
weft microvm                       # tenant microVMs
weft instance                      # legacy alias / classical VM lifecycle

# Storage
weft volume                        # block volumes (RWO)
weft share                         # POSIX shares (RWX)

# Networking
weft network                       # overlay networks
weft securitygroup                 # L3/L4 rules
weft overlaycmd                    # overlay debug commands

# Compute envelope
weft flavor                        # compute flavours (cpu/mem/disk)

# Platform
weft image                         # OCI image cache
weft script                        # provisioning scripts
weft host                          # hypervisor inventory
weft infra                         # platform services
weft events                        # live event stream

# Cluster lifecycle
weft up                            # bring up from cluster.hcl
weft down                          # tear down

# Auth + admin
weft login                         # OIDC auth
weft admin                         # platform admin
weft clean                         # garbage-collect orphaned state
weft wait                          # block until a resource reaches a state
```

Detailed docs for the two most-used subcommands :

- [`weft agent`](../cli/agent.md) — flags, sockets, what it owns.
- [`weft microvm`](../cli/microvm.md) — run, ls, logs, rm, pull, pod-init-build.

## `weft microvm` quick reference

```
weft microvm run IMAGE[:TAG] [-- CMD...]   # boot a VM from OCI image
weft microvm ls                            # list VMs
weft microvm logs NAME                     # tail guest serial
weft microvm rm NAME...                    # stop + remove
weft microvm pull IMAGE[:TAG]              # warm the image cache
weft microvm pull-kernel REF               # pull the microVM kernel OCI artifact
weft microvm init-build INIT_BINARY        # build the single-binary initrd
weft microvm pod-init-build                # build the pod-mode initrd
```

See [`weft microvm`](../cli/microvm.md) for the full flag matrix.

## `weft volume`

```
weft volume create  NAME --size <bytes> [--flavor <name>]
weft volume ls
weft volume rm      NAME
weft volume attach  NAME --vm <name>
weft volume detach  NAME --vm <name>
```

A `weft volume snapshot` subcommand is on the roadmap to wrap the
reflink CoW path described in
[Backup & restore](../operator-handbook/backup-and-restore.md). Today
the operator runs `cp --reflink=always` (Linux) or `cp -c` (APFS)
against the volume image directly.

## `weft up` / `weft down`

```
weft up   -f cluster.hcl --apply       # bring up from HCL
weft up   -f cluster.hcl --dry-run     # preview the plan
weft down -f cluster.hcl --apply       # tear down
```

Convergent — re-running `weft up` reconciles against declared state
instead of duplicating resources. See
[3-DC bring-up](../getting-started/three-dc.md).

## `weft infra`

```
weft infra bootstrap                       # deploy all infra services
weft infra bootstrap --services etcd,dex   # subset
weft infra status                          # health + placement
weft infra validate                        # check plans
weft infra deploy <service>                # force-redeploy one
```

See [Infra services](../operations/infra.md).

## `weft events`

```
weft events --vm  <name>           # subscribe to a single VM
weft events --project <name>       # subscribe to a project
weft events                        # all events the caller can see (RBAC-scoped)
```

Wraps a gRPC streaming RPC ; the same subjects the dashboard's
activity feed subscribes to. See
[Observability](../operator-handbook/observability.md#live-event-stream).

## `weft login`

```
weft login                                  # opens browser, completes OIDC dance
weft login --provider https://dex.weft.lan  # explicit issuer
```

Token cache at `$XDG_CONFIG_HOME/weft/credentials.json` (mode 0600).

## Global flags

| Flag         | Default                          | Notes                                                                            |
| ------------ | -------------------------------- | -------------------------------------------------------------------------------- |
| `--socket`   | `unix:///run/weft/agent.sock`    | Local agent socket ; override for cross-host CLI use.                            |
| `--server`   | discovered via SRV               | Explicit gRPC endpoint. Format `host:port`.                                      |
| `--project`  | empty (= caller's default)       | Project namespace for the call.                                                  |
| `--insecure` | `false`                          | Skip TLS verification. Lab clusters only.                                        |
| `--debug`    | `false`                          | Verbose logging on the client side.                                              |

## Source

Every subcommand's source lives under
[`cmd/weft/<subcommand>/`](https://github.com/openweft/weft/tree/main/cmd/weft).
The cobra command tree is wired in `cmd/weft/main.go`. For a complete
flag matrix run :

```
$ weft <subcommand> --help
$ weft help <subcommand>
```

## Cross-references

- [`weft agent`](../cli/agent.md), [`weft microvm`](../cli/microvm.md) —
  detailed reference for the two most-used subcommands.
- [API reference](../api/index.md) — the gRPC contract every command
  ultimately drives.
- [Terraform provider](terraform-provider.md) — declarative alternative
  to the imperative CLI.
