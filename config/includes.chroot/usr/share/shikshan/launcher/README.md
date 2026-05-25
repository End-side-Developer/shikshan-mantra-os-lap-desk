# /usr/share/shikshan/launcher/

The module launcher web app. Bundles into the ISO at `/usr/share/shikshan/launcher/` and is served at `http://localhost:8080/launcher/` by a small local web server (a systemd user unit installed via `config/includes.chroot/etc/systemd/user/shikshan-launcher.service`, to be added in a follow-up task).

## Responsibilities

- Resolve catalogs declared in `/etc/shikshan/policy.yml`
- Verify catalog and module signatures + checksums
- Apply `unlock_rules` against the SQLite progress store
- Filter by `age_band` and `language`
- Render Hindi + English UI; the launcher refuses to render any module whose manifest fails the Hi+En parity check on `title` and `description`

## Build status

v1 launcher is implemented incrementally:
- Phase 7 (this scaffold): placeholder index page that lists `Hello` in both languages
- Phase 8: catalog verifier
- Phase 9: progress store integration
- Phase 10: full module launching with sandboxed iframes

This README will track milestones as they land.

## Source layout (future tasks SMO-0020..0050)

```
launcher/
├── index.html
├── app.js
├── catalog-verifier.js
├── progress-client.js
├── ui/
│   ├── en/
│   └── hi/
└── tests/
```
