# config/bootloaders/

**PROTECTED** — every file under this directory is gated by `touches-bootloader`
(security + platform two-team approval) per
[policies/sensitive-change-labels.yml](../../policies/sensitive-change-labels.yml).
Phase-3 solo-maintainer relaxation: PR may carry `solo-maintainer-override` in
addition to `touches-bootloader` + `allowlist-override` and be self-merged after
CI is green. See [CLAUDE.md](../../CLAUDE.md).

## Why it is protected

The bootloader is the **first** code that runs on the device. Silent modification
could bypass measured-boot integrity, disable kernel security parameters,
substitute the kernel image, or add a hidden boot entry. Every binary asset and
every menu line in this tree is reviewed.

## Layout

```
config/bootloaders/
├── README.md                      (this file)
├── isolinux/                      (BIOS boot path, picked up by live-build)
│   ├── isolinux.cfg               top-level: loads vesamenu.c32, includes menu+live
│   ├── menu.cfg                   vesamenu colors + MENU TITLE
│   ├── live.cfg                   DEFAULT + fail-safe boot entries
│   └── splash.png                 640x480 16-color palette PNG
└── grub-pc/                       (UEFI boot path, picked up by live-build)
    ├── config.cfg                 menuentries for Live + fail-safe
    └── theme/
        ├── theme.txt              GRUB theme definition
        └── background.png         1024x768 RGB PNG
```

live-build (`lb config`) finds this directory automatically by virtue of being
named `config/bootloaders/` in the project root — no `--syslinux-theme` flag
needed in `auto/config`. See live-build customization-contents docs.

## Asset provenance

All graphics in this directory are **in-house originals**, derived
deterministically from
[`branding/logo/shikshan-mantra.svg`](../../branding/logo/shikshan-mantra.svg)
at commit `930b877c3011d22c2a456bd86fa122d47528d72d`, using brand tokens from
[`branding/tokens.json`](../../branding/tokens.json).

| File | Dimensions | Format | Source | License |
|------|------------|--------|--------|---------|
| `isolinux/splash.png` | 640x480 | PNG palette (16 colors) | derived from `branding/logo/shikshan-mantra.svg` + `branding/tokens.json` | `SPDX-License-Identifier: CC-BY-SA-4.0` |
| `grub-pc/theme/background.png` | 1024x768 | PNG RGB | derived from `branding/logo/shikshan-mantra.svg` + `branding/tokens.json` | `SPDX-License-Identifier: CC-BY-SA-4.0` |

No third-party binary blobs are included.

## Format constraints

* **splash.png:** 640x480 exactly, <=16 colors, PNG palette mode (LSS16 / legacy
  vesamenu requirement; ADR-0010 locks the stricter color constraint).
* **background.png:** 800x600 or 1024x768, PNG RGB/RGBA. See
  <https://www.gnu.org/software/grub/manual/grub/html_node/Theme-file-format.html>.

## Regenerating the PNG assets

Linux/macOS with librsvg + pngquant:

```bash
rsvg-convert -w 640 -h 480 branding/logo/shikshan-mantra.svg \
  | pngquant 16 --force --output config/bootloaders/isolinux/splash.png -
rsvg-convert -w 1024 -h 768 branding/logo/shikshan-mantra.svg \
  -o config/bootloaders/grub-pc/theme/background.png
```

Cross-platform Python+Pillow alternative: compose brand-token palette and
quantize with `Image.quantize(colors=16, method=Image.Quantize.MEDIANCUT)`. The
canonical renderer that produced the committed PNGs is preserved in the
SMO-0410 PR description. After regenerating, run
`tests/build/test_bootloader_branding.sh` to verify.

## Editing rules

* Every change requires the `touches-bootloader` label.
* Phase-3 solo mode: add `solo-maintainer-override` + `allowlist-override`,
  acknowledge the two-team deviation in the PR body, self-merge after CI green.
* Any new binary asset MUST be documented in the **Asset provenance** table
  above with dimensions, source, and SPDX license.
* No menu-visible string may contain "Debian" — `tests/build/test_bootloader_branding.sh`
  enforces this.
* The matching ADR is [docs/adr/0010-bootloader-visual-identity.md](../../docs/adr/0010-bootloader-visual-identity.md).

## Related

* [docs/phases/phase-4.md](../../docs/phases/phase-4.md) — Phase 4 (full OS branding)
* [docs/adr/0010-bootloader-visual-identity.md](../../docs/adr/0010-bootloader-visual-identity.md)
* [policies/protected-paths.yml](../../policies/protected-paths.yml)
* [auto/config](../../auto/config) — `lb config` invocation; picks up this dir automatically
