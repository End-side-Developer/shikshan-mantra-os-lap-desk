# tests/qemu/

End-to-end boot smoke tests for the built ISO. Used by `.github/workflows/ci-qemu-*.yml`.

| Script | Required-check name | Purpose |
|---|---|---|
| `boot-bios.sh` | `e2e / qemu-bios` | Boot under BIOS, wait for autologin marker |
| `boot-uefi.sh` | `e2e / qemu-uefi` | Boot under OVMF UEFI |
| `persistence.sh` | `e2e / persistence` | (Phase 8 task SMO-0090) Verify persistence partition mount + write |
| `installer-calamares.sh` | `e2e / installer` | (Phase 8 task SMO-0091) Calamares install-to-disk in VM |
| `filtering.sh` | `e2e / web-filtering` | (Phase 8 task SMO-0092) DNS/proxy block tests |
| `module-launch.sh` | `e2e / module-launch` | (Phase 8 task SMO-0093) Module launcher + Kolibri offline |

## Locally

```bash
sudo apt install qemu-system-x86 ovmf
bash scripts/build/build-iso.sh
bash tests/qemu/boot-bios.sh artifacts/shikshan.iso
bash tests/qemu/boot-uefi.sh artifacts/shikshan.iso
```

Each script writes a log under `tests/qemu/logs/` (gitignored). The CI run uploads logs as workflow artifacts for post-mortem.

## Success markers

A boot is "successful" when the serial log contains either:
- `lightdm.*autologin` (LightDM picked up our autologin config), or
- `shikshan.local login` (getty login prompt visible)

The marker is intentionally lenient — we are smoke-testing, not fully testing the desktop. Deeper UI behaviors live in the (forthcoming) installer and module-launch tests.
