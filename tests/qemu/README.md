# tests/qemu/

End-to-end boot smoke tests for the built ISO. Used by `.github/workflows/ci-qemu-*.yml`.

| Script | Required-check name | Purpose |
|---|---|---|
| `boot-bios.sh` | `e2e / qemu-bios` | Boot under BIOS, wait for autologin marker |
| `boot-uefi.sh` | `e2e / qemu-uefi` | Boot under OVMF UEFI |
| `run-smoke.sh` | `e2e / qemu-smoke` | Orchestrates BIOS + UEFI and emits JUnit XML |
| `persistence.sh` | `e2e / persistence` | (Phase 8 task SMO-0090) Verify persistence partition mount + write |
| `installer-calamares.sh` | `e2e / installer` | (Phase 8 task SMO-0091) Calamares install-to-disk in VM |
| `filtering.sh` | `e2e / web-filtering` | (Phase 8 task SMO-0092) DNS/proxy block tests |
| `module-launch.sh` | `e2e / module-launch` | (Phase 8 task SMO-0093) Module launcher + Kolibri offline |

## Invocation forms

Both `boot-bios.sh` and `boot-uefi.sh` accept two argument forms:

```bash
# Full path (any directory):
bash tests/qemu/boot-bios.sh path/to/shikshan-mantra-os-1.2.3.iso

# Bare bundle basename (resolved under RELEASES_DIR, default: releases/):
bash tests/qemu/boot-bios.sh shikshan-mantra-os-1.2.3.iso
```

The bare-basename form is the primary path when using the canonical `releases/` layout produced by `scripts/build/build-iso.sh`.

## Pre-flight verification

Before launching QEMU, each script calls `scripts/verify/verify-iso.sh <iso>`. The verification checks:

- All companion artifacts present (`.sha256`, `.sha512`, `.cdx.json`, `.spdx.json`,
  `.intoto.jsonl`, `.intoto.jsonl.sig`, `MANIFEST.txt`)
- SHA-256 and SHA-512 hashes match

If verification fails the script exits **4** (see exit code table below) without invoking QEMU.

## Locally

```bash
sudo apt install qemu-system-x86 ovmf
bash scripts/build/build-iso.sh
# Using canonical releases/ layout:
bash tests/qemu/boot-bios.sh shikshan-mantra-os-1.2.3.iso
bash tests/qemu/boot-uefi.sh shikshan-mantra-os-1.2.3.iso
```

Each script writes a log under `tests/qemu/logs/` (gitignored). The CI run uploads logs as workflow artifacts for post-mortem.

## Environment variables

| Variable | Default | Purpose |
|---|---|---|
| `RELEASES_DIR` | `<repo-root>/releases` | Directory searched when a bare basename is given |
| `SHIKSHAN_QEMU_LOG_DIR` | `tests/qemu/logs` | Directory for boot log files |
| `OVMF_CODE` | `/usr/share/OVMF/OVMF_CODE.fd` | UEFI firmware code (boot-uefi.sh only) |
| `OVMF_VARS` | `/usr/share/OVMF/OVMF_VARS.fd` | UEFI variable store template (boot-uefi.sh only) |

## Exit codes

| Code | Meaning |
|---|---|
| `0` | Success marker matched in serial log |
| `1` | Usage error / missing ISO file / OVMF firmware not found |
| `2` | Deadline exceeded (540 s) without success marker |
| `3` | QEMU process exited before success marker appeared |
| `4` | `verify-iso.sh` failed — companion missing or hash mismatch |

## Orchestrator: run-smoke.sh

`run-smoke.sh <iso-path-or-basename>` runs `boot-bios.sh` then `boot-uefi.sh` in
sequence. The UEFI leg always runs even if BIOS fails, so the JUnit report is
always complete. Exit code: `0` only if both legs exit `0`; otherwise the first
non-zero leg's exit code is propagated (BIOS checked first).

A single timestamped run directory is created under
`${SHIKSHAN_QEMU_LOG_DIR:-tests/qemu/logs}/run-<UTC-ISO8601>/`:

| File | Contents |
|---|---|
| `bios.log` | Combined stdout+stderr of the BIOS leg |
| `uefi.log` | Combined stdout+stderr of the UEFI leg |
| `junit.xml` | JUnit XML, one `<testcase>` per leg, `<system-out>` carries the log |

### Test-injection environment variables (integration tests only)

| Variable | Default | Purpose |
|---|---|---|
| `BOOT_BIOS` | `<script-dir>/boot-bios.sh` | Override BIOS leg path (stub target) |
| `BOOT_UEFI` | `<script-dir>/boot-uefi.sh` | Override UEFI leg path (stub target) |

## Success markers

A boot is "successful" when the serial log contains either:

- `lightdm.*autologin` (LightDM picked up our autologin config), or
- `shikshan.local login` (getty login prompt visible)

The marker is intentionally lenient — we are smoke-testing, not fully testing the desktop.
Deeper UI behaviors live in the (forthcoming) installer and module-launch tests.
