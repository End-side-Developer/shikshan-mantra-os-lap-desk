# branding/greeter/

LightDM `slick-greeter` configuration for Shikshan Mantra OS. Source for the
INI installed at `/etc/lightdm/slick-greeter.conf` by
[config/hooks/live/0031-greeter-theme.hook.chroot](../../config/hooks/live/0031-greeter-theme.hook.chroot).
See [ADR-0009](../../docs/adr/0009-login-branding-auth.md).

## Conf-file fields

The `[Greeter]` section of `slick-greeter.conf`:

| Key | Value | Notes |
|-----|-------|-------|
| `background` | `/usr/share/backgrounds/shikshan/default.png` | Produced by SMO-0404 sync. Fallback documented below. |
| `background-color` | `#0E4F88` | `tokens.json` → `greeter.background_color`. Used when image fails to load. |
| `logo` | `/usr/share/shikshan/branding/logo/shikshan-mantra.svg` | The SMO-0404 logo SVG. |
| `theme-name`, `icon-theme-name` | `Adwaita` | Conservative defaults that ship with Debian trixie. |
| `font-name` | `Noto Sans 11` | Matches `tokens.json` sans family. |
| `draw-user-backgrounds` | `false` | Do not let per-user backgrounds override branding. |
| `show-power`, `show-clock`, `show-quit` | `true` | Standard controls. |
| `show-keyboard` | `false` | On-screen keyboard hidden for v1 (laptop/desk target). |

Full slick-greeter key reference: https://github.com/linuxmint/slick-greeter.

## Path-fallback behaviour

If the background PNG or logo SVG is missing at boot (e.g., the SMO-0404
sync produced an empty branding tree), slick-greeter degrades cleanly:

1. **Background missing** → solid `background-color` (`#0E4F88`).
2. **Logo missing** → no logo shown; layout otherwise unchanged.

A broken sync doesn't break the login screen — it just renders plainly.

## Claimed-marker gating

Per ADR-0009, the live session keeps auto-login
([config/hooks/live/0030-autologin.hook.chroot](../../config/hooks/live/0030-autologin.hook.chroot)
writes `/etc/lightdm/lightdm.conf.d/50-shikshan-autologin.conf`). The
slick-greeter becomes the login surface only on **claimed** systems
(installed or admin-configured), signalled by `/var/lib/shikshan/claimed`.

Hook `0031-greeter-theme.hook.chroot` implements the gate:

1. Writes `/etc/lightdm/lightdm.conf.d/60-shikshan-greeter.conf` declaring
   `greeter-session=lightdm-slick-greeter` — only matters when LightDM
   actually shows a greeter.
2. Installs `/usr/local/bin/shikshan-claimed-gate`, an idempotent shell
   script that:
   - **Marker present** → moves `50-shikshan-autologin.conf` aside to
     `.50-shikshan-autologin.conf.disabled`, so LightDM shows the greeter.
   - **Marker absent** → restores the autologin conf if previously
     disabled.
3. Installs `/etc/systemd/system/lightdm.service.d/shikshan-claimed.conf`
   with `ExecStartPre=-/usr/local/bin/shikshan-claimed-gate`.

Hook 0031 does **not** edit or remove the `50-shikshan-autologin.conf`
produced by hook 0030; the gate only moves the file in place.

The marker itself is **not** written by this batch — Calamares (or a
follow-up admin-provisioning surface) sets it post-install. To force the
greeter manually during development: `sudo touch /var/lib/shikshan/claimed`
then `sudo systemctl restart lightdm`.
