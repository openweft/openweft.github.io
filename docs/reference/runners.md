# CI runners

Weft ships three CI-runner integrations, one per supported forge :
GitHub Actions, GitLab CI, Forgejo Actions. Each is a standalone
operator that registers ephemeral microVM-backed runners against the
forge's API and reaps them when the job finishes.

The three are deliberately separate repos because the forge APIs
diverge enough that a unified controller would be more cost than
benefit. They share the same scheduling pattern (one microVM per job,
hard isolation, no cross-job state).

## Repos

| Forge              | Repo                                                                              | Status                                                                 |
| ------------------ | --------------------------------------------------------------------------------- | ---------------------------------------------------------------------- |
| GitHub Actions     | [`openweft/weft-runner-github`](https://github.com/openweft/weft-runner-github)   | Most-exercised ; reference implementation.                             |
| GitLab CI          | [`openweft/weft-runner-gitlab`](https://github.com/openweft/weft-runner-gitlab)   | Mature ; tracks GitLab Runner's executor contract.                     |
| Forgejo Actions    | [`openweft/weft-runner-forgejo`](https://github.com/openweft/weft-runner-forgejo) | Parity with the GitHub Actions runner since Forgejo Actions is API-compatible. |

## When to use which

| Forge in use                  | Pick                                                       |
| ----------------------------- | ---------------------------------------------------------- |
| GitHub.com or GitHub Enterprise Server | `weft-runner-github`.                              |
| GitLab.com or self-hosted GitLab        | `weft-runner-gitlab`.                              |
| Forgejo / Codeberg            | `weft-runner-forgejo`.                                     |
| Gitea (current)               | `weft-runner-forgejo` works ; Gitea Actions tracks Forgejo's API. |
| BitBucket / Azure DevOps      | No runner today ; PRs welcome.                             |

## Shape

All three follow the same lifecycle :

1. Operator runs the runner controller as a microVM under weft
   (`weft microvm run ghcr.io/openweft/weft-runner-<forge>:latest`)
   with the forge's API token in env.
2. Controller registers as a runner pool, polls for jobs.
3. On job pickup, the controller calls `weft microvm run` to spawn an
   ephemeral microVM with the job's image, mounts the workspace as a
   share, and forwards the runner agent into the guest.
4. Job runs in full microVM isolation ; no cross-job filesystem
   contamination, no cached layer reuse across tenants.
5. On job completion, the controller calls `weft microvm rm` ; the
   reflink-CoW rootfs is freed in O(1).

## Why microVM isolation

The classical CI-runner story (Docker-on-host, k8s pod-per-job, etc.)
shares the host kernel across jobs from different repos / orgs /
tenants. That's a known supply-chain weak point — a malicious PR can
escalate from a job container into the host, then into adjacent jobs.

microVM isolation per job means each CI job is a fresh kernel, fresh
filesystem, fresh network namespace. The cost is the boot time of a
microVM (~1 second on Apple-VZ / KVM, ~5 seconds on TCG). For most CI
workloads this is dominated by image-pull time anyway.

## Operator runbook

Each repo's README is the canonical runbook ; the shared shape is :

1. Deploy the controller as a long-lived microVM with the forge's API
   token in env.
2. Wire the controller's gRPC endpoint to your `weft-agent` socket.
3. Set the runner pool's concurrency limit based on host capacity.
4. Hook metrics (`/metrics` on the controller) into your Prometheus
   scrape (see [Observability](../operator-handbook/observability.md)).

## Cross-references

- [microVM quickstart](../getting-started/microvm-quickstart.md) — same
  lifecycle the controllers drive, in CLI form.
- [Architecture : data plane](../architecture/data-plane.md) — the
  isolation model the runners exploit.
- [Reference : CLI](cli.md) — `weft microvm` commands the controllers
  call.
