# plans/

Repo-tracked design rationale for multi-task initiatives. Plans sit *between* [PLAN.md](../PLAN.md) (broad product spec) and [tasks/](../tasks/) (formal C = (I, O, S, R, T, Φ, Ψ) contracts for one bounded change).

A plan is the higher-altitude design — the *why* and the *how at a sketch level* — that a sequence of `SMO-NNNN` task contracts implements.

## Lifecycle

```
plans/
├── README.md           # this file
├── active/             # plans driving open or in-progress tasks
│   └── <slug>.md
└── completed/          # plans whose linked tasks are all merged
    └── <slug>.md       # archived, treat as immutable
```

```
1. Maintainer drops plans/active/<slug>.md
        │
        ▼ files one or more tasks/open/SMO-NNNN.yml with linked_plan: plans/active/<slug>.md
   tasks/open/SMO-NNNN.yml … SMO-NNNN+k.yml
        │
        ▼ tasks are claimed, implemented, merged
   tasks/completed/SMO-NNNN.yml … SMO-NNNN+k.yml
        │
        ▼ when every ID in <slug>.md frontmatter `linked_tasks:` is in tasks/completed/
   git mv plans/active/<slug>.md plans/completed/<slug>.md  (status: completed)
```

`plans/active/` ends up empty when no initiative is in flight. The archive move is performed by [.claude/commands/auto-task.md](../.claude/commands/auto-task.md) step 5a after the last linked task closes.

## Plan file format

Filename: `<slug>.md`, kebab-case. No `SMO-NNNN` in the filename — a plan typically maps to a *range* of task IDs.

Frontmatter contract:

```markdown
---
slug: login-branding-batch              # must match filename stem
title: Login + branding batch (SMO-0401..0408)
status: active                          # active while in plans/active/, flip to completed on move
linked_adr: docs/adr/0009-...md         # optional
linked_tasks:                           # required, min 1; SMO-NNNN IDs this plan spawns
  - SMO-0401
  - SMO-0402
created: 2026-05-27                     # ISO date
---

## Context
Why this initiative exists. What problem it solves.

## Approach
The design at a higher altitude than any single task contract.
Sub-decisions, trade-offs ruled out, locked interfaces.

## Task breakdown
- SMO-0401 — short title — one-line scope
- SMO-0402 — short title — one-line scope (e.g., human-only, allowlist expansion)

## Verification
How "done" looks at the *plan* level (not the task level).
The integration outcome — e.g., "Vidyarthi v1.0 milestone-gate E2E test passes".
```

Tasks reference a plan via the optional `linked_plan:` field in [tasks/schema/task.schema.yml](../tasks/schema/task.schema.yml). Trivial fixes (typo, single-line config) need no plan — the field is optional.

## Editing rules

- `plans/active/**` — maintainer files plans; agents may file plans they propose, subject to the agent allowlist.
- `plans/completed/**` — treat as immutable archive (parallel to `tasks/completed/`). The move from `active/` is a content-preserving rename plus a `status:` flip in the frontmatter; no other content changes after archive.
- The planner subagent reads the `linked_plan:` file when it exists (see [.claude/agents/planner.md](../.claude/agents/planner.md) inputs).
