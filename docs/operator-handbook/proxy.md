# Reverse-proxy plane

Weft's L4/L7 data plane is **Caddy embedded in `weft-agent`**, supervised
as a subprocess on every host. The agent owns the lifecycle ; routes
land via etcd watch → JSON POST to Caddy's admin socket. ACME-driven
auto-HTTPS, sub-second config reloads, no separate proxy box.

## Canonical runbook

The end-to-end operator guide lives in the `weft` repo :

[**weft/docs/operations/proxy.md →**](https://github.com/openweft/weft/blob/main/docs/operations/proxy.md)

It covers :

- Enabling on a host (HCL `agent_config { proxy { enabled = true } }`
  + CLI `weft agent --proxy`).
- The admin socket path and how to dial it for debugging.
- Route lifecycle — how `LoadBalancer` / `Router` resources in
  weft-network land as Caddy `apps.http.servers` config.
- Caddy `/metrics` enabling and the unix-socket-to-TCP bridge for
  Prometheus scraping.
- TLS posture and cert sharing across hosts via
  `caddy-storage-etcd`.

## Why Caddy in weft-agent

Background and the design tradeoffs that landed on this shape are
covered in the [Architecture : data plane](../architecture/data-plane.md#l4-l7-caddy-in-weft-agent)
page. Short version : crash isolation (Caddy panic doesn't take the
agent down), operational consistency (the agent already supervises
driver-plugin subprocesses), and vendor weight (avoiding ~30
transitive modules pulled by `caddy/v2` as a library).

## Common operator tasks

| Task                                       | Where to look                                                                                                            |
| ------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------ |
| Enable the proxy plane on a host           | [weft/docs/operations/proxy.md#enabling-on-a-host](https://github.com/openweft/weft/blob/main/docs/operations/proxy.md)  |
| Verify a route loaded                      | `curl --unix-socket /run/weft/caddy.sock http://admin/config/`                                                           |
| Tail Caddy logs                            | `journalctl -u weft-agent -f` — Caddy stdio is captured by the supervisor.                                               |
| Scrape Caddy metrics                       | [weft/docs/operations/proxy.md#caddy-admin-metrics](https://github.com/openweft/weft/blob/main/docs/operations/proxy.md) |
| Multi-host cert sharing (no ACME burst)    | `WEFT_PROXY_STORAGE_ETCD_ENDPOINTS` env on each agent. See the runbook.                                                  |

## Cross-references

- [Architecture : data plane](../architecture/data-plane.md) — design rationale.
- [Observability](observability.md) — scrape recipe that includes Caddy's `/metrics`.
- [Reference : CLI](../reference/cli.md) — `weft agent --proxy` flags.

## Legacy : standalone weft-proxy binary

A standalone proxy binary lived in
[`openweft/weft-proxy`](https://github.com/openweft/weft-proxy) before
the in-agent Caddy decision landed. It's still buildable from that
repo for setups that intentionally separate the proxy from the agent
(rare ; usually only worth it when the agent and proxy have very
different lifecycle / blast-radius constraints).

For everything else, prefer the in-agent path covered by the
canonical runbook above.
