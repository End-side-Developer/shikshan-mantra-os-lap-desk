---
name: iso-build
description: Build the Shikshan Mantra OS ISO locally using live-build in a clean container. Use when a maintainer asks to "build the ISO", "produce an image", or "test a hook change end-to-end". Requires Debian host with live-build and Docker/Podman.
---

# Skill: iso-build

## When to use
- Maintainer asks for a local ISO build
- A change touches `config/`, `auto/`, or `modules/`
- Pre-release verification before tagging

## Prerequisites
```bash
sudo apt install live-build qemu-system-x86 docker.io
```

## Steps

1. **Verify the workspace is clean**
   ```bash
   git status --porcelain | grep -q . && echo "WARN: uncommitted changes" || true
   ```

2. **Run the wrapper**
   ```bash
   bash scripts/build/build-iso.sh
   ```
   This invokes `auto/build` inside a pinned Debian container so the host's APT state cannot leak into the image.

3. **Verify the artifact**
   ```bash
   bash scripts/verify/verify-iso.sh artifacts/shikshan.iso
   ```
   Asserts SHA-256, lintian baseline, presence of expected packages.

4. **Boot smoke (optional but recommended)**
   ```bash
   bash tests/qemu/boot-bios.sh artifacts/shikshan.iso
   bash tests/qemu/boot-uefi.sh artifacts/shikshan.iso
   ```

## Common failures

| Symptom | Likely cause | Fix |
|---|---|---|
| `lb: command not found` | live-build not installed on host | `sudo apt install live-build` |
| `apt-get update` fails inside container | snapshot.debian.org pin in `config/archives/debian.list.chroot` is stale | Pin to a newer snapshot (requires ADR) |
| Lintian E: tag in `verify-iso.sh` | New package introduced a lintian violation | Either fix the package or add a baselined override in `tests/lintian/` |
| QEMU boot hangs at "Loading initial ramdisk" | Wrong bootloader config | Check `config/bootloaders/` (PROTECTED — needs `touches-bootloader` PR) |

## Forbidden
- Do not edit `config/bootloaders/` or `config/archives/*.key.*` to "fix" a build error — these are protected paths. Open a `touches-bootloader` or `touches-signing` PR with two-team approval.
- Do not commit the built ISO into the repository. It belongs in `artifacts/` (gitignored) and on GitHub Releases.
