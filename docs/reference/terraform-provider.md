# Terraform provider

The `openweft/weft` Terraform provider drives a weft cluster
declaratively : projects, microVMs, networks, load balancers,
scheduling rules, the works. Built on the
[Plugin Framework](https://developer.hashicorp.com/terraform/plugin/framework)
(not the legacy SDKv2 — framework-only by policy).

## Source of truth

| Resource                                                                                          | What lives there                                                                |
| ------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------- |
| [`openweft/terraform-provider-weft`](https://github.com/openweft/terraform-provider-weft)         | Source, examples, GAPS.md.                                                      |
| [README](https://github.com/openweft/terraform-provider-weft/blob/main/README.md)                 | Quickstart, provider config, resource list.                                     |
| [RELEASING.md](https://github.com/openweft/terraform-provider-weft/blob/main/RELEASING.md)        | Tag → goreleaser → registry publish flow.                                       |
| [GAPS.md](https://github.com/openweft/terraform-provider-weft/blob/main/GAPS.md)                  | Known unimplemented resources / fields ; tracks the gap to the gRPC contract.   |
| [examples/](https://github.com/openweft/terraform-provider-weft/tree/main/examples)               | Runnable HCL recipes ; copy-paste-friendly.                                     |
| [Registry](https://registry.terraform.io/providers/openweft/weft/latest)                          | Published provider — once the first tag is cut.                                 |

## Quickstart

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
  # Default = unix socket if reachable, else the cluster's gRPC endpoint.
  socket = "unix:///run/weft/agent.sock"
}

resource "weft_project" "demo" {
  name = "team-alpha"
}

resource "weft_microvm" "demo" {
  name    = "alpine-demo"
  project = weft_project.demo.name
  image   = "alpine:3.21"
}
```

Then :

```
$ terraform init
$ terraform plan
$ terraform apply
```

## Provider configuration

| Field             | Default                            | Notes                                                                  |
| ----------------- | ---------------------------------- | ---------------------------------------------------------------------- |
| `socket`          | `unix:///run/weft/agent.sock`      | Local agent. Use `tcp://host:7443` for cross-host.                     |
| `token`           | `$XDG_CONFIG_HOME/weft/credentials.json` | OIDC token. Acquire via `weft login` on your workstation first.  |
| `insecure`        | `false`                            | Skip TLS verification ; lab clusters only.                             |

## Resource list

Today (early development — see `GAPS.md` for the up-to-date matrix) :

- `weft_project` — tenant project.
- `weft_user` — user under a project (typically managed via OIDC IdP
  instead).
- `weft_microvm` — tenant microVM.
- `weft_network` — overlay network.
- `weft_securitygroup` — L3 / L4 rules.
- `weft_router` — weft-network router resource.
- `weft_loadbalancer` — weft-network load-balancer resource.
- `weft_scheduling_rule` — placement / anti-affinity / DC pinning.
- `weft_volume` — block volume.
- `weft_share` — multi-attach POSIX share (CubeFS or other backends).
- `weft_flavor` — compute envelope.

Each resource exposes the same fields as the corresponding gRPC RPC ;
field names match the proto with idiomatic Terraform snake-casing.

## When the provider is the right tool

| Use the provider when                                | Use the CLI when                                    |
| ---------------------------------------------------- | --------------------------------------------------- |
| Multi-resource declarative state.                    | One-off troubleshooting.                            |
| CI / GitOps pipelines.                               | Streaming logs / events to your terminal.           |
| Composability with non-weft Terraform modules.       | Shell-scriptable lifecycle.                         |
| Long-lived workloads with stable identity.           | Iteration during development.                       |

For the underlying CLI surface the provider drives, see
[Reference : CLI](cli.md).

## Releasing

Maintainers : see
[RELEASING.md](https://github.com/openweft/terraform-provider-weft/blob/main/RELEASING.md)
in the provider repo. Summary of the flow :

1. Tag `vX.Y.Z` on the provider repo.
2. CI (`.github/workflows/release.yml`) runs goreleaser.
3. Goreleaser uploads signed archives + manifest to the GitHub release.
4. Terraform Registry picks them up via the linked GPG key.

Do not auto-publish — the registry publish step is intentionally manual
so a broken release can be unwound before downstream consumers pin it.

## Cross-references

- [microVM quickstart](../getting-started/microvm-quickstart.md) — Terraform
  side-by-side with the CLI.
- [API reference](../api/index.md) — gRPC contract the provider implements.
- [Contributing](../contributing/coding-conventions.md) — framework-only
  policy and other provider-side conventions.
