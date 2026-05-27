# ui/login/welcome/

Post-login welcome dialog rendered as a plain HTML page and opened in the
user's default browser by an autostart wrapper. See
[ADR-0009](../../../docs/adr/0009-login-branding-auth.md).

## Files

| File | Purpose |
|------|---------|
| `index.html` | Page markup. Two role buttons: Local Student (active) and Institution Login (disabled stub). |
| `styles.css` | Token-derived styling — colours mirror `branding/tokens.json`. |
| `welcome.js` | Click handlers. Local Student calls `window.close()`; Institution button stays `disabled`. |

## Firstrun marker

The dialog is shown once per user session, controlled by
`~/.config/shikshan/welcome-shown`. The marker is written by the wrapper
script `/usr/local/bin/shikshan-welcome` (installed by
[config/hooks/live/0050-welcome-firstrun.hook.chroot](../../../config/hooks/live/0050-welcome-firstrun.hook.chroot)),
not by `welcome.js`. The wrapper checks the marker on autostart, opens the
page with `xdg-open` if absent, and writes the marker immediately after.

Re-show the dialog during development:

```bash
rm -f ~/.config/shikshan/welcome-shown
/usr/local/bin/shikshan-welcome
```

## Manual preview

```bash
xdg-open /usr/share/shikshan/login/welcome/index.html
```

Opening the source HTML directly in a browser also works; the logo `<img>`
`src` is absolute so it renders broken on the host — expected during
development.

## Institution login stub

The Institution Login button stays in the DOM but is `disabled` with an
`aria-disabled="true"` and a `title=` tooltip pointing to SMO-0299. The
working implementation lands once the auth-backend client is in place
([docs/architecture/api/auth-v1.yaml](../../../docs/architecture/api/auth-v1.yaml),
landing in SMO-0407).
