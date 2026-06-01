---
slug: plans-folder-bootstrap
title: Bootstrap the plans/ folder lifecycle (SMO-0600)
status: completed
linked_tasks:
  - SMO-0600
created: 2026-06-01
---

## Context

The repo had no design-rationale layer between [PLAN.md](../../PLAN.md) (broad product spec) and `tasks/open/SMO-NNNN.yml` (formal one-change contracts). Multi-task initiatives like the Vidyarthi SMO-0500..0590 batch and the login/branding SMO-0401..0408 batch lived in external harness plan files (`~/.claude/plans/*.md`), invisible to CI, contributors, and the planner subagent that should be reading them.

This plan bootstraps a repo-tracked `plans/` folder so future multi-task initiatives have an in-repo anchor doc that the planner and builder consume.

## Approach

- `plans/active/` holds plans driving open or in-progress tasks; `plans/completed/` is the archive (parallel to `tasks/completed/`).
- A plan is a markdown file with frontmatter declaring `slug`, `status`, and `linked_tasks: [SMO-NNNN, ...]`. Filename is `<slug>.md` — no SMO ID, because a plan typically spans a range.
- The task schema gains an optional `linked_plan:` field. Trivial fixes need no plan. No `linked_plan` requirement is enforced for any task type — strict mode deferred per the user's Phase-3 stance.
- `/task-claim` reads the linked plan before deciding planner-vs-skip (context, not a planner trigger).
- `/auto-task` archives a plan from `plans/active/` to `plans/completed/` after its last linked task closes (frontmatter `status:` flipped in the same move commit).

Locked interfaces:
- `linked_plan` regex: `^plans/(active|completed)/[a-z0-9-]+\.md$`
- Frontmatter required keys: `slug`, `status`, `linked_tasks`
- Plan archive trigger: every ID in `linked_tasks` present in `tasks/completed/`

## Task breakdown

- **SMO-0600** — Add `plans/` folder, README, schema field, agent-allowlist entry, planner+task-claim+auto-task wiring, tasks/README cross-link

Single task — the whole change is small, bounded (≤300 diff lines, ≤10 files), and self-contained. Subsequent multi-task plans will spawn N tasks; this bootstrap is the one exception that lives 1:1 with its task.

## Verification

Plan is "done" when:
1. `plans/active/plans-folder-bootstrap.md` archives itself to `plans/completed/plans-folder-bootstrap.md` as a smoke-test of the lifecycle (the auto-task step 5a should fire because SMO-0600 is the only linked task and it just closed).
2. A second test plan with two linked tasks (one open, one completed) demonstrates the plan stays in `active/` until *both* are closed — left as a future verification when a real multi-task plan lands.
