---
description: Build the Shikshan Mantra OS ISO end-to-end (calls the iso-build skill)
allowed-tools: Bash, Read
---

Invoke the `iso-build` skill to produce `artifacts/shikshan.iso`, then run the verify-iso step.

After the build, report:
- ISO path and SHA-256
- Lintian summary (E:/W:/I: counts)
- QEMU BIOS+UEFI smoke status (PASS/FAIL)
- Build wall-clock time

If anything failed, do not modify any file under `config/bootloaders/`, `config/archives/`, or `config/packages.chroot/` — those are protected. File an issue and stop.
