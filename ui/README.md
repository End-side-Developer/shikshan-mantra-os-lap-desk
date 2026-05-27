# ui/

Source tree for human-editable UI components shipped on Shikshan Mantra OS.
See [ADR-0009](../docs/adr/0009-login-branding-auth.md) for the architectural
decision that introduced this directory.

This directory holds **sources only**. At ISO build time,
[scripts/build/sync-ui-to-iso.sh](../scripts/build/sync-ui-to-iso.sh) (added
in SMO-0404) rsyncs each subdirectory into the live-build payload at
`config/includes.chroot/usr/share/shikshan/...`, where it lands on the
running OS as `/usr/share/shikshan/...`. Edits made directly under
`config/includes.chroot/usr/share/shikshan/` (outside of what the sync
produces) will be overwritten on the next build.

## Subdirectories

| Path | Purpose | Sync destination |
|------|---------|------------------|
| `launcher/` | The Shikshan Mantra learning-module launcher (HTML/CSS/JS). Replaces ad-hoc edits under `config/includes.chroot/usr/share/shikshan/launcher/`. | `/usr/share/shikshan/launcher/` |
| `login/` | Post-login welcome dialog (SMO-0406) and any future identity-related UI surfaces (institution login, role picker). | `/usr/share/shikshan/login/` |
| `themes/` | Qt stylesheets (`.qss`), GTK overrides, and theme-specific assets. The default `shikshan-light/` theme lives here. | `/usr/share/shikshan/themes/` |
| `shared/` | Cross-cutting CSS variables, JS utilities, fonts, and other artifacts consumed by `launcher/`, `login/`, and `themes/`. | `/usr/share/shikshan/shared/` |

## Asset masters live in `branding/`

This directory does **not** hold raster/SVG asset masters (wallpapers, logos)
— those live in [branding/](../branding/) and are synced to
`/usr/share/backgrounds/shikshan/` and `/usr/share/shikshan/branding/` by
the same script. Theme colours/typography come from
[branding/tokens.json](../branding/tokens.json).

## Editing rules

- Treat each subdirectory as a self-contained UI package. Do not import from
  sibling subdirectories at build time — share through `shared/` instead.
- HTML files must declare `lang=` and use UTF-8.
- CSS should consume colours from `tokens.json` (inlined at sync time, or
  referenced via CSS custom properties at `:root`).
- No third-party CDN references at runtime — the OS targets offline-first
  use; ship vendored copies under `shared/` when needed.
