---
description: Claim a task from tasks/open/, move it to tasks/in-progress/, create the branch, and start the planner subagent
argument-hint: <SMO-NNNN>
allowed-tools: Bash, Read, Edit, Glob
---

Claim task `$ARGUMENTS`.

Steps:
1. Verify `tasks/open/$ARGUMENTS.yml` exists. If not, stop and explain.
2. Validate it against `tasks/schema/task.schema.yml`.
3. `git mv tasks/open/$ARGUMENTS.yml tasks/in-progress/$ARGUMENTS.yml`
4. `git checkout -b agent/$ARGUMENTS-<slug>` (derive `<slug>` from the task's `title` field, kebab-cased, max 30 chars).
5. Export `SHIKSHAN_TASK_ID=$ARGUMENTS` and `SHIKSHAN_AGENT_ID=agent:claude-code` for this session.
6. Invoke the `planner` subagent with the task contract as input.
7. Wait for the planner's plan block. Do NOT proceed to edits in this command — the user reviews the plan first.

Output: the planner's block verbatim, plus a one-line "Branch created: agent/$ARGUMENTS-<slug>" confirmation.
