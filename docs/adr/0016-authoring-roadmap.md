---
status: "proposed"
date: 2026-05-28
decision-makers: ["@shikshan/platform"]
consulted: []
informed: ["@shikshan/platform"]
---

# 0016 — Vidyarthi authoring track: CLI-first, Flutter Desktop deferred

## Context and Problem Statement

Vidyarthi modules must be authored by content creators — educators,
subject-matter experts, and community contributors who are not
necessarily on Debian or in the repo. There is also a future need to
let the backend review, co-sign, and publish community modules into the
official catalog without requiring those authors to understand the
Debian package build pipeline. The question is: what is the authoring
toolchain, and when is it built? Two anchoring constraints shape the
answer: (1) Vidyarthi v1 must focus on the SQL MVP engine — authoring
tooling that blocks on the engine surface would delay the OS product;
(2) the user has explicitly requested a Flutter Desktop app
(Windows + cross-platform) as the eventual authoring tool. This ADR
locks the phasing and the responsibility split, not the final tool UX.

## Decision Drivers

* Authoring tooling must not block or slow the SQL MVP (SMO-0560).
* The authoring tool must produce the same signed bundle format as
  `modules/core/*` so first-party and community modules share one path.
* The tool targets Windows primarily (educator workstations), with
  Linux/macOS support desirable.
* The OS-side signing and verification chain must remain authoritative
  regardless of what tool generated the bundle.
* A minimal local validation loop (scaffold, validate schema, dry-run
  in engine) must exist for OS developers to author test modules today.

## Considered Options

* **CLI-first (Phase-3 now) + Flutter Desktop app (Phase-6 separate
  repo)** — ship a `vidyarthi-modulectl` subcommand set for OS
  developers now; defer the GUI authoring tool to Phase-6.
* **Flutter Desktop app now** — build the Windows authoring app
  concurrently with the SQL engine.
* **Bundled web-SPA authoring UI** — embed an authoring SPA inside the
  Vidyarthi launcher (same WebKitGTK runtime, no new toolchain).
* **Headless CLI only, no GUI ever** — never build a GUI authoring
  tool; rely on text editors + the CLI.

## Decision Outcome

Chosen option: **"CLI-first now; Flutter Desktop authoring app as a
Phase-6 separate-repo deliverable"**, because it unblocks OS developers
today (module scaffolding, schema validation, signature verification)
while reserving the Windows-native GUI authoring experience for Phase-6
where it belongs — after the engine surfaces are stable enough to
drive a visual exercise builder.

### Phase-3 (now): `vidyarthi-modulectl` CLI subcommands

`vidyarthi-modulectl` (filed in SMO-0580) ships with the
`shikshan-vidyarthi` Debian package. For Phase-3, it provides:

* `vidyarthi-modulectl scaffold <module-id> --type interactive-runner
  --sub-engine sql` — creates a skeleton bundle directory with a
  conformant `manifest.yml`, stub exercise files, and a `fixtures/`
  directory.
* `vidyarthi-modulectl validate <path>` — validates manifest.yml and
  all exercise files against their JSON Schemas; exits 0 on pass.
* `vidyarthi-modulectl install <path>` — installs a local unsigned
  bundle into `~/.local/share/shikshan/modules/` for development use
  (bypasses cosign; only allowed when `policy.yml safety_mode: open`
  or `allowed_trust_levels` includes `experimental`).
* `vidyarthi-modulectl verify <path>` — verifies cosign signature and
  sha256 checksum against the catalog entry.

No bundle signing in Phase-3 — signing is the release workflow's job.

### Phase-6 (future): Flutter Desktop authoring app

A separate repository (`shikshan-vidyarthi-author` or similar) will
ship a Flutter Desktop application targeting Windows first, then
Linux/macOS. It:

* Presents a visual exercise builder per engine type (SQL query editor,
  quiz form, web sandbox, etc.).
* Generates the same `manifest.yml` + exercise YAML bundle format
  validated by the Phase-3 schemas (SMO-0511..0515).
* Exports a `.smo-module` archive (tar.zst of the bundle + a detached
  signature-request envelope).
* Submits to the backend catalog server (SMO-0510 registry, deferred
  to post-3-engines milestone) for human review, cosign signing, and
  publication.

The Flutter app is not installed on the OS image. Its binaries are
distributed separately (GitHub Releases, eventually a Windows installer).
The OS-side signing chain remains the authority — the Flutter app is a
convenience input tool.

### Backend publication flow (future, not v1)

```text
Author (Flutter app) → .smo-module upload
  → backend: schema validate + safety check
  → human reviewer approval
  → backend: cosign sign with catalog key
  → official/verified-community catalog entry published
  → OS clients download via vidyarthi-modulectl sync
```

This flow is documented here for future implementers; none of it is
built in Phase-3.

### Consequences

* **Good**, because the CLI ships in Phase-3 alongside the SQL engine
  — OS developers can author and test the 3 sample exercises
  (SMO-0560) without waiting for a GUI.
* **Good**, because the Flutter app is decoupled from the OS release
  cadence; it can ship months after the OS is in learners' hands.
* **Good**, because the bundle format is locked by Phase-3 schemas
  (SMO-0511..0515) — the Flutter app implements against a stable
  target.
* **Neutral**, because we accept a period where community authors
  must use the CLI (or just text editors) to create modules. This is
  acceptable while the learner base is small.
* **Bad**, because the Flutter Desktop app introduces Dart/Flutter as
  a second build toolchain in the wider project. This is explicitly
  chosen, not accidental — it targets Windows educators and the OS
  team does not own the authoring repo.

### Confirmation

Phase-3 compliance verified by:

* `tests/cli/test_modulectl.sh` (SMO-0580) — exercises `scaffold`,
  `validate`, and `install` against a fixture module.
* The same fixture module is used as `modules/core/sql-basics/`
  (SMO-0560) — the CLI must scaffold it and `validate` must pass.

Phase-6 scope is tracked as a separate planning item; this ADR is the
authoritative record of the decision to defer.

## Pros and Cons of the Options

### CLI-first + Flutter Desktop (Phase-6)

* **Good**, because OS development unblocked today; GUI deferred
  appropriately.
* **Good**, because Flutter is purpose-fit for Windows-native UI.
* **Bad**, because a gap period where community authors lack a GUI.

### Flutter Desktop app now

* **Good**, because native Windows UX from day one.
* **Bad**, because building the visual exercise builder requires the
  engine surfaces (SQL, web, code) to be stable — building it
  concurrently means constant churn as schemas evolve.
* **Bad**, because it adds Dart/Flutter to the Phase-3 critical path,
  compressing time on the SQL MVP.

### Bundled web-SPA authoring UI

* **Good**, because reuses the WebKitGTK runtime already in the
  launcher.
* **Bad**, because it would be OS-only; Windows educators would need to
  run a Linux VM or container — no real improvement over the CLI.
* **Bad**, because a SPA authoring UI inside the launcher is a large
  scope addition that competes with the SQL engine MVP for Phase-3
  resources.

### Headless CLI only

* **Good**, because zero extra scope.
* **Bad**, because community module authoring at scale requires a GUI;
  YAML by hand does not scale to non-technical educators.

## Supply-chain and audit implications

The Phase-3 `vidyarthi-modulectl` CLI is Python (already in our
toolchain) and ships in the `shikshan-vidyarthi` package. No new
supply-chain surface. The Phase-6 Flutter app lives in a separate repo
and has its own supply chain; its output (the bundle archive) is
verified by the OS-side cosign chain before any module enters the
catalog — the Flutter app cannot bypass OS trust gates.

## Rollback plan

If Phase-6 Flutter Desktop proves unmaintainable (e.g., Flutter Linux
API churn, Google abandons the desktop target), supersede ADR-0016 with
a replacement choosing the next best authoring channel. The CLI
(`vidyarthi-modulectl`) is not affected — it is the OS-side authoring
primitive and would remain regardless.

## More Information

* Related ADRs: 0011 (engine IPC), 0012 (frontend stack — authoring
  tool is separate from the learner-app frontend)
* Related tasks: SMO-0580 (vidyarthi-modulectl CLI implementation),
  SMO-0510..0515 (schemas the authoring tool must target), SMO-0560
  (SQL exercises authored via CLI scaffold)
* External references:
  * Flutter Desktop — https://flutter.dev/multi-platform/desktop
  * cosign — https://docs.sigstore.dev/cosign/overview/
