# modules/catalogs/schemas/exercises/

Per-sub-engine exercise specification schemas for Vidyarthi
`interactive-runner` modules (ADR-0011, SMO-0510).

## Schema files

| File | Sub-engine | Landed in |
|---|---|---|
| `sql.schema.json` | `sql` | SMO-0511 |
| `quiz.schema.json` | `quiz` | SMO-0512 |
| `code.schema.json` | `code` | SMO-0513 |
| `web.schema.json` | `web` | SMO-0514 |
| `ctf.schema.json` | `ctf` | SMO-0515 |

## When is validation applied?

`vidyarthi-modulectl validate <path>` checks each exercise file
listed in the module bundle against the schema for its `sub_engine`.
The pre-commit `manifest-validate` hook runs the same check on
`modules/core/**` during development.

The module-level `exercise_spec` field in `module.schema.json` is
typed as a freeform object (to keep the parent schema engine-agnostic);
the per-engine schemas here are the normative constraints.
