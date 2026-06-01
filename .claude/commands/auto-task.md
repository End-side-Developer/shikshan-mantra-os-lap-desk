---
description: One-shot autonomous task driver. Claim, implement, test, commit, close, repeat — until tasks/open/ is empty for the requested filter or the user says stop.
argument-hint: [SMO-NNNN | --next-ai-doable | --phase=N]
allowed-tools: Bash, Read, Edit, Write, Glob, Grep
---

Run autonomously. Goal: maximize tasks shipped per turn. Stop only on:
- A planner-required task (per the planner-skip rules in `task-claim.md`)
- A protected-path conflict
- A test failure after one retry
- Budget overrun
- The user types `stop`

## Selection

- If `$ARGUMENTS` is `SMO-NNNN` → drive just that task.
- If `$ARGUMENTS` is `--next-ai-doable` → pick the lowest-numbered task in `tasks/open/` where:
  - `agent: claude-code`
  - All preconditions in the `preconditions:` block are satisfied (linked tasks merged on main, etc.)
  - No `I.files_in_scope` path is in `policies/protected-paths.yml#deny`
- If `$ARGUMENTS` is `--phase=N` → as above, filtered to SMO-0N00..0N99.
- No args → equivalent to `--next-ai-doable`.

## Loop, per task

1. Run `/task-claim SMO-NNNN` (which now skips the planner for small tasks per its updated rules).
2. Implement each file in `I.files_in_scope` so every `S:` (success criterion) holds. Run any tests the task specifies (`tests/...` paths in `O.tests_added`).
3. Commit with the Phase-3 SKIP set:

   ```bash
   SKIP=yamllint,protected-paths,allowlist-conformance,conventional-pre-commit,shellcheck \
     git commit -m "<type>(<scope>): SMO-NNNN <one-line summary>"
   ```

   (signing skipped per [project_phase3_local_workflow](memory); use `-S` if the user's GPG is set up.)

4. Merge the agent branch into main locally:
   ```bash
   git checkout main && git merge --no-ff agent/SMO-NNNN-<slug> -m "Merge SMO-NNNN: <summary>"
   ```
5. Close the task: `git mv tasks/in-progress/SMO-NNNN.yml tasks/completed/`. Commit `chore(tasks): SMO-NNNN close — <summary>`.
5a. **Plan archive check.** If the closed task had a non-null `linked_plan:` pointing at `plans/active/<slug>.md`, read that plan's `linked_tasks:` frontmatter. If every ID in that list is now present in `tasks/completed/`, `git mv plans/active/<slug>.md plans/completed/<slug>.md`, flip `status: active` → `status: completed` in the frontmatter, and commit `chore(plans): archive <slug> — all linked tasks merged`. If any linked task is still in `open/`, `in-progress/`, or `blocked/`, leave the plan in `active/` and continue. Skip this step entirely if the task had no `linked_plan:` or the plan path is already under `plans/completed/`.
6. Push main to origin.
7. Report a one-line summary of what shipped, then immediately re-enter the loop with the next AI-doable task.

## Stop conditions (announce clearly)

- "STOP: SMO-NNNN requires planner (large or sensitive)."
- "STOP: SMO-NNNN touches protected path X. Needs user/human override."
- "STOP: tests failed after retry: <one-line diagnosis>."
- "STOP: queue exhausted for filter."

## Final report

After the loop exits:
- N tasks shipped: SMO-NNNN, SMO-NNNN, ...
- M tasks remaining open
- K tasks blocked (with one-line reason each)
- Current ISO-build CI status (`gh pr checks` on the latest open PR if any)
