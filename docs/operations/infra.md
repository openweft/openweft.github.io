# Infra services

`weft infra bootstrap` brings up the infrastructure microVMs in
dependency order :

```
$ weft infra bootstrap            # deploys all infra services
$ weft infra bootstrap --services etcd,dex,zot,nats
$ weft infra status               # what's running, where
$ weft infra validate             # check plans against the cluster
$ weft infra deploy <service>     # one service, force-redeploy
```

Each service has a `plan.hcl` shipped in `weft/infra/<service>/` ; the
bootstrap walks them in topological order.

## Default service set

| Service          | Image / source                     | Purpose                                           |
| ---------------- | ---------------------------------- | ------------------------------------------------- |
| etcd             | OCI image                          | Cluster state ; Raft quorum (one per DC).         |
| dex              | OCI image                          | OIDC identity provider.                           |
| zot              | OCI image                          | Local OCI registry ; cached upstream pulls.       |
| nats             | OCI image                          | Event bus + dynamic config push to guest agents.  |
| coredns          | OCI image                          | DNS for `_weft._tcp.weft.internal` SRV records.   |
| cubefs           | OCI image                          | Default storage backend (shares + buckets).       |
| otel-collector   | OCI image                          | OpenTelemetry export pipeline.                    |
| victoriametrics  | OCI image                          | Metrics storage.                                  |
| perses           | OCI image                          | Dashboards.                                       |

## Status

`weft infra status` prints a table of every infra microVM with its host
placement, AZ, and last observed health. Health probes are defined in
the per-service `plan.hcl`.
