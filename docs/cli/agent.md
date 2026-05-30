# `weft agent`

Boots the long-lived control daemon for this host. Embeds etcd in single-host
dev mode, dials an external cluster otherwise. Owns the gRPC API surface
on a stable port and the unix socket the CLI uses locally.

```
$ weft agent --help
$ weft agent                            # default flags, dev-friendly
$ weft agent --az DC-A --rack rack-1    # propagate placement metadata
                                        # to the host registry
```

## Flags

The agent inherits the global `--socket` flag so local CLI calls hit the
same unix socket the daemon publishes. Production flags include the
state directory (`--state-dir`), AZ / rack tags (`--az`, `--rack`), and
the credentials path for the event bus.

## What the agent owns

- Host registration (UUID at `<state-dir>/host-uuid`, idempotent on
  re-registration).
- Driver plugin lifecycle — pulls OCI artifacts for
  `weft-driver-vz` / `-qemu`, launches them as go-plugin subprocesses,
  routes Hypervisor / Network / Volume / Image RPCs.
- Caddy supervision (`weft/agent/proxy/`) — the L4/L7 data plane lives
  here as a supervised subprocess.
- microVM lifecycle — register, start, stop, remove ; events emitted on
  the bus.
