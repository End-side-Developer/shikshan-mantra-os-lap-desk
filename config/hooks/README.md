# config/hooks/

Shell hooks invoked by live-build during the chroot and binary-assembly phases.

| Subdir | When invoked | Filename pattern |
|---|---|---|
| `live/` | Inside the chroot, as root | `*.hook.chroot` |
| `normal/` | During binary image assembly, on the build host | `*.hook.binary` |

## Ordering

Files run in lexicographic order. Use a 4-digit numeric prefix (`0010-`, `0020-`, ...) so insertions are easy.

## Rules every hook must follow

- `#!/bin/sh` and `set -eu` at the top.
- Shellcheck-clean (the `live-build-shellcheck` pre-commit hook runs against this directory).
- Idempotent — re-running must not break the chroot.
- No network calls except via `apt-get` (which is already mirror-pinned per `config/archives/`).
- Print a one-line `[hook NNNN] doing thing` at start so build logs are diff-able.
- Never write secrets or PII.

## Adding a hook

1. Pick the next free numeric prefix in the right subdir.
2. Write the hook.
3. Make executable: `chmod +x config/hooks/live/NNNN-name.hook.chroot`.
4. Add a brief comment header explaining purpose and trigger.
5. Add or update a `tests/smoke/` test that verifies the post-condition (e.g., "after 0040, `/etc/dnsmasq.d/shikshan-school-safe.conf` exists and contains 1.1.1.3").

## Removing a hook

A removal is also a behavior change; it needs an ADR if it changes a defaulted-on behavior (autologin, school-safe DNS, etc.).
