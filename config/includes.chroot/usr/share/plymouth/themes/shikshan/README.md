# Shikshan Mantra Plymouth theme

Plymouth boot splash shown during the kernel → desktop transition. This is the
final branding surface in Phase 4 (see [docs/phases/phase-4.md](../../../../../../docs/phases/phase-4.md)
and [ADR-0010](../../../../../../docs/adr/0010-bootloader-visual-identity.md)).

Unlike `config/bootloaders/**`, this directory is **not** in
`policies/protected-paths.yml#deny`. Edits follow the normal allowlisted-PR flow.

## Files

| File | Purpose |
|------|---------|
| `shikshan.plymouth` | Theme descriptor (INI). Sets ModuleName=script. |
| `shikshan.script` | Plymouth scripting DSL — places logo, pulsing caption, message handler. |
| `logo.png` | 320×320 RGBA, centered logo (in-house). |
| `background.png` | 1366×768 RGB, brand-dark with faint wordmark (in-house). |

## Asset provenance

Both PNGs are in-house originals derived from
[`branding/logo/shikshan-mantra.svg`](../../../../../../branding/logo/shikshan-mantra.svg)
and [`branding/tokens.json`](../../../../../../branding/tokens.json), licensed
`SPDX-License-Identifier: CC-BY-SA-4.0`. No third-party blobs.

## How the theme is activated

`config/hooks/live/0033-plymouth-default.hook.chroot` runs at chroot build time
and either:

1. Calls `plymouth-set-default-theme -R shikshan` (preferred), OR
2. Writes `/etc/plymouth/plymouthd.conf` with `[Daemon] Theme=shikshan` (fallback).

The `plymouth` and `plymouth-themes` packages are pulled in via
[`config/package-lists/plymouth-shikshan.list.chroot`](../../../../../../config/package-lists/plymouth-shikshan.list.chroot).

## Regenerating PNGs

Cross-platform Python+PIL recipe:

```python
from PIL import Image, ImageDraw
# logo: 320x320 RGBA, draw flame-above-book disc using brand palette
# background: 1366x768 RGB filled with #0B1620, optional wordmark
```

The canonical renderer that produced the committed PNGs is preserved in the
SMO-0411 PR description. After regenerating, run
`tests/build/test_plymouth_theme.sh` to verify.
