# Coding conventions

The conventions every weft repo follows. They exist so a PR in any
repo lands without having to relearn the project's idioms.

## Language + toolchain

- **Go**. Every server-side and CLI binary. Targets the current
  Go release ; `go.mod` pins the major version. `CGO=0` is the
  default on every platform including darwin — cgo / Apple entitlement
  code lives only inside `weft-driver-vz`.
- **`go` lives at `/usr/local/go/bin/go`**, not on `PATH` by default
  on the dev hosts. Export `PATH` before invoking build scripts ;
  `task build` handles this for you.
- **`task` lives at `~/go/bin/task`**. Every repo has a `Taskfile.yml`
  with the canonical entry points.

## CLI convention — cobra everywhere

Every CLI (the main `weft` binary plus the mini-binaries in
`weft-microvm`, `weft-driver-*`, `weft-runner-*`, etc.) uses
[cobra](https://github.com/spf13/cobra). The `flag` stdlib is
**never** used, even for mono-mode binaries — porting legacy `flag.*`
on the way past is part of the convention. New subcommands extend the
existing cobra command tree.

## Shell scripts — pkgx bash

Scripts use the pkgx bash shebang :

```bash
#!/usr/bin/env -S pkgx bash
```

This pins bash 5.x rather than Apple's bash 3.2. zsh-isms (`[[ ... ]]`,
arrays, parameter expansion features) work as expected.

Loop variables : **never use `path`** as a loop variable name in zsh —
it's tied to `PATH` (lowercase / uppercase aliasing), and the
silent overwrite breaks cgo builds without any error. Use `p` /
`file` / `entry` instead.

## CLI tool installation — pkgx first

Default tool installation is via [pkgx](https://pkgx.sh/) so versions
are pinned and reproducible. brew is a fallback only when pkgx
doesn't carry the tool (rare).

## Workspace layout

- `github.com/openweft/` is the root org dir under
  `~/share/github.com/`.
- Each repo is a subdirectory of the org. Sibling repos (`weft`,
  `weft-microvm`, `weft-driver-vz`, …) are at the same level — none
  is nested inside another.
- The `go-*` repos were moved to siblings of `openweft/` ;
  cross-references in code use module paths, not relative paths.

## Coverage — Plan B

- 100% coverage target on **pure-Go logic**.
- Generated code, `main()`, cgo, AppKit bindings are explicitly
  excluded from the coverage target.
- Test harnesses are reusable across packages ; helpers go in
  `internal/testutil` or a sibling `<package>_test` package.

## Naming — hypervisor-agnostic CLI

The CLI is `weft <subcommand>` ; **never** `vz-*` / `kvm-*` /
`qemu-*` even when the subcommand only makes sense for one
hypervisor. The control daemon is `weft agent`, **never** `vzd`
(legacy ; do not reintroduce). The driver binaries (`weft-driver-vz`,
`weft-driver-qemu`) are the only place a hypervisor name appears.

## Naming sweep 2026-05-30

A complete sweep renamed `vzd` / `vzc` / `ncl` / `nano-container-linux`
to `weft` / `weft-microvm`. Tombstones were removed. Environment
variables, sockets, NATS subjects, kernel command-line args — all
renamed. **Do not reintroduce the legacy names in new code.**

## Terraform provider — framework-only

The provider is built on the
[Plugin Framework](https://developer.hashicorp.com/terraform/plugin/framework),
never SDKv2. Any new resource lands as a framework resource. If you
find SDKv2 code in the provider, it's a migration target, not a
template.

## Release flow — no auto-publish

Tags trigger CI, CI runs goreleaser, goreleaser produces signed
artefacts. **Publishing to downstream registries (Terraform Registry,
ghcr.io for runners, etc.) is intentionally manual** — a broken
release can be unwound before consumers pin it.

## Container images — local-first, GHCR fallback

Driver plugins, the microVM kernel, and the runner controllers are
pulled OCI-style. The pull chain is **local-first → ghcr.io fallback**,
cached by digest. Cluster config can override the registry via
`cluster.hcl`'s `drivers { registry = … }` block or per-flavour `*_ref`
overrides.

## License posture

Every component is libre — Apache 2.0 / BSD / MIT / LGPL / AGPL where
unavoidable. SSPL / BUSL / RSAL are **out by policy** ; pulling a
dependency under those licences is a hard no, even transitively.

If a dependency moves to a non-libre licence (the historical
elastic / mongo / cockroach story), it's swapped or forked, not pinned
to the pre-relicence tag indefinitely.

## In-guest dynamic config — pattern

`weft-microvm-agent` applies runtime config received over NATS via
the per-concern `Subscriber + ApplyFunc` pattern. One subscriber per
concern (mesh = WireGuard, mounts = SFTP / FUSE), one subject per VM,
idempotent. New concerns extend the pattern ; they don't bypass it.

Dependencies for in-guest applies (FUSE / SFTP libraries) belong in
`weft-microvm-agent`, **not** in `weft-init` — the initramfs stays
minimal.

## Cross-references

- [Architecture overview](../architecture/index.md) — the design
  decisions these conventions implement.
- [Reference : CLI](../reference/cli.md) — surface every cobra
  subcommand lives on.
- [Reference : Terraform provider](../reference/terraform-provider.md) —
  framework-only policy in action.
