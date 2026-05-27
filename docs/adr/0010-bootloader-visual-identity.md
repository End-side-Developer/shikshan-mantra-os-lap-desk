---
status: "accepted"
date: 2026-05-27
decision-makers: ["@shikshan/platform", "@shikshan/security"]
consulted: ["@shikshan/devex", "@shikshan/safety"]
informed: ["@shikshan/release-managers"]
---

# 0010 — Bootloader and Plymouth visual identity

## Context and Problem Statement

Shikshan Mantra OS v1 currently shows the default Debian syslinux/GRUB boot menu
("Debian GNU/Linux 13 (trixie) amd64") on first screen after power-on, and shows
no Plymouth splash during kernel → desktop transition. Phase 4 (ADR-0009) branded
all post-login surfaces (greeter, wallpaper, Calamares, welcome dialog) but left
the pre-login boot sequence untouched.

The result is a jarring brand discontinuity: users see "Debian" before they see
any Shikshan Mantra identity. Phase 4 is incomplete until the bootloader menu and
Plymouth splash are replaced.

What is the locked design for: (1) syslinux (BIOS) and GRUB-EFI (UEFI) boot menu
branding, (2) Plymouth splash theme, and (3) the protected-path override process
required to land these changes?

## Decision Drivers

* Boot menu is the first thing a user sees — must say "Shikshan Mantra OS"
* `config/bootloaders/**` is a protected path requiring `touches-bootloader` override
* syslinux splash has strict format constraints (640×480, ≤16 colors PNG/LSS16)
* GRUB theme must be a valid GRUB theme directory (theme.txt + font + image assets)
* Plymouth theme must be installable from Debian trixie (no custom builds in Phase 4)
* No binary blobs without documented upstream source + license
* 2 GB RAM target: no large graphical assets that inflate ISO size significantly

## Considered Options

* **Option A** — Full custom syslinux + GRUB + Plymouth themes with in-house SVG/PNG art
* **Option B** — Minimal text-only override (menu title + entry labels only, no splash graphic)
* **Option C** — Minimal splash (recolor Debian swirl to Shikshan palette) + text override

## Decision Outcome

Chosen option: **"Option A — Full custom themes"**, because the product requires a
complete brand identity at every surface; Option B leaves Debian graphics visible;
Option C still carries Debian art. Phase 4 budget allows custom SVG-derived assets.

### Consequences

* **Good**, because every boot-time surface shows Shikshan Mantra identity consistently.
* **Good**, because `LB_SYSLINUX_THEME` in auto/config can finally be unblocked (was
  deferred since scaffold commit with comment `# deferred to Phase-8 SMO-0061`).
* **Bad**, because `config/bootloaders/**` requires `touches-bootloader` override PR;
  this adds review overhead and cannot be self-merged without `solo-maintainer-override`.
* **Neutral**, because syslinux 640×480 ≤16-color constraint means splash is low-res;
  acceptable for the target low-end device profile.

### Confirmation

Compliance confirmed by:

1. `tests/build/test_bootloader_branding.sh` — asserts live.cfg / grub.cfg title
   strings contain "Shikshan Mantra OS", not "Debian".
2. QEMU BIOS smoke boot: `scripts/verify/qemu-screenshot-boot.sh` captures first
   frame and fails if "Debian" appears (Phase 5 target; Phase 4 ships the script stub).
3. Pre-commit hook `protected-paths` (once SMO-0299 lands) — auto-rejects edits to
   `config/bootloaders/` without `allowlist-override` label.

## Pros and Cons of the Options

### Option A — Full custom themes

* **Good**, because complete brand identity; no Debian artifacts visible.
* **Good**, because foundation for animated Plymouth and future theme variants.
* **Bad**, because requires custom art pipeline and touches protected path.

### Option B — Text-only override

* **Good**, because minimal diff, lowest risk on protected path.
* **Bad**, because Debian swirl graphic still visible; branding incomplete.

### Option C — Recolor Debian swirl

* **Good**, because small diff.
* **Bad**, because ships Debian-derived art; licensing unclear; brand ambiguous.

## Supply-chain and audit implications

syslinux splash source PNG and GRUB background PNG must each have:

* Documented upstream source URL (or "in-house original") in the task's `S:` block
  and in `config/bootloaders/README.md`
* SPDX license identifier
* No binary blobs committed without the above

Plymouth theme: use `plymouth-theme-spinner` or similar Debian-packaged base theme
as a dependency; custom overlay assets follow the same source-doc requirement.

Audit rows written by `post-tool-use/audit-append.sh` on every edit to
`config/bootloaders/**` under the `allowlist-override` override.

## Rollback plan

Revert by deleting `config/bootloaders/` directory and removing the `LB_SYSLINUX_THEME`
and GRUB theme flags from `auto/config`. live-build then falls back to its default
Debian-themed bootloader assets. The rollback commit itself requires a new
`touches-bootloader` override PR.

## More Information

* Related ADRs: [ADR-0009 Login, branding, auth](0009-login-branding-auth.md)
* Related policies: [policies/protected-paths.yml](../../policies/protected-paths.yml),
  [policies/sensitive-change-labels.yml](../../policies/sensitive-change-labels.yml)
* Related runbooks: [docs/runbooks/build-iso-locally.md](../runbooks/build-iso-locally.md)
* Phase doc: [docs/phases/phase-4.md](../phases/phase-4.md)
* Task: [tasks/open/SMO-0410-bootloader-branding.yml](../../tasks/open/SMO-0410-bootloader-branding.yml)
* External references:
  * syslinux isolinux theme format: https://wiki.syslinux.org/wiki/index.php?title=Comboot/menu.c32
  * GRUB theme format: https://www.gnu.org/software/grub/manual/grub/html_node/Theme-file-format.html
  * Plymouth theme authoring: https://freedesktop.org/wiki/Software/Plymouth/
  * live-build bootloader hooks: https://live-team.pages.debian.net/live-manual/html/live-manual/customization-contents.en.html
