# CLI

The `weft` binary plays two roles depending on the subcommand
(HashiCorp-style) :

- `weft agent` boots the long-lived control daemon for this host.
- Every other subcommand (`weft project`, `weft microvm`, `weft network`, …)
  is a client that dials the local agent over its unix socket, or any
  cluster member over gRPC.

## Top-level commands

```
weft agent                         # long-lived control daemon

weft project / user                # tenancy
weft microvm                       # tenant workloads
weft volume / share                # storage
weft network / securitygroup       # networking
weft flavor                        # compute envelopes
weft image                         # OCI image cache
weft script                        # provisioning scripts
weft host                          # hypervisor inventory
weft infra                         # platform services
weft events                        # live event stream
weft up / down                     # cluster lifecycle from HCL
weft admin                         # platform admin
weft login                         # OIDC auth
```

## Read next

- [`weft agent`](agent.md) — control daemon flags and unix sockets.
- [`weft microvm`](microvm.md) — running workloads.
