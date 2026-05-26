---
description: Claim a task from tasks/open/, move it to tasks/in-progress/, create the branch. Planner is invoked only for large or sensitive tasks; small tasks proceed directly to build.
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

6. **Decide whether to invoke the planner subagent.**

   **Skip the planner** (proceed directly to implementation) when ALL of the following hold:
   - `agent: claude-code` in the task contract
   - `R.max_diff_lines <= 300`
   - `R.max_files_changed <= 10`
   - No path in `I.files_in_scope` matches a glob in `policies/protected-paths.yml#deny`
   - Task `type` is one of: `tests`, `docs`, `build-config`, `adr`

   **Invoke the planner** otherwise (large changes, protected-path overrides, security-sensitive types, novel architecture).

   Skip-mode rationale: per [project_phase3_local_workflow](memory) + [feedback_velocity_over_ceremony](memory), small bounded tasks don't benefit from a planner roundtrip — the contract's `S:` block already specifies success criteria. The planner is the right tool when scope is ambiguous; bounded tasks just need execution.

7. **If planner skipped:** announce "Planner skipped (small task, bounded). Beginning implementation per task contract S: criteria." Then proceed with the edits in the same turn.

8. **If planner invoked:** wait for the planner's plan block. Do NOT proceed to edits in this command — the user reviews the plan first.

Output:
- One-line "Branch created: agent/$ARGUMENTS-<slug>"
- Either the planner block verbatim, OR a "Planner skipped — implementing now" announcement followed by the actual edits.
