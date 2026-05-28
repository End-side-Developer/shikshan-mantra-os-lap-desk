---
status: "proposed"
date: 2026-05-28
decision-makers: ["@shikshan/platform"]
consulted: []
informed: ["@shikshan/platform"]
---

# 0014 — Vidyarthi telemetry format: xAPI statements

## Context and Problem Statement

Every Vidyarthi engine subprocess returns graded results (ADR-0011 —
`grade` RPC response). Those results must be persisted so the launcher
can show per-learner progress, and so the OS can eventually integrate
with external LMS/LRS systems (school networks, teacher dashboards).
We need to lock the *shape* of the persisted telemetry record: what
fields are mandatory, how is the learner identified, and what does
the wire format look like? The shape must be stable enough to survive
the addition of future engine types (SMO-0511..0515 schemas) without
a migration, but cannot require a network stack or a running LRS
server — this is an offline-first OS on 2 GB RAM.

## Decision Drivers

* Must work fully offline (no LRS endpoint required at runtime).
* Must be extensible across engine types (SQL, web, code, CTF, quiz)
  without changing the storage schema.
* Must not embed PII — learner identity is an anonymous UUID scoped
  to the local device.
* Must be hashable into the existing audit chain
  (`scripts/audit/append-entry.py`) without changing its format.
* Ideally interoperable with standard LMS/LRS tooling for future
  school-network deployments.

## Considered Options

* **xAPI (Tin Can API) statements**, stored locally in SQLite,
  hashed into the audit chain at session close.
* **SCORM 1.2 / 2004 CMI data model** — a property-bag
  (`cmi.core.score.raw`, `cmi.core.lesson_status`, …) wrapped in
  a JavaScript postMessage round-trip.
* **Custom Shikshan progress JSON** — a purpose-built flat record
  with fields chosen for Vidyarthi's exact needs.
* **H5P xAPI runtime** — reuse H5P's built-in xAPI emission wired
  into a local LRS stub.

## Decision Outcome

Chosen option: **"xAPI statements stored locally in SQLite"**, because
xAPI is the lingua franca for `learner X did Y on Z with result R`,
carries no network requirement, and its statement shape is extensible
to new verbs and activity types without a schema migration.

### Mandatory xAPI statement subset

Every engine's `grade` RPC response MUST include an array of xAPI
statement objects with at least these fields populated:

```json
actor:   { objectType: "Agent",
           account: { homePage: "urn:shikshan:device",
                      name: "<device-scoped-uuid>" } }

verb:    one of:
           { id: "http://adlnet.gov/expapi/verbs/attempted" }
           { id: "http://adlnet.gov/expapi/verbs/completed" }
           { id: "http://adlnet.gov/expapi/verbs/scored" }

object:  { objectType: "Activity",
           id: "urn:shikshan:module:<module-id>:exercise:<exercise-id>",
           definition: { type: "http://adlnet.gov/expapi/activities/assessment" } }

result:  { score:   { scaled: 0.0–1.0, raw: 0–100 },
           success: true | false,
           response: "<learner-submitted-text, max 4 KB>" }

context: { platform: "Shikshan Mantra OS",
           language: "en" | "hi",
           extensions: {
             "urn:shikshan:sub_engine": "<sql|web|code|ctf|quiz>",
             "urn:shikshan:engine_version": "<semver>"
           } }

timestamp: ISO 8601 UTC
```

Fields not in this subset MAY be added by individual engines via
`context.extensions`; they are stored as-is and ignored by the
progress UI until a future ADR defines their meaning.

### Storage

Statements are written to
`~/.local/share/shikshan/vidyarthi/learner.db` (SQLite). Schema:

```sql
CREATE TABLE IF NOT EXISTS xapi_statements (
    id         TEXT PRIMARY KEY,   -- statement UUID (v4)
    stored_at  TEXT NOT NULL,       -- ISO 8601 UTC wall clock
    statement  TEXT NOT NULL        -- JSON blob (full xAPI statement)
);
```

The table is append-only. The launcher MUST NOT UPDATE or DELETE rows.

### Audit-chain anchoring

At the end of each exercise session the launcher calls
`scripts/audit/append-entry.py` with:

```yaml
action:   "xapi-session-close"
subject:  "<module-id>/<exercise-id>"
detail:   "sha256:<sha256-of-all-statement-UUIDs-in-session>"
```

This anchors the session into the existing hash-chained audit log
without embedding the full statement payloads in the audit DB.

### Consequences

* **Good**, because xAPI's statement model covers all current and
  planned engine types with no field additions — future verb IDs can
  be added without a SQLite schema migration.
* **Good**, because the actor uses an anonymous device-scoped UUID;
  no name, email, or institutional ID is stored unless the school
  admin explicitly configures `institution` mode (see
  `auth-config.schema.json`).
* **Good**, because any school operating an LRS (SCORM Cloud, ADL LRS,
  Learning Locker) can eventually consume the learner.db export via
  the xAPI batch-submit path — zero glue code needed on our side.
* **Neutral**, because we are using only a small subset of xAPI;
  statements are not validated against the full xAPI spec at runtime
  (too heavy for offline-first); a future `vidyarthi-modulectl
  validate-statements` subcommand may add that.
* **Bad**, because SQLite gives us no built-in replication; if the
  learner.db is corrupted or deleted, progress is lost. Mitigation:
  periodic backup to `/var/backup/shikshan/` is a future task.

### Confirmation

Compliance is verified by:

* `tests/engines/test_sql_engine.py` (SMO-0560) — asserts that the
  SQL engine's `grade` response contains a valid xAPI statement array
  matching the mandatory subset above.
* `docs/architecture/vidyarthi-xapi-subset.md` (SMO-0531) — the
  normative spec document; a passing `markdownlint` run on that file
  is the gate.

## Pros and Cons of the Options

### xAPI statements in local SQLite

* **Good**, because extensible, lingua franca, no network required.
* **Bad**, because subset definition requires discipline to keep
  consistent across engine authors.

### SCORM 1.2 / 2004 CMI data model

* **Good**, because very widely supported.
* **Bad**, because CMI is tied to a JavaScript runtime inside an HTML
  SCO; our engines are not HTML documents — they are subprocess
  binaries communicating via JSON-RPC stdio (ADR-0011).
* **Bad**, because SCORM requires a runtime host (an LMS or a local
  SCORM player); we would have to embed one.

### Custom Shikshan progress JSON

* **Good**, because exactly the fields we need, nothing more.
* **Bad**, because zero ecosystem interoperability; any future
  school-network integration requires a custom ETL.

### H5P xAPI runtime

* **Good**, because H5P already emits xAPI statements.
* **Bad**, because H5P content types do not cover live SQL/code
  execution (no custom runners); we would need H5P only for the
  statement emission plumbing, then bypass it for all engine logic.

## Supply-chain and audit implications

SQLite is in Debian main (`libsqlite3-0`, `python3-sqlite3`). The
`learner.db` is user-owned data — it is never committed to the repo
and is not in any signing chain. Anchoring via
`scripts/audit/append-entry.py` reuses the existing audit chain
without any format change to `docs/audit/audit.db`.

## Rollback plan

If xAPI proves wrong (e.g., the statement shape changes incompatibly
across engines, or school-network LRS requirements demand a different
format), supersede ADR-0014 with a new ADR. The migration path is:
export learner.db to the new format in a one-time script, remove the
xAPI statement array from the engine `grade` RPC response (semver-bump
the engine protocol), update SMO-0531 spec and all engine tests.

## More Information

* Related ADRs: 0011 (grade RPC carries statements), 0013 (disjoint
  from Kolibri telemetry), 0015 (sandbox does not interfere with
  statement write path — statements are returned via JSON-RPC stdout,
  not file writes from inside the sandbox)
* Related tasks: SMO-0530 (engine RPC spec), SMO-0531 (xAPI subset
  spec), SMO-0560 (SQL engine emits statements)
* External references:
  * xAPI spec — https://adlnet.gov/projects/xapi/
  * xAPI verbs registry — https://registry.tincanapi.com/
