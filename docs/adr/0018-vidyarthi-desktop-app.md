---
status: "proposed"
date: 2026-06-04
decision-makers: ["@shikshan/platform", "@shikshan/governance"]
consulted: ["@shikshan/content"]
informed: ["@shikshan/security"]
---

# 0018 — Vidyarthi desktop app surface: GTK-free core, headless test runner, frontend-owned xAPI, local-only SQL MVP

## Context and Problem Statement

The Vidyarthi batch (SMO-0500..0590) shipped the *pieces* of the SQL practice engine but
never connected them into something a student can open and use. The engine
([engines/sql/main.py](../../config/includes.chroot/usr/share/shikshan/vidyarthi/engines/sql/main.py))
grades correctly over JSON-RPC, but the GTK frontend
([src/window.py](../../config/includes.chroot/usr/share/shikshan/vidyarthi/src/window.py))
was a catalog-title skeleton: it never opened an exercise, spawned the engine, or graded.
There was no desktop entry at all (no `.desktop`, no menu/desktop icon, no GUI launcher
binary), the official catalog was empty, and the modules were never installed into the image.

We need a real desktop app for the SQL module that works end-to-end on the 2 GB target — and,
critically, one we can **test without building an ISO or running GTK** on the Windows
maintainer workstation. How do we wire the frontend to the engine while keeping the grade
pipeline fast to test, and how is telemetry emitted given the engine returns no statements?

## Decision Drivers

* Honor the locked frontend stack ([ADR-0012](0012-frontend-stack.md): PyGObject + GTK4 +
  GtkSourceView5) and engine IPC ([ADR-0011](0011-engine-ipc.md): subprocess + JSON-RPC).
* A student must reach a graded exercise from a desktop/menu icon — the literal "app".
* The grade pipeline must be testable on Windows with only `python3 + sqlite3 + PyYAML` — no
  GTK, no bubblewrap, no ISO — so iteration is fast and CI is cheap.
* Telemetry must land somewhere: the SQL engine returns `xapi_statements: []` by contract
  ([ADR-0014](0014-xapi-telemetry.md)), so the emitter must live elsewhere.
* SQL practice must work fully offline (no dependency on the phase-1 backend, which only
  serves `/health`).

## Considered Options

* **A** — Put all logic in the GTK `window.py`; test only via a booted ISO / GUI automation.
* **B** — Factor a **GTK-free core** (catalog + engine client + session + xapi) that both the
  GTK window and a headless CLI runner drive; test the core on any host.
* **C** — Replace the GTK app with a terminal-only runner for the MVP (defer GUI).

## Decision Outcome

Chosen option: **"B — GTK-free core with a headless runner"**, because it makes the entire
grade pipeline testable off-device while still delivering the GTK app that ADR-0012 requires.
The GTK window becomes a thin view; the runner exercises the identical code path.

### Locked decisions

1. **GTK-free core.** All logic lives in `src/catalog.py`, `src/engine_client.py`,
   `src/session.py`, `src/xapi.py` — **zero `gi`/GTK imports**. These are importable and
   unit-testable on Windows. `src/window.py` (GTK) and `src/runner.py` (CLI) are both thin
   drivers over them.

2. **Engine client is a subprocess JSON-RPC client.** `EngineClient` speaks the
   [vidyarthi-engine-rpc](../architecture/vidyarthi-engine-rpc.md) protocol to the existing SQL
   engine. The bubblewrap sandbox ([ADR-0015](0015-sandbox-primitive.md)) is applied
   automatically on Linux when `bwrap` is present (namespace isolation; `VIDYARTHI_SANDBOX=0`
   opts out); the client direct-spawns otherwise so dev/test works on Windows. Seccomp is left
   to the engine host, not this client.

3. **Frontend owns xAPI.** Because the engine returns `xapi_statements: []`, `src/xapi.py`
   writes the `scored` statement to the local learner store on **Submit** (not Run). The store
   path honors `XDG_DATA_HOME`, defaulting to `~/.local/share/shikshan/learner.db`, with the
   schema already proven in the SMO-0590 E2E test.

4. **Exercise identity is the file stem.** The engine resolves
   `content/exercises/<stem>.yml` (e.g. `01-select`), which differs from the YAML `id:` field
   (e.g. `select-all`). The catalog/session layers key on the stem to avoid that footgun.

5. **Desktop surface.** A `vidyarthi` launcher wrapper (`/usr/local/bin/vidyarthi`), a
   freedesktop `.desktop` entry under `/usr/share/applications/`, and an `/etc/skel/Desktop/`
   copy so the icon appears on the student desktop. Branded icon in `branding/logo/`.

6. **Content is installed via the existing sync pattern.**
   [sync-ui-to-iso.sh](../../scripts/build/sync-ui-to-iso.sh) (run by `build-iso.sh` before
   `lb build`) stages `modules/core/` → `/usr/share/shikshan/modules/` and the official catalog
   → `/usr/share/shikshan/catalogs/`. `bubblewrap`, `libseccomp2`, and `python3-yaml` are added
   to the package list so the engine spawns and imports on the ISO. Catalog resolution is by id
   (`/usr/share/shikshan/modules/<id>/`), with a repo fallback for dev.

7. **Local-only.** The SQL MVP makes no backend call. The phase-1 backend
   ([ADR-0017](0017-content-backend-architecture.md)) is not contacted; an optional `/health`
   indicator is explicitly deferred.

### Layered test strategy (the "easy to test" requirement)

| Layer | Where | What runs |
|-------|-------|-----------|
| L1 unit | Windows | `pytest tests/unit/vidyarthi/` — core modules + real engine subprocess |
| L2 headless | Windows | `runner.py … --submit` — GUI-equivalent grade + xAPI, no GTK |
| L3 GUI smoke | OS VM `.10` | `vidyarthi` under LXQt; click through an exercise |
| L4 ISO E2E | OS VM `.10` | `tests/e2e/test_vidyarthi_sql_mvp.sh` after `build-iso.sh` |

### Consequences

* **Good** — the grade pipeline (engine included) is testable on the dev box in <1 s; the GUI
  is a thin, low-risk view.
* **Good** — telemetry has a single, tested owner; Run vs Submit cleanly separates "try" from
  "record".
* **Good** — content install reuses the audited `sync-ui-to-iso.sh` mechanism; nothing new in
  the build pipeline.
* **Bad** — the GTK window itself still can only be smoke-tested on Linux (L3/L4); Windows
  covers everything *below* the view.
* **Neutral** — the GTK-free core duplicates a little path-resolution logic that the engine
  also has; acceptable for the testability win.

### Deferred (explicitly out of scope)

* WebKitGTK / sqlite-wasm runtime (the engine uses system `sqlite3` today).
* Quiz/code/web/ctf engines; cosign verification in `modulectl`.
* Backend sync / auth; online indicator; i18n `.po` catalogs; authoring tool
  ([ADR-0016](0016-authoring-roadmap.md)).

### Confirmation

* `pytest tests/unit/vidyarthi/` and `bash tests/integration/test_headless_runner.sh` are green
  on the Windows dev box (engine subprocess, session orchestration, xAPI write).
* `bash tests/e2e/test_vidyarthi_sql_mvp.sh` (extended in SMO-0616) gates the desktop entry,
  catalog registration, and the headless round-trip on the OS VM.
* `python scripts/audit/verify-chain.py --db docs/audit/audit.db` continues to pass.
* CODEOWNERS routes `/docs/adr/` to `@shikshan/governance`.

## More Information

* Related ADRs: [0011](0011-engine-ipc.md), [0012](0012-frontend-stack.md),
  [0014](0014-xapi-telemetry.md), [0015](0015-sandbox-primitive.md),
  [0017](0017-content-backend-architecture.md).
* Related architecture: [vidyarthi-engine-rpc.md](../architecture/vidyarthi-engine-rpc.md),
  [vidyarthi-xapi-subset.md](../architecture/vidyarthi-xapi-subset.md).
* Related runbook: [vidyarthi-sql-desktop-smoke.md](../runbooks/vidyarthi-sql-desktop-smoke.md).
* MADR 3.x — https://adr.github.io/madr/
