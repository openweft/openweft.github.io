# Operator handbook

The operator-facing index. Long-form runbooks live in the
[`weft` repo's `docs/operations/`](https://github.com/openweft/weft/tree/main/docs/operations) ;
this section points at them, frames when each applies, and adds the
cross-component context the in-repo runbooks don't have on their own.

The split exists because runbooks belong next to the code that
implements them (so they ship + version together), and the meta layer
belongs on a portal that aggregates across all the openweft repos.
Bookmark this page ; follow the links.

## Day-2 surfaces

| Concern                                                              | Lives at                                                                                                          |
| -------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------- |
| [Reverse-proxy plane (Caddy)](proxy.md)                              | `weft/docs/operations/proxy.md` — enabling `--proxy`, route lifecycle, admin socket.                              |
| [Observability — metrics + traces](observability.md)                 | `weft/docs/operations/observability.md` — `--metrics-listen`, scrape recipe, Caddy `/metrics`.                    |
| [Backup & restore (etcd + volumes)](backup-and-restore.md)           | `weft/docs/operations/etcd-backup.md` plus the per-volume snapshot path (this site).                              |
| [HA & DR (3-DC failover)](ha-and-dr.md)                              | `weft/docs/operations/ha-failover.md` — quarterly fire drill, recovery procedure.                                 |
| [Security — RBAC + OIDC + TLS](security.md)                          | `weft/docs/operations/rbac.md` for the model ; OIDC + TLS posture summary on this site.                           |
| [Cloud-init host bring-up](https://github.com/openweft/weft/blob/main/docs/operations/cloud-init.md) | `weft/docs/operations/cloud-init.md` — `examples/cloud-init/` reference `#cloud-config`.   |

## When to read what

- **First production deployment.** Read all the linked runbooks
  end-to-end before you turn the cluster over to real workloads. They
  are written assuming you'll skim them twice and then refer back.
- **Incident.** Jump straight to the matching runbook ; this index
  exists so you don't have to remember which repo the runbook lives
  in.
- **Quarterly drill.** [HA & DR](ha-and-dr.md) → run the failover
  script ; [Backup & restore](backup-and-restore.md) → take a fresh
  snapshot, restore into a lab cluster, validate.

## Reading order for new operators

1. [Single-host bring-up](../getting-started/single-host.md) — lab cluster.
2. [microVM quickstart](../getting-started/microvm-quickstart.md) — first workload.
3. [Observability](observability.md) — wire scraping before anything else.
4. [Backup & restore](backup-and-restore.md) — take a snapshot,
   restore it into a throwaway cluster.
5. [Security](security.md) — RBAC + OIDC + TLS posture review.
6. [HA & DR](ha-and-dr.md) — failover drill against a 3-DC lab cluster.
7. [Proxy](proxy.md) — only if you need L7 ingress.

## Where the source-of-truth lives

| Repo                                                                                            | Runbooks                                                                                       |
| ----------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------- |
| [`openweft/weft`](https://github.com/openweft/weft/tree/main/docs/operations)                   | cloud-init, etcd-backup, ha-failover, observability, proxy, rbac.                              |
| [`openweft/weft-proxy`](https://github.com/openweft/weft-proxy)                                 | README — proxy plane standalone binary (legacy ; superseded by in-agent Caddy on most setups). |
| [`openweft/weft-network`](https://github.com/openweft/weft-network)                             | `deploy/` — hardened systemd unit + Dockerfile for the networking control plane.               |
| [`openweft/terraform-provider-weft`](https://github.com/openweft/terraform-provider-weft)       | README + RELEASING.md — provider usage and release flow.                                       |

## Conventions

- Commands run as the `weft` user on the agent host unless noted.
- Lab cluster = throwaway 3-DC cluster on cheap cloud VMs ; never run
  destructive drills (HA failover, etcd restore) against production
  without a recent snapshot.
- Every runbook is dated implicitly by its git history — check
  `git log` in the `openweft/weft` repo if a step looks stale.
