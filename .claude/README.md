# .claude/

Claude Code workspace configuration for Shikshan Mantra OS.

| Path | What |
|---|---|
| [settings.json](settings.json) | Committed: permissions allow/deny, hook bindings, env vars. **Protected** — changes require touches-policy two-team approval. |
| `settings.local.json` | Gitignored per-developer overrides. Add personal MCP servers, extra permissions, etc. |
| [hooks/](hooks/) | Pre/post/stop hooks that enforce protected-paths, write audit rows, and finalize tasks. |
| [agents/](agents/) | Subagent definitions: `planner` (read-only design), `builder` (executes plan), `reviewer` (read-only second opinion). |
| [skills/](skills/) | Reusable workflows: `iso-build`, `audit-verify`, `lint-manifest`. |
| [commands/](commands/) | Slash commands users invoke: `/iso-build`, `/audit-verify`, `/task-claim SMO-NNNN`. |

## Required environment for agent sessions

Set before working:
```bash
export SHIKSHAN_AGENT_ID="agent:claude-code"   # so audit rows attribute correctly
export SHIKSHAN_TASK_ID="SMO-0042"              # the task you've claimed
export SHIKSHAN_REPO_ROOT="$(pwd)"             # usually auto-set by Claude Code
```

If `SHIKSHAN_TASK_ID` is unset, the hooks still record audit rows but without task attribution — the PR validator will reject.

## Hook flow

```
User asks for an Edit/Write
  → PreToolUse hooks fire:
      load-context.sh           (once per session reminder)
      protected-paths.sh        (aborts if target is in deny list)
  → If allowed, tool executes
  → PostToolUse hook fires:
      audit-append.sh           (appends hash-chained row)
  ...
Session ends
  → Stop hook fires:
      finalize-task.sh          (final audit row + chain verify)
```

## See also
- [AGENTS.md](../AGENTS.md) — universal contract (read this first)
- [policies/](../policies/) — protected paths, allowlist, labels, budgets
- [docs/audit/audit-log-spec.md](../docs/audit/audit-log-spec.md) — what the hooks write into
