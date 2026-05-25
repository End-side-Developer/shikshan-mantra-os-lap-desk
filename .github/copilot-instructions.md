# Copilot Instructions

This file is for GitHub Copilot (Workspace, Coding Agent, Chat). The full agent contract is in [AGENTS.md](../AGENTS.md) — read it first; this file only restates the highest-leverage rules.

## Before suggesting any edit

1. Read [AGENTS.md](../AGENTS.md), [PLAN.md](../PLAN.md), [policies/protected-paths.yml](../policies/protected-paths.yml).
2. If the file you are about to edit matches a `deny:` glob in `protected-paths.yml`, **stop**. Suggest opening a `tasks/blocked/` entry or applying the `allowlist-override` label with two-team approval.

## Do
- Use [Conventional Commits 1.0](https://www.conventionalcommits.org/en/v1.0.0/) for commit messages.
- Add or update tests for every code change.
- Add an ADR (`docs/adr/NNNN-<slug>.md`) for any architectural change before code.
- Sign commits with gitsign.
- Keep Hindi/English UI string parity.
- Cap PRs at one logical change.

## Don't
- Edit `policies/`, `.github/workflows/`, `.github/rulesets/`, `.github/CODEOWNERS`, `scripts/audit/`, `config/bootloaders/`, `config/archives/*.key.*`, `AGENTS.md`, `AGENT_CARD.md`, `LICENSE`, or `SECURITY.md` without an explicit override.
- Use `git push --force`, `git rebase -i`, `git commit --no-verify`, or `git commit --amend`.
- Add `curl | sh` or any pipe-to-shell installer.
- Disable a pre-commit hook or CI check.
- Touch `docs/audit/audit.db` directly — always via `scripts/audit/append-entry.py`.

## Tooling we expect you to use

| Task | Tool |
|---|---|
| Lint | `pre-commit run --all-files` (yamllint, shellcheck, markdownlint, ruff, gitleaks) |
| Manifest validation | `bash scripts/verify/verify-manifests.sh` |
| Audit chain | `python scripts/audit/verify-chain.py --since-commit origin/main` |
| Allowlist conformance | `python scripts/policy/check-allowlist.py --task tasks/in-progress/SMO-NNNN.yml --diff` |
| Build ISO locally | `bash scripts/build/build-iso.sh` |

## Branch naming

`agent/SMO-NNNN-<short-slug>` — required so the `agent-task-validate` workflow can match the PR to a task contract.

## When in doubt

Stop and ask a human. The escalation matrix is at [policies/escalation-matrix.yml](../policies/escalation-matrix.yml).
