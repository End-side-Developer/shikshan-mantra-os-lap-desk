# tasks/

File-system-backed agent task queue. Each task is a YAML file that formalizes the work contract per [tasks/schema/task.schema.yml](schema/task.schema.yml). The schema implements the formal C = (I, O, S, R, T, Φ, Ψ) model from [docs/architecture/threat-model.md](../docs/architecture/threat-model.md).

## Lifecycle directories

```
tasks/
├── schema/task.schema.yml      # Contract schema (validated by agent-task-validate.yml)
├── open/                       # Ready-for-agent tasks
├── in-progress/                # Claimed by an agent; PR open
├── completed/                  # Merged — immutable archive (append-only)
├── blocked/                    # Awaiting human decision / ADR / override
└── examples/                   # Reference contracts (read-only learning material)
```

## Lifecycle transitions

```
GitHub Issue (template agent-task.yml)
        │
        ▼ triage assigns SMO-NNNN, files contract
   tasks/open/SMO-NNNN.yml
        │
        ▼ agent claims via `/task-claim SMO-NNNN`
   tasks/in-progress/SMO-NNNN.yml + branch agent/SMO-NNNN-<slug>
        │
        ├── on PR merge → tasks/completed/SMO-NNNN.yml (immutable)
        │
        └── on Ψ-recovery trigger → tasks/blocked/SMO-NNNN.yml + label `needs-human`
                                                  │
                                                  ▼ human resolves → moves back to open/
```

## How an agent claims a task

1. Verify `tasks/open/SMO-NNNN.yml` exists.
2. Validate it against `tasks/schema/task.schema.yml`.
3. `git mv tasks/open/SMO-NNNN.yml tasks/in-progress/SMO-NNNN.yml`
4. `git checkout -b agent/SMO-NNNN-<short-slug>`
5. Export `SHIKSHAN_TASK_ID=SMO-NNNN` and `SHIKSHAN_AGENT_ID=agent:claude-code`.
6. Invoke the [planner](../.claude/agents/planner.md) subagent on the task.
7. After planner approval, hand to [builder](../.claude/agents/builder.md) (see `.claude/commands/task-claim.md`).

The slash command `/task-claim SMO-NNNN` does steps 1-6 automatically.

## Scope enforcement

The `agent-task-validate.yml` workflow runs on every PR labelled `agent-task` (or with a branch matching `agent/SMO-*`). It:
1. Extracts the task ID from the branch name.
2. Schema-validates `tasks/in-progress/SMO-NNNN.yml`.
3. Compares the PR's changed-file set against `task.I.files_in_scope`. Any file outside is a failure.
4. Compares against `policies/protected-paths.yml` `deny:` — any intersection is a failure (regardless of scope).

## Naming

- ID: `SMO-NNNN` (zero-padded 4 digits). Sequential.
- Filename: `SMO-NNNN.yml` (no descriptive slug in the filename — the slug goes in the `title:` field and the branch name).

## Editing rules

- `tasks/open/**` — agent may file new tasks; humans usually do.
- `tasks/in-progress/<self>.yml` — only the agent that claimed the task may edit its own contract. Enforced by hooks + `agent-task-validate`.
- `tasks/completed/**` — append-only; never edited.
- `tasks/blocked/**` — agents move tasks here on Ψ-recovery; humans edit to add resolution notes.

See [policies/agent-allowlist.yml](../policies/agent-allowlist.yml) for the canonical scope rules.

## Plans

Multi-task initiatives have a higher-altitude design doc in [plans/](../plans/). A task may reference its plan via the optional `linked_plan:` field in the schema (path must match `^plans/(active|completed)/[a-z0-9-]+\.md$`). Trivial one-off tasks need no plan. When every task linked to a plan is in `tasks/completed/`, the plan is archived from `plans/active/` to `plans/completed/` (see [.claude/commands/auto-task.md](../.claude/commands/auto-task.md) step 5a).
