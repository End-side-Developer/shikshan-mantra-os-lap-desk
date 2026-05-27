# Phase 4 — Full OS Visual Identity & Branding

**Status:** In Progress
**ADR:** [ADR-0009](../adr/0009-login-branding-auth.md), [ADR-0010](../adr/0010-bootloader-visual-identity.md)
**Tasks:** SMO-0401 → SMO-041x
**Started:** 2026-05-27

---

## Goal

Replace every surface that currently shows "Debian" branding with Shikshan Mantra OS
branding, producing a consistent visual identity from the first pixel of boot through
install completion. No surface should mention "Debian" to the end user in a production
image; only technical credits in About dialogs are acceptable.

---

## Surfaces Covered

| # | Surface | When it appears | Task |
|---|---------|-----------------|------|
| 1 | Greeter (slick-greeter) | Live session login screen | SMO-0405 ✅ |
| 2 | Desktop wallpaper + LXQt panel branding | After login in live session | SMO-0403 ✅ |
| 3 | Logo sync script | Build-time asset pipeline | SMO-0404 ✅ |
| 4 | First-run welcome dialog | First desktop boot | SMO-0406 ✅ |
| 5 | Auth API contract | Institution-login backend stub | SMO-0407 ✅ |
| 6 | Logout / leave dialog splash | Session end | SMO-0408 ✅ |
| 7 | Calamares installer text + imagery | Install wizard | SMO-0409 ✅ |
| 8 | **Bootloader menu (syslinux + GRUB-EFI)** | First screen on BIOS/UEFI boot | **SMO-0410 🔲** |
| 9 | Plymouth boot splash | Kernel → desktop transition | SMO-0411 🔲 |

---

## Phase 4 Task Index

### Completed

| Task | Title | ADR |
|------|-------|-----|
| SMO-0401 | ADR-0009 login-branding-auth decision | ADR-0009 |
| SMO-0402 | Allowlist expansion for UI-branding paths | ADR-0009 |
| SMO-0403 | UI branding scaffold (wallpaper, tokens, directory layout) | ADR-0009 |
| SMO-0404 | Logo sync script (branding/ → config/includes.chroot/) | ADR-0009 |
| SMO-0405 | slick-greeter theme (colors, logo, hostname label) | ADR-0009 |
| SMO-0406 | First-run welcome dialog (desktop autostart) | ADR-0009 |
| SMO-0407 | Auth API contract v1 (OpenAPI stub, JSON Schema) | ADR-0009 |
| SMO-0408 | Logout/leave splash (LXQt leave dialog override) | ADR-0009 |
| SMO-0409 | Calamares installer branding bundle (text + SVG) | ADR-0009 |

### Open

| Task | Title | ADR | Protected? |
|------|-------|-----|-----------|
| **SMO-0410** | Bootloader menu branding (syslinux BIOS + GRUB-EFI) | ADR-0010 | ✅ `touches-bootloader` |
| SMO-0411 | Plymouth boot splash (shikshan theme) | ADR-0010 | No |

---

## Phase 4 Definition of Done

Phase 4 is complete when **all nine surfaces** show Shikshan Mantra branding:

- [ ] Bootloader menu title = "Shikshan Mantra OS" (not "Debian GNU/Linux 13 (trixie)")
- [ ] Bootloader menu entries = "Shikshan Mantra OS (Live)", "Shikshan Mantra OS (fail-safe)"
- [ ] GRUB splash graphic = Shikshan Mantra logo (not Debian swirl)
- [ ] syslinux splash = Shikshan Mantra logo/colors
- [ ] Plymouth splash = Shikshan Mantra animated logo
- [x] slick-greeter = Shikshan Mantra themed
- [x] Desktop wallpaper = Shikshan Mantra
- [x] Calamares installer = Shikshan Mantra
- [x] Welcome dialog = Shikshan Mantra
- [x] Logout dialog = Shikshan Mantra

CI check: QEMU boot screenshot diff test (Phase 5 target — captures first boot frame and
asserts "Shikshan" text present via OCR or pixel-hash baseline).

---

## Key Constraints

- `config/bootloaders/**` is a **protected path** — all changes require the
  `touches-bootloader` label plus `solo-maintainer-override` (Phase-3) or two-team
  approval (post-contributors). See [policies/protected-paths.yml](../../policies/protected-paths.yml).
- Bootloader changes require an ADR (ADR-0010) before implementation PR.
- syslinux splash must be a valid 640×480 PNG with ≤ 16 colors (isolinux/syslinux constraint).
- GRUB-EFI theme must be a valid GRUB theme directory (theme.txt + assets).
- No binary blobs without a documented upstream source + license in the task's `S:` block.

---

## Related Documents

- [ADR-0009 Login, branding, auth](../adr/0009-login-branding-auth.md)
- [ADR-0010 Bootloader visual identity](../adr/0010-bootloader-visual-identity.md)
- [config/README.md](../../config/README.md)
- [branding/tokens.json](../../branding/tokens.json)
- [auto/config](../../auto/config) — `LB_SYSLINUX_THEME` variable (deferred, unblock in SMO-0410)
