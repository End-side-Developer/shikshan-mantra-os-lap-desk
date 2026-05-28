---
status: "proposed"
date: 2026-05-28
decision-makers: ["@shikshan/platform"]
consulted: []
informed: ["@shikshan/platform"]
---

# 0012 — Vidyarthi frontend stack: PyGObject + libadwaita + GtkSourceView

## Context and Problem Statement

ADR-0011 locked the engine IPC at subprocess + JSON-RPC over stdio. The
frontend that drives those engines — catalog browser, exercise pane, editor,
result view — still needs a stack. The choice is urgent because SMO-0550
(the Meson + hello-world launcher skeleton) is blocked on it: every later
engine task spawns from the same frontend, so the language and widget toolkit
must be locked first. The constraints are the project-wide ones: 2 GB RAM
target, reproducible builds against snapshot.debian.org, no proprietary
toolchains, bilingual (en/hi) text rendering, accessible by default. See
[PLAN.md](../../PLAN.md) and the `project_vidyarthi_initiative` memory entry.

## Decision Drivers

* Must fit the 2 GB RAM target with comfortable headroom (idle launcher
  < 80 MB RSS).
* Must be reproducibly buildable from snapshot.debian.org — no curl-piped
  toolchain installs.
* Must render Hindi (Devanagari) text correctly out of the box.
* Must be readable and editable by future student-contributors.
* Must give us a syntax-aware code editor without writing one.

## Considered Options

* **PyGObject + GTK 4 + libadwaita + GtkSourceView 5** (with Blueprint UI
  markup + Meson build).
* **gtk4-rs** (Rust bindings to GTK 4 + libadwaita).
* **Vala** (compiles to C, native GObject).
* **Electron** or **Tauri** (web stack in a Chromium/WebView shell).
* **Flutter Desktop** (Linux).
* **PyQt6** / **PySide6** (Qt 6 Python bindings).

## Decision Outcome

Chosen option: **"PyGObject + GTK 4 + libadwaita + GtkSourceView 5"**, because
it is the lowest-friction stack for a solo-maintainer Python-heavy repo, it
ships entirely from Debian main, and GtkSourceView gives us a syntax-aware
editor for SQL/Python/web with zero custom code.

### Locked dependency set

The `shikshan-vidyarthi` Debian package (stub in SMO-0540) depends on:

* `python3` (>= 3.11)
* `python3-gi`
* `gir1.2-gtk-4.0`
* `gir1.2-adw-1`
* `gir1.2-gtksourceview-5`
* `gir1.2-webkit-6.0` (engine host iframe for sql.js and DOM grading; only
  loaded inside engine subprocesses, never in the launcher chrome)
* `libadwaita-1-0`
* `libgtk-4-1`
* `libgtksourceview-5-0`

Build-time only:

* `meson`
* `blueprint-compiler` (compiles `.blp` → `.ui` at build time so we keep
  XML out of source control)

### Launcher path

A POSIX shell wrapper at `/usr/bin/vidyarthi` executes
`python3 /usr/share/shikshan/vidyarthi/src/main.py "$@"`. The wrapper is
shipped by `shikshan-vidyarthi` and is the single entry point referenced
from the LXQt menu, the launcher desktop icon, and the welcome dialog.

### Consequences

* **Good**, because idle RSS measured against an empty PyGObject +
  libadwaita window is ~55–70 MB on Debian trixie — comfortable headroom
  inside the 2 GB target.
* **Good**, because every dependency is in Debian main and pinned by
  snapshot.debian.org via [docs/adr/0007-live-build-config-flags.md](0007-live-build-config-flags.md);
  no third-party apt source, no language version manager, no Rust
  toolchain bootstrap.
* **Good**, because libadwaita ships HC-themable widgets, screen-reader
  support, and Devanagari rendering through Pango/HarfBuzz at zero extra
  cost — accessibility and bilingual surface are inherited.
* **Good**, because Python tracebacks land on stderr and are immediately
  legible to a student-contributor; GObject-Introspection means the same
  API the C docs describe is what we call from Python.
* **Neutral**, because Python startup (~150–250 ms cold) is slower than
  a compiled binary; acceptable for a launcher that opens once per
  session and stays resident.
* **Bad**, because we accept a GIL constraint on the launcher process;
  engines run as separate subprocesses (ADR-0011) so this only bites if
  the launcher ever needs CPU-bound work in its main loop, which the
  design avoids.

### Confirmation

Compliance is verified by:

* `tests/build/test_vidyarthi_skeleton.sh` (filed in SMO-0550) — asserts
  the launcher imports `gi.repository.{Gtk,Adw,GtkSource}` without error,
  the `.blp` files compile, and Meson installs to the expected paths.
* The standing iso-build smoke test — the ISO must boot, the Vidyarthi
  menu entry must launch, and the catalog browser must render.

## Pros and Cons of the Options

### PyGObject + GTK 4 + libadwaita + GtkSourceView 5

* **Good**, because every part ships from Debian main.
* **Good**, because GtkSourceView 5 is the canonical Linux source-editor
  widget (also used by GNOME Builder, gedit's successor `gnome-text-editor`).
* **Bad**, because Python startup latency.

### gtk4-rs (Rust)

* **Good**, because compiled binary, no GIL, very small RAM footprint.
* **Bad**, because Rust toolchain is not on the live-build snapshot.debian.org
  pin in a stable form for Vidyarthi's release cadence; bootstrapping
  cargo-vendor into the live-build flow adds review surface and supply-chain
  complexity.
* **Bad**, because the team velocity is Python-first (audit scripts,
  vendor-sync, tests are all Python); adding Rust splits maintainer
  attention.

### Vala

* **Good**, because compiles to C, very fast, native GObject feel.
* **Bad**, because community is small and shrinking; fewer educational
  examples for student-contributors to learn from; harder to hire/onboard.

### Electron / Tauri

* **Good**, because reuses web skills.
* **Bad**, because Electron resident set is 100+ MB per window —
  incompatible with 2 GB target.
* **Bad**, because we'd own Chromium's security surface on a child-targeted
  OS.

### Flutter Desktop

* Deferred to the authoring track (ADR-0016). Flutter Desktop is being
  reserved for the cross-platform module-authoring application; using
  it for the on-OS learner app would force the Dart runtime into the
  live system for no net win over GTK + Python.

### PyQt6 / PySide6

* **Good**, because mature Python bindings to Qt 6.
* **Bad**, because LGPL boundary on PyQt's commercial license adds
  legal review surface; PySide6 is LGPL-clean but lacks libadwaita's
  adaptive widgets and Indic script rendering parity.
* **Bad**, because LXQt already pulls in Qt 5 — adding Qt 6 doubles the
  Qt footprint on the live system.

## Supply-chain and audit implications

All dependencies are in Debian main and pulled via the snapshot.debian.org
pin from ADR-0007 (`config/archives/debian.list.chroot`). No new apt
sources, no curl-piped installers, no language-managed package wheels.
`blueprint-compiler` runs at build time only; its output (`.ui` XML) is
not committed — it is regenerated during the Debian package build, which
will be reproducible by ADR-0007's flag set.

## Rollback plan

If this decision proves wrong (e.g., Python startup latency on real
2 GB hardware is intolerable, or libadwaita's API churn breaks Debian
trixie support), supersede ADR-0012 with a replacement ADR naming the
new stack (most likely gtk4-rs once Rust is in the snapshot pin, or
Vala if we accept the contributor-pool risk). Revert sequence: remove
`config/package-lists/vidyarthi.list.chroot`, delete
`config/includes.chroot/usr/share/shikshan/vidyarthi/`, regenerate
SMO-0550 against the new stack.

## More Information

* Related ADRs: 0007 (live-build flags), 0011 (engine IPC), 0015
  (sandbox), 0016 (authoring roadmap)
* Related tasks: SMO-0540 (debian/control stubs), SMO-0550 (Meson +
  PyGObject skeleton), SMO-0560 (SQL engine uses GtkSourceView), SMO-0590
  (e2e smoke)
* External references:
  * PyGObject — https://pygobject.gnome.org/
  * libadwaita — https://gnome.pages.gitlab.gnome.org/libadwaita/
  * GtkSourceView — https://gnome.pages.gitlab.gnome.org/gtksourceview/gtksourceview5/
  * Blueprint — https://jwestman.pages.gitlab.gnome.org/blueprint-compiler/
