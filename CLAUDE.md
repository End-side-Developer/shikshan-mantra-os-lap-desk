# CLAUDE.md

Claude Code addendum to [AGENTS.md](AGENTS.md). Read AGENTS.md first; this file only adds Claude-specific details.

## WHAT
Shikshan Mantra OS — Debian 13.5 live-build education OS, 2 GB RAM target, AI-controlled repo. See [PLAN.md](PLAN.md).

## WHY
Strict-mode AI governance: every edit is auditable, every architectural choice has an ADR, every commit is signed, two humans approve sensitive paths. **Phase-3 solo-maintainer relaxation is in force** (see below) until contributors join and SMO-0299 ships the hook-script repairs.

## HOW (Claude specifics)
- Hooks live in [.claude/hooks/](.claude/hooks/) — `pre-tool-use/protected-paths.sh` aborts edits to denied paths; `post-tool-use/audit-append.sh` writes audit rows.
- Subagents: [.claude/agents/planner.md](.claude/agents/planner.md), [.claude/agents/builder.md](.claude/agents/builder.md), [.claude/agents/reviewer.md](.claude/agents/reviewer.md).
- Skills: [.claude/skills/iso-build/](.claude/skills/iso-build/), [.claude/skills/audit-verify/](.claude/skills/audit-verify/), [.claude/skills/lint-manifest/](.claude/skills/lint-manifest/).
- Slash commands: [.claude/commands/iso-build.md](.claude/commands/iso-build.md), [.claude/commands/audit-verify.md](.claude/commands/audit-verify.md), [.claude/commands/task-claim.md](.claude/commands/task-claim.md), [.claude/commands/auto-task.md](.claude/commands/auto-task.md).
- Settings: [.claude/settings.json](.claude/settings.json) is committed (hooks + permissions). [.claude/settings.local.json](.claude/settings.local.json) is gitignored.

## Quick commands
```bash
pre-commit run --all-files                                # local gates
python scripts/audit/verify-chain.py --db docs/audit/audit.db
python scripts/policy/check-protected-paths.py --base origin/main --head HEAD
bash scripts/verify/verify-manifests.sh
```

## Phase-3 solo-maintainer relaxation (TEMPORARY — revisit when contributors join)

The strict workflow in AGENTS.md assumes ≥2 reviewers from ≥2 teams. The project is currently single-maintainer (no GitHub teams exist in the org). Until that changes:

### Self-approval is allowed for solo PRs
- Solo maintainer (the GitHub user who owns the repo) MAY self-merge a PR after:
  - CI is green
  - PR body acknowledges the two-team deviation
  - PR carries the `solo-maintainer-override` label (in addition to `allowlist-override` when touching protected paths)

### Planner subagent skip
The `/task-claim` slash command now skips the planner subagent for **small bounded tasks** (`R.max_diff_lines <= 300`, `R.max_files_changed <= 10`, no protected-path overlap, type in {tests, docs, build-config, adr}). Planner is still invoked for larger or sensitive tasks. See [.claude/commands/task-claim.md](.claude/commands/task-claim.md).

### Autonomous task driver
`/auto-task` runs claim → implement → commit → close → next-task in a loop until the queue is empty or a stop condition fires. See [.claude/commands/auto-task.md](.claude/commands/auto-task.md).

### Pre-commit hooks documented to SKIP
Known-broken hooks until SMO-0299 lands repairs. Use:
```bash
SKIP=yamllint,protected-paths,allowlist-conformance,conventional-pre-commit,shellcheck git commit ...
```
- `protected-paths` — missing `scripts/policy/check-protected-paths.py`
- `allowlist-conformance` — missing `scripts/policy/check-allowlist.py`
- `conventional-pre-commit` — passes `--types` flag that v3.4.0 doesn't recognize
- `yamllint` — too strict on pre-existing task YAML
- `shellcheck` — SC2034 warnings on `LB_*` env vars consumed by live-build externally

`SKIP=` is NOT the same as `--no-verify`. The remaining hooks (gitleaks, audit hash-chain, exec-bit check, trim-whitespace) still run. This is documented Phase-3 procedure, not policy bypass.

### Commit signing
gitsign keyless via OIDC is the goal. If your local environment lacks GPG/sigstore setup, drop `-S` for Phase-3 commits. The `ci-sign-verify` workflow will need to be relaxed in main-branch.json (separate human PR) for unsigned merges to land. When contributors join, restore mandatory signing.

### Phase-3 fast-path summary
For an AI agent (you):
1. `/task-claim SMO-NNNN` — planner skipped for small tasks, you proceed straight to edits
2. Implement per the task contract's `S:` block
3. `SKIP=... git commit -m "...SMO-NNNN..."`
4. Merge into main locally (`git merge --no-ff agent/SMO-NNNN-<slug>`)
5. `git mv tasks/in-progress/SMO-NNNN.yml tasks/completed/`
6. `git push origin main`
7. Loop to next task

## Never
- Skip hooks (`--no-verify`), unsign commits, or edit anything in `policies/`, `.github/workflows/`, `.github/rulesets/`, `scripts/audit/`, `config/bootloaders/`, or `config/archives/*.key.*` without an `allowlist-override` PR with `solo-maintainer-override` (solo mode) or two-team approval (post-contributors).
- Open more than one logical change per PR (still applies in solo mode).
- Touch `docs/audit/audit.db` directly — always go through `scripts/audit/append-entry.py`.
- Use `SKIP=` to bypass `gitleaks`, `detect-private-key`, or the audit hash-chain check. The SKIP allowlist above is exhaustive.
