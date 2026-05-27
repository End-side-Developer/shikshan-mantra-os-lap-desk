---
status: "proposed"
date: 2026-05-27
decision-makers: ["@shikshan/platform", "@shikshan/devex"]
consulted: ["@shikshan/security", "@shikshan/safety"]
informed: ["@shikshan/release-managers"]
---

# 0009 — Login surface, branding pipeline, and auth-backend contract

## Context and Problem Statement

Shikshan Mantra OS v1 currently boots straight into an auto-logged-in `student`
session (config/hooks/live/0030-autologin.hook.chroot) with no branded greeter,
no role concept, and no path for an institution-issued identity. The product
intent (PLAN.md and CLAUDE.md) calls for two login modes — a local `student`
account that works offline, and an institution-issued identity that authenticates
against a Shikshan-managed backend — plus a Shikshan-Mantra-themed visual
identity across the greeter, wallpaper, and logout surfaces. UI source files
are also currently stored under `config/includes.chroot/usr/share/shikshan/`,
which mixes editable design sources with the live-build packaging payload and
makes design iteration slow.

What is the locked design for: (1) the login surface (greeter choice, modes,
flow), (2) the branding-asset pipeline (where sources live, how they reach the
ISO), and (3) the auth-backend contract that the institution-login UI will
eventually call?

## Decision Drivers

* 2 GB RAM target — the greeter and any login UI must keep first-boot RSS
  inside the ADR-0007 ceiling.
* Live-session boot speed — the live ISO must still auto-login fast for the
  rescue/USB-stick use case; the greeter only takes over once a system is
  "claimed" (installed, persisted, or admin-configured).
* Offline-first — the local login mode MUST work with no network; the
  institution login is opt-in and clearly marked when the backend is
  unreachable.
* Phase-3 review surface — every change in this batch must fit the small-
  bounded fast-path (`R.max_diff_lines <= 300`, `R.max_files_changed <= 10`,
  no protected-path overlap) per CLAUDE.md, except the one-time policy
  expansion that adds `ui/**` and `branding/**` to the agent allowlist.
* Auditability — the auth-backend contract must be frozen as a versioned
  OpenAPI document before any client code is written, so the eventual
  implementation (and SMO-0299 hook repairs) has a stable target.
* Source-vs-payload separation — design assets (PNG, SVG, CSS, HTML)
  must be editable independent of live-build's packaging layout.

## Considered Options

For the three axes where there is a real choice:

* Greeter: `lightdm-slick-greeter` / `lightdm-webkit2-greeter` / SDDM /
  keep auto-login with a post-login welcome dialog.
* UI source layout: top-level `ui/` + `branding/` + sync script /
  single `ui/` with assets inside / stay under
  `config/includes.chroot/usr/share/shikshan/`.
* Institution-login surface placement: extra button in the greeter /
  post-login welcome dialog with a disabled "Coming Soon" stub /
  hidden until backend lands.

## Decision Outcome

Chosen options:

* **Greeter: `lightdm-slick-greeter`** — light (~5 MB), GTK-based, themable
  via `/etc/lightdm/slick-greeter.conf` (background, logo, theme/icon name,
  draw-user-backgrounds). Auto-login is **retained** for the live session;
  the greeter only takes over when `/var/lib/shikshan/claimed` exists
  (written by Calamares post-install or by the welcome dialog when a real
  password is set). Webkit2-greeter is rejected (~30 MB extra, WebKit on
  2 GB is sluggish). SDDM is rejected (would force dropping LightDM and
  invalidate the existing autologin hook).

* **UI source layout: top-level `ui/` + `branding/`**. `ui/` holds editable
  HTML/CSS/JS sources for the launcher, login welcome dialog, and themes.
  `branding/` holds raster/SVG asset masters, `tokens.json` (the canonical
  color palette + typography tokens), and the slick-greeter config. A new
  build script `scripts/build/sync-ui-to-iso.sh` rsyncs them into
  `config/includes.chroot/usr/share/shikshan/...` and into
  `config/includes.chroot/usr/share/backgrounds/shikshan/` before `lb build`
  runs; `scripts/build/build-iso.sh` invokes it as its first step.

* **Institution-login placement: post-login welcome dialog with disabled
  "Coming Soon" stub**. The greeter shows only the local-account login
  (which is the Phase-3 status quo, but now branded). After login, an
  autostart `.desktop` entry runs once per user (firstrun marker under
  `~/.config/shikshan/welcome-shown`) and presents a role-picker dialog
  with two buttons: **Local Student** (active) and **Institution Login**
  (rendered, disabled, tooltip "Coming Soon — see SMO-0299"). Greeter
  changes stay small; the welcome dialog is just an autostart entry that
  can be removed without touching LightDM's boot path.

* **Auth-backend contract: OpenAPI 3.1 at
  `docs/architecture/api/auth-v1.yaml`**. Endpoints frozen by this ADR:
  `POST /v1/auth/login`, `POST /v1/auth/refresh`, `POST /v1/auth/logout`.
  Roles: `student | teacher | admin | institution_admin`. Transport: TLS
  with a pinned CA cert path declared in `/etc/shikshan/auth.yml`. **No
  client implementation lands in this batch** — only the contract and the
  config-file schema. SMO-0299 (or a follow-up SMO-04xx) implements the
  client.

### Consequences

* **Good**, because separating `ui/` and `branding/` from
  `config/includes.chroot/` lets designers iterate on HTML/CSS/SVG without
  navigating the live-build packaging tree, and lets `lint-manifest` /
  `pre-commit` apply UI-specific linters (stylelint, prettier) only to
  `ui/**`.
* **Good**, because retaining auto-login for the live session preserves the
  USB-stick / rescue boot speed driver from ADR-0001.
* **Good**, because freezing the auth-backend OpenAPI surface now means the
  institution-login UI can be rendered (and visually reviewed) without
  blocking on the backend implementation.
* **Good**, because slick-greeter's config surface is a single `.conf` file,
  which makes the greeter theme grep-able and revertable.
* **Bad**, because `ui/**` and `branding/**` need to be added to
  `policies/agent-allowlist.yml allow:`; that file is in deny, so the
  expansion requires a one-time `allowlist-override + solo-maintainer-
  override` PR (SMO-0402) before agent tasks can scaffold the trees.
* **Bad**, because the welcome dialog runs as an autostart `.desktop` in
  user session context, so it cannot enforce login policy at the OS gate —
  for true OS-gate enforcement we would need a custom PAM module or a
  greeter-side webview (deferred).
* **Neutral**, because slick-greeter's customisation ceiling (no shader
  animations, no QML) is acceptable for v1; if a richer greeter becomes a
  requirement later, this ADR's rollback path is to switch to
  `webkit2-greeter` (HTML/CSS-driven) without changing the auth contract or
  the UI source layout.

### Confirmation

Compliance with this ADR will be confirmed by:

* `tests/build/test_sync_ui_to_iso.sh` (SMO-0404) — asserts that
  `scripts/build/build-iso.sh` invokes `sync-ui-to-iso.sh` before `lb build`
  and that the synced files land at the documented paths.
* `tests/build/test_greeter_config.sh` (SMO-0405) — asserts that
  `lightdm-slick-greeter` is present in
  `config/package-lists/desktop-lxqt.list.chroot`, that
  `/etc/lightdm/slick-greeter.conf` is installed by hook
  `0031-greeter-theme.hook.chroot`, and that auto-login remains in effect
  until `/var/lib/shikshan/claimed` exists.
* `tests/build/test_welcome_autostart.sh` (SMO-0406) — asserts that the
  `shikshan-welcome.desktop` autostart entry is present and that the
  Institution-login control renders as `disabled` in the welcome dialog
  HTML.
* `tests/policy/test_auth_config_schema.sh` (SMO-0407) — validates
  `config/includes.chroot/etc/shikshan/auth.yml` against
  `modules/catalogs/schemas/auth-config.schema.json` and asserts the
  OpenAPI document parses.
* `tests/build/test_lxqt_leave_theme.sh` (SMO-0408) — asserts the
  branded logout splash QSS is installed.

## Pros and Cons of the Options

### Greeter choice

* `lightdm-slick-greeter` (chosen) — **Good**, because it keeps LightDM (no
  display-manager swap), it is themable via a single `.conf` file, and it
  ships in Debian trixie. **Bad**, because it cannot host arbitrary HTML
  widgets, so the institution-login button cannot live in the greeter
  itself.
* `lightdm-webkit2-greeter` — **Good**, because the login screen is HTML/CSS
  and can host both modes natively. **Bad**, because the WebKit dependency
  adds ~30 MB and is slow on 2 GB devices; ADR-0007's RAM ceiling makes
  this unsuitable for v1.
* SDDM — **Good**, because QML allows rich animation. **Bad**, because it
  forces a display-manager swap (LightDM is currently in
  `desktop-lxqt.list.chroot`) and invalidates the existing autologin hook.

### UI source layout

* Top-level `ui/` + `branding/` (chosen) — **Good**, because design sources
  and packaging payload are cleanly separated; linters and pre-commit hooks
  can target `ui/**` without false positives from `config/includes.chroot/`.
  **Bad**, because one-time `policies/agent-allowlist.yml` expansion is
  needed.
* Single top-level `ui/` with assets inside — **Good**, because fewer
  top-level dirs. **Bad**, because raster masters (PNG) and source code
  share a directory, which is a pre-commit / linter mess.
* Stay under `config/includes.chroot/usr/share/shikshan/` — **Good**,
  because no allowlist change. **Bad**, because design iteration mixes
  with live-build packaging and the same path is both source and payload,
  which complicates diff review.

### Institution-login surface placement

* Welcome dialog with disabled stub (chosen) — **Good**, because the
  greeter stays minimal and the dialog is removable by deleting one
  `.desktop` file. **Bad**, because it runs in user-session context, not
  at the OS gate.
* Extra greeter button — **Good**, because OS-gate. **Bad**, because
  slick-greeter does not host arbitrary buttons; achieving this needs
  webkit2-greeter (rejected above).
* Hidden until backend lands — **Good**, because no stub UI. **Bad**,
  because users have no visible signal that institution login is a future
  feature, and the auth contract cannot be visually reviewed end-to-end.

## Supply-chain and audit implications

This ADR introduces no new upstream packages beyond `lightdm-slick-greeter`
(present in Debian trixie main; subject to ADR-0001's snapshot pin) and does
not change signing material. The auth-backend OpenAPI document is a
*specification*, not a deployable artifact; it will not invoke any network
step in the ISO build. `config/includes.chroot/etc/shikshan/auth.yml` is a
configuration file with safe-by-default values (`modes: [local]`, institution
endpoint blank) and is validated by `modules/catalogs/schemas/auth-config.
schema.json`. No change to `scripts/audit/append-entry.py`, the audit-row
schema, or the audit chain.

## Rollback plan

If this design proves wrong:

1. Revert the package-list addition of `lightdm-slick-greeter` in
   `config/package-lists/desktop-lxqt.list.chroot` (the default greeter
   falls back to `lightdm-gtk-greeter`).
2. Remove `config/hooks/live/0031-greeter-theme.hook.chroot` and
   `config/hooks/live/0050-welcome-firstrun.hook.chroot`; the existing
   `0030-autologin.hook.chroot` continues to drive auto-login unchanged.
3. Mark `docs/architecture/api/auth-v1.yaml` as `status: rejected` via a
   superseding ADR; the `auth.yml` config file may be left as a dormant
   safe-default.
4. The `ui/` and `branding/` top-level trees may be retained even on full
   rollback — they only ship when `scripts/build/sync-ui-to-iso.sh` runs,
   which is gated by `scripts/build/build-iso.sh`.

## More Information

* Related ADRs:
  * [ADR-0007 — Locked `lb config` flag set](0007-live-build-config-flags.md).
  * [ADR-0006 — Release artifact bundle layout](0006-release-artifact-layout.md).
* Related policies:
  * `policies/agent-allowlist.yml` — expanded by SMO-0402 to include
    `ui/**` and `branding/**`.
  * `policies/protected-paths.yml` — unchanged.
  * `policies/sensitive-change-labels.yml` — unchanged.
* Related tasks:
  * SMO-0401 — this ADR.
  * SMO-0402 — one-time allowlist expansion (human, solo-override).
  * SMO-0403 — scaffold `ui/` + `branding/` directory trees.
  * SMO-0404 — Shikshan logo SVG + sync script + build-iso wiring.
  * SMO-0405 — slick-greeter package + branded theme config.
  * SMO-0406 — welcome dialog with role picker + institution stub.
  * SMO-0407 — auth OpenAPI contract + `/etc/shikshan/auth.yml` schema.
  * SMO-0408 — branded LXQt logout splash.
* Out of scope:
  * Institution-login client implementation (PAM/NSS/webview) — tracked
    against SMO-0299 hook repairs.
  * Calamares-side role mapping during install — separate follow-up.
  * Wallpaper rotation, theme-switching UI — v1 ships single light theme.
* External references:
  * https://github.com/linuxmint/slick-greeter
  * https://wiki.debian.org/LightDM
  * https://specifications.freedesktop.org/autostart-spec/autostart-spec-latest.html
  * https://spec.openapis.org/oas/v3.1.0
