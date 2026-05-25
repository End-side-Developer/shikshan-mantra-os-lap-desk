# CLAUDE.md

Claude Code addendum to [AGENTS.md](AGENTS.md). Read AGENTS.md first; this file only adds Claude-specific details.

## WHAT
Shikshan Mantra OS — Debian 13.5 live-build education OS, 2 GB RAM target, AI-controlled repo. See [PLAN.md](PLAN.md).

## WHY
Strict-mode AI governance: every edit is auditable, every architectural choice has an ADR, every commit is signed, two humans approve sensitive paths.

## HOW (Claude specifics)
- Hooks live in [.claude/hooks/](.claude/hooks/) — `pre-tool-use/protected-paths.sh` aborts edits to denied paths; `post-tool-use/audit-append.sh` writes audit rows.
- Subagents: [.claude/agents/planner.md](.claude/agents/planner.md), [.claude/agents/builder.md](.claude/agents/builder.md), [.claude/agents/reviewer.md](.claude/agents/reviewer.md).
- Skills: [.claude/skills/iso-build/](.claude/skills/iso-build/), [.claude/skills/audit-verify/](.claude/skills/audit-verify/), [.claude/skills/lint-manifest/](.claude/skills/lint-manifest/).
- Slash commands: [.claude/commands/iso-build.md](.claude/commands/iso-build.md), [.claude/commands/audit-verify.md](.claude/commands/audit-verify.md).
- Settings: [.claude/settings.json](.claude/settings.json) is committed (hooks + permissions). [.claude/settings.local.json](.claude/settings.local.json) is gitignored.

## Quick commands
```bash
pre-commit run --all-files                                # local gates
python scripts/audit/verify-chain.py --db docs/audit/audit.db
python scripts/policy/check-protected-paths.py --base origin/main --head HEAD
bash scripts/verify/verify-manifests.sh
```

## Never
- Skip hooks (`--no-verify`), unsign commits, or edit anything in `policies/`, `.github/workflows/`, `.github/rulesets/`, `scripts/audit/`, `config/bootloaders/`, or `config/archives/*.key.*` without an `allowlist-override` PR with two-team approval.
- Open more than one logical change per PR.
- Touch `docs/audit/audit.db` directly — always go through `scripts/audit/append-entry.py`.
