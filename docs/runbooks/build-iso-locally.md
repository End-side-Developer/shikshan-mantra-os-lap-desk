# Runbook — Build the ISO Locally

For maintainers and contributors who need to test a `config/` or `modules/` change before opening a PR.

## Prerequisites

- Debian 12+ or Ubuntu 22.04+ host (the build wrapper uses a pinned Debian container, but the orchestrating host needs `live-build` and a container runtime)
- Docker or Podman
- ≥ 8 GB free disk space
- ≥ 4 GB RAM on the host

```bash
sudo apt update
sudo apt install -y live-build qemu-system-x86 ovmf docker.io
```

## Build

```bash
bash scripts/dev/bootstrap.sh        # one-time: installs pre-commit, cosign, gitsign, syft, etc.
bash scripts/build/build-iso.sh
```

Output: `artifacts/shikshan.iso` (and `.sha256` sibling).

Build time: 40-60 minutes on a 4-core, 8 GB RAM host.

## Quick verify

```bash
bash scripts/verify/verify-iso.sh artifacts/shikshan.iso
```

This checks SHA-256, runs lintian against the ISO contents, and asserts expected packages are present.

## Smoke-test in QEMU

```bash
bash tests/qemu/boot-bios.sh artifacts/shikshan.iso         # BIOS boot
bash tests/qemu/boot-uefi.sh artifacts/shikshan.iso         # UEFI boot
```

Each test boots the ISO with 2 GB RAM, waits for the LXQt session, and runs a smoke check (e.g., the module launcher's `--selftest` flag returns 0).

## When the build breaks

| Symptom | Cause | Fix |
|---|---|---|
| `lb: command not found` | `live-build` not installed | `sudo apt install live-build` |
| `apt-get update` fails in container | snapshot.debian.org pin is stale | Update the pin via `touches-signing` PR + ADR; do NOT bump manually |
| Lintian E: tag | New package introduced a violation | Fix the package; OR add a baselined override in `tests/lintian/` with justification |
| QEMU hangs at "Loading initial ramdisk" | Wrong bootloader config | Open `touches-bootloader` PR; needs two-team approval |
| Out of disk | Container temp files | `docker system prune -af` |

## Forbidden shortcuts

- Editing `config/bootloaders/`, `config/archives/*.key.*`, or `config/packages.chroot/` directly to "make the build pass". These are protected. Open a PR with the appropriate sensitive label.
- Disabling lintian to ship faster.
- Bumping the snapshot pin without an ADR.
- Committing the built ISO into Git. It belongs only in `artifacts/` (gitignored) and on GitHub Releases.
