# ui/themes/shikshan-light/

The default Shikshan Mantra OS light theme. Qt stylesheets (`.qss`) only;
GTK/icon theme tokens stay in `branding/tokens.json`.

## Files

| File | Purpose | Sync destination |
|------|---------|------------------|
| `lxqt-leave.qss` | Branded logout splash (SMO-0408) | `/usr/share/shikshan/themes/shikshan-light/lxqt-leave.qss` |

## QSS selector targets (lxqt-leave)

| Selector | What it styles |
|----------|----------------|
| `QDialog` | The dialog window itself — background, base font. |
| `QLabel` | The header / prompt text. |
| `QPushButton` | All action buttons (default surface look). |
| `QPushButton#logout` | The primary "Logout" action — filled blue, white text. |
| `QPushButton#reboot`, `#shutdown`, `#suspend`, `#cancel` | Secondary actions — default surface. |
| `QPushButton:hover`, `QPushButton:focus` | Border colour changes only. |

## Token mapping

Colour values are inlined in the QSS (Qt's stylesheet engine does not
consume external CSS variables). The source-of-truth lives in
[`branding/tokens.json`](../../../branding/tokens.json) — every hex value
in the QSS carries an end-of-line comment naming the token key, so a
search for `tokens.colors.primary` finds every consumer.

| Token | Used by |
|-------|---------|
| `background_light` | `QDialog` background |
| `text_primary` | `QDialog`, `QPushButton` default text |
| `primary` | `QLabel`, `QPushButton#logout`, hover border |
| `text_on_primary` | `QPushButton#logout` text |
| `surface` | `QPushButton` default background |
| `border_subtle` | `QPushButton` default border |
| `secondary` | `QPushButton` focus border |
| `radius_md` | `QPushButton` border-radius |

## Manual preview

Launch the lxqt-leave dialog on a test session to render this stylesheet:

```bash
lxqt-leave
```

If you edit colours in `tokens.json`, rebuild and re-sync (or update
the inline values here in lockstep).
