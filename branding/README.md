# branding/

Source tree for Shikshan Mantra OS visual identity assets — wallpaper
masters, the project logo, greeter chrome, and the canonical colour /
typography tokens. See
[ADR-0009](../docs/adr/0009-login-branding-auth.md) for the architectural
decision that introduced this directory.

This directory holds **asset masters only**. At ISO build time,
[scripts/build/sync-ui-to-iso.sh](../scripts/build/sync-ui-to-iso.sh)
(added in SMO-0404) copies the assets into the live-build payload at the
destinations listed below. Direct edits to the synced destinations under
`config/includes.chroot/` will be overwritten on the next build.

## Subdirectories

| Path | Purpose | Sync destination |
|------|---------|------------------|
| `wallpapers/` | Desktop and greeter background images. Source format: PNG (1920x1080 default + smaller alternates) or SVG with a build-time rasterisation step. | `/usr/share/backgrounds/shikshan/` |
| `logo/` | Project logo in SVG (master). Used by the greeter, the welcome dialog, the launcher header, and the LXQt panel. | `/usr/share/shikshan/branding/logo/` |
| `greeter/` | `lightdm-slick-greeter` config (`slick-greeter.conf`) and any greeter-specific overrides (e.g., custom CSS the greeter consumes via `theme-name`). | `/etc/lightdm/` (via hook 0031, SMO-0405) |

## tokens.json

[`tokens.json`](tokens.json) is the canonical source of truth for the
project palette and typography. It is consumed at build/sync time to inject
CSS custom properties into `ui/` sources and Qt colour values into theme
QSS files. The JSON Schema for `tokens.json` will live alongside it at
`branding/schemas/tokens.schema.json` (out of scope for SMO-0403; tracked
as a follow-up).

When a UI surface needs a new colour or font role, add the role to
`tokens.json` first and reference it by key name — do not hard-code hex
values in CSS or QSS. Hard-coded values in `ui/themes/shikshan-light/*.qss`
must include a code comment naming the source token key.

## Editing rules

- Wallpaper PNGs should be lossless or near-lossless (PNG-8 acceptable when
  palette permits). Do not commit JPEG masters.
- The logo SVG must declare `viewBox`, include a `<title>` element, and
  must not embed external font files or `<image href="...">` references
  to non-vendored URLs.
- Colour values in `tokens.json` must be in `#RRGGBB` (or `#RRGGBBAA`)
  form so they are usable by both CSS (web) and Qt (`QColor`).
- Greeter-specific files in `greeter/` must remain INI-parseable (slick-
  greeter consumes plain INI).
