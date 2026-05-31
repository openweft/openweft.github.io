# Observability

Two metric surfaces, one trace pipeline, one event bus. All opt-in and
all wireable into the operator's existing stack (Prometheus / VictoriaMetrics
/ OTLP collectors / NATS clients).

## Canonical runbook

End-to-end : the `--metrics-listen` recipe, the gRPC-side histograms,
the Caddy admin metrics bridge :

[**weft/docs/operations/observability.md →**](https://github.com/openweft/weft/blob/main/docs/operations/observability.md)

## What's exposed where

| Surface                         | Endpoint                                             | Covers                                                                          |
| ------------------------------- | ---------------------------------------------------- | ------------------------------------------------------------------------------- |
| **weft-agent /metrics**         | `host:port` from `--metrics-listen`                  | `process_*`, `go_*`, `grpc_server_*` (counters + latency histograms).           |
| **Caddy /metrics**              | Caddy admin socket (see proxy runbook)               | HTTP server metrics, upstream health, ACME state.                               |
| **weft-network /metrics**       | `:9100` on the weft-network daemon                   | RPC counters / latency, etcd-connected gauge, build_info.                       |
| **weft-microvm-agent /metrics** | In-guest, exported per VM via NATS                   | Mesh state, mount status, per-concern apply timings.                            |
| **Events (NATS)**               | `weft events --vm <name>` or NATS subjects directly  | microVM lifecycle, scheduling decisions, driver-plugin events.                  |

## Recommended baseline

For a 3-DC cluster :

1. **VictoriaMetrics** (already deployed by `weft infra bootstrap` —
   see [Infra services](../operations/infra.md)). Scrape config :

    ```yaml
    scrape_configs:
      - job_name: weft-agent
        static_configs:
          - targets:
              - host-a.weft.internal:9090
              - host-b.weft.internal:9090
              - host-c.weft.internal:9090

      - job_name: weft-network
        static_configs:
          - targets:
              - weft-network-a.weft.internal:9100
              - weft-network-b.weft.internal:9100
              - weft-network-c.weft.internal:9100

      - job_name: caddy
        static_configs:
          - targets:
              - host-a.weft.internal:2019
              - host-b.weft.internal:2019
              - host-c.weft.internal:2019
    ```

    See [proxy](proxy.md) for the unix-socket-to-TCP bridge needed for
    Caddy on `:2019`.

2. **Perses** (also part of the infra bundle) — dashboards for the
   gRPC histograms, etcd lag, microVM lifecycle counters.

3. **OpenTelemetry collector** (infra bundle) — receives OTLP traces
   from the agent's gRPC server-side interceptors and from
   weft-network. Forward to your existing trace backend (Tempo /
   Jaeger / Honeycomb / etc.).

## Tracing

The agent's gRPC server-side interceptor emits OTLP spans for every
RPC. Configure the OTLP endpoint via :

```
$ weft agent --otlp-endpoint otel-collector.weft.internal:4317
```

Or via `agent_config { otlp_endpoint = "…" }` in `cluster.hcl`.

## Live event stream

Per-VM events are streamed over NATS and surfaced via :

```
$ weft events --vm <name>
$ weft events --project team-alpha
```

The dashboard's per-VM activity feed subscribes to the same subjects.
See the [API reference](../api/index.md#live-events) for the gRPC
streaming RPC the CLI uses.

## What to alert on

Bare-minimum alert set for a production cluster :

| Alert                                              | Threshold                                                            |
| -------------------------------------------------- | -------------------------------------------------------------------- |
| Agent down                                         | `up{job="weft-agent"} == 0` for > 1m                                 |
| etcd quorum lost                                   | etcd-connected gauge `< 2` across all weft-network instances         |
| Driver plugin crash loop                           | Driver process restarts > 3 in 5m                                    |
| ACME issuance failure                              | Caddy `tls_acme_renewals_failed_total` > 0 over 1h                   |
| Proxy admin socket unreachable                     | weft-network `caddy_admin_apply_failures_total` rate > 0             |
| Trace export drops                                 | OTLP collector `otelcol_exporter_send_failed_spans` rate > 0         |

## Cross-references

- [Proxy](proxy.md) — Caddy admin metrics bridge.
- [Infra services](../operations/infra.md) — VictoriaMetrics + Perses + OTel landing.
- [HA & DR](ha-and-dr.md) — what to watch during a failover.
