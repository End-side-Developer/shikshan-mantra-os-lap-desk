---
status: "proposed"
date: 2026-05-28
decision-makers: ["@shikshan/platform"]
consulted: []
informed: ["@shikshan/platform"]
---

# 0013 — Kolibri relationship: sibling app, not host

## Context and Problem Statement

Kolibri is already installed on Shikshan Mantra OS (it is in
`config/package-lists/edu-kolibri.list.chroot`) and ships with the
default desktop. Vidyarthi (ADR-0011, ADR-0012) is a *new* learner-
facing app that overlaps with Kolibri in obvious ways — it shows
content, tracks progress, organises material into topics. A learner
sitting in front of the desktop will see both icons and must know
which to launch when. We need to lock the relationship between the
two so that builder agents, content authors, and learners share a
single mental model and so that the engineering split is unambiguous.
See [PLAN.md](../../PLAN.md) and the `project_vidyarthi_initiative`
memory entry.

## Decision Drivers

* Learner clarity: each app must have a one-line job description.
* Independent release cadence: Vidyarthi must not block on Kolibri
  upstream releases, and vice versa.
* Per-content-type policy gating (ADR-0011 / ADR-0015) must remain
  feasible — Kolibri's channel-import model does not gate by content
  type.
* Reuse where it does not cost us — students and authors who already
  know Kolibri vocabulary should not learn two ontologies.

## Considered Options

* **Sibling apps with shared vocabulary, disjoint storage**
  (chosen).
* **Vidyarthi as a Kolibri plugin** — Vidyarthi loads inside the
  Kolibri server process and renders via Kolibri's KOLIBRI plugin
  contract.
* **Vidyarthi modules served from Kolibri channels** — Vidyarthi
  becomes a content type inside a Kolibri channel; modules ship through
  Kolibri Studio / ricecooker.
* **Vidyarthi replaces Kolibri** — single learner app, retire
  Kolibri.

## Decision Outcome

Chosen option: **"Sibling apps with shared vocabulary, disjoint
storage"**, because it preserves Kolibri's strengths (library and
curated channels) while letting Vidyarthi own the interactive-runner
surface with its own policy gating, sandbox, and release cadence.

### Shared vocabulary

Vidyarthi reuses the following ContentNode taxonomy terms from Kolibri
so that authors and learners do not learn two ontologies:

* **topic** — a folder of content (Kolibri term: `topic`)
* **exercise** — a graded activity (Kolibri term: `exercise`)
* **video** — a video resource
* **document** — a PDF/HTML resource

Vidyarthi's `interactive-runner` content type (SMO-0510) is a
specialisation of `exercise` — it carries the same outcomes-and-mastery
notion but runs in a Vidyarthi engine subprocess rather than a Kolibri
Perseus widget.

### Disjoint storage

Storage paths are disjoint:

* Kolibri user data: `~/.kolibri/`
* Kolibri channel cache: `/var/lib/kolibri/content/`
* Vidyarthi system modules: `/usr/share/shikshan/modules/`
* Vidyarthi user modules: `~/.local/share/shikshan/modules/`
* Vidyarthi telemetry: `~/.local/share/shikshan/vidyarthi/learner.db`
  (ADR-0014)

Neither app reads or writes the other's directories. Module signing
(catalogs, cosign) is Vidyarthi-specific; Kolibri channel signing is
Kolibri-specific.

### URI scheme handshake

The two apps may cross-link from list views and welcome dialogs:

* `kolibri://channel/<channel-id>/node/<node-id>` — opens Kolibri to
  the named resource.
* `vidyarthi://module/<module-id>/exercise/<exercise-id>` — opens
  Vidyarthi to the named exercise.

Full URI grammar is deferred to a follow-up doc once both apps have a
landed entrypoint; this ADR only reserves the schemes and confirms
that handshake is one-way (launch the other app) and does not share
process state.

### Consequences

* **Good**, because Vidyarthi releases on its own schedule; Kolibri
  upstream version bumps do not gate Vidyarthi.
* **Good**, because Vidyarthi avoids depending on Kolibri's Python
  runtime version, web server, or plugin contract — none of those
  are stable APIs from our perspective.
* **Good**, because content-type policy gating (`safety_mode` per
  ADR-0015 + the policy.yml gates from SMO-0520) only has to apply
  to Vidyarthi's surface; Kolibri's existing safety story is
  untouched.
* **Neutral**, because we accept duplicate ContentNode-style walkers
  in two codebases (Kolibri's Python, Vidyarthi's Python). The
  duplication is small (taxonomy is < 10 fields) and keeps the two
  apps decoupled.
* **Bad**, because two icons on the desktop need clear labelling.
  Mitigation: the LXQt menu groups them as "Library: Kolibri" and
  "Practice: Vidyarthi"; the first-run welcome dialog (SMO-0406
  artefact) introduces both with a one-line job description.

### Confirmation

Compliance is verified by:

* `tests/integration/test_kolibri_vidyarthi_disjoint.sh` (placeholder
  — filed in a follow-up SMO when Vidyarthi has its own entrypoint;
  the test will assert that neither app writes inside the other's
  storage paths during a 5-minute exercise session).
* Manual reviewer step: any PR touching both
  `config/package-lists/edu-kolibri.list.chroot` and
  `config/package-lists/vidyarthi.list.chroot` must reference this
  ADR.

## Pros and Cons of the Options

### Sibling apps with shared vocabulary, disjoint storage

* **Good**, because release cadences are independent.
* **Good**, because shared vocabulary keeps authors fluent in one
  ontology.
* **Bad**, because two icons require clear labelling.

### Vidyarthi as a Kolibri plugin

* **Good**, because single binary to install and update.
* **Bad**, because Kolibri's plugin model is web-first; spawning
  native subprocess engines per exercise (ADR-0011) does not compose
  cleanly with Kolibri's Django/Tornado serving model.
* **Bad**, because Vidyarthi releases would be gated on Kolibri's
  upstream API stability — Kolibri does not commit to a stable
  plugin contract.

### Vidyarthi modules served from Kolibri channels

* **Good**, because we'd inherit Kolibri's channel discovery and
  import UI.
* **Bad**, because content-type policy gating becomes impossible
  (Kolibri channels carry any content type by design); the
  `safety_mode` story collapses.
* **Bad**, because we'd be authoring our exercises in Kolibri Studio
  / ricecooker — a heavy and Perseus-shaped toolchain that has no SQL
  or live-coding widgets.

### Vidyarthi replaces Kolibri

* **Good**, because single learner app, single brand.
* **Bad**, because Kolibri's curated library and offline channel
  ecosystem are real strengths we have no resourcing to replicate;
  removing Kolibri would be a regression for learners on day one.

## Supply-chain and audit implications

None — the two apps remain on independent supply chains. Kolibri
ships from Debian main; Vidyarthi will ship from
`shikshan-vidyarthi` (SMO-0540 stub). Audit-row format is
unaffected.

## Rollback plan

If this decision proves wrong (e.g., learners conflate the two apps
and the labelling does not solve it, or Vidyarthi ends up
reimplementing too much of Kolibri's library), supersede ADR-0013
with a replacement ADR specifying the new relationship. A real merge
or full split would be a multi-quarter migration — the ADR
supersession is the cheap part; the engineering work is not. Until
then, the URI scheme reservation here is binding.

## More Information

* Related ADRs: 0011 (engine IPC), 0012 (frontend stack), 0014
  (xAPI telemetry — uses its own learner.db, disjoint from Kolibri's)
* Related tasks: SMO-0510 (schema content-type carries the shared
  taxonomy subset), SMO-0550 (Vidyarthi launcher introduces the
  vidyarthi:// URI handler)
* External references:
  * Kolibri Perseus exercise plugin —
    https://github.com/learningequality/kolibri-exercise-perseus-plugin
  * Kolibri content types —
    https://www.mintlify.com/learningequality/studio/concepts/content-types
