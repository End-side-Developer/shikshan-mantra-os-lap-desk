# Contributing to Shikshan Mantra OS

This guide is for **human contributors**. Agents (Claude Code, Copilot, and peers) follow [AGENTS.md](AGENTS.md) — humans should read it too, because the same gates apply to everyone.

## Before you start

1. Read [AGENTS.md](AGENTS.md), [PLAN.md](PLAN.md), [policies/protected-paths.yml](policies/protected-paths.yml).
2. Install local tooling:
   ```bash
   bash scripts/dev/bootstrap.sh
   pre-commit install --install-hooks
   ```
   This installs `pre-commit`, `cosign`, `gitsign`, `syft`, `lintian`, `shellcheck`, `yamllint`, and project-specific schema validators.
3. Configure commit signing:
   ```bash
   gitsign initialize
   git config --local commit.gpgsign true
   git config --local gpg.x509.program gitsign
   git config --local gpg.format x509
   ```

## How to file work

| Type | Use template | Notes |
|---|---|---|
| Bug | `.github/ISSUE_TEMPLATE/bug.yml` | Include repro steps |
| New learning module | `.github/ISSUE_TEMPLATE/module-proposal.yml` | Catalog publishers welcome |
| Architectural change | `.github/ISSUE_TEMPLATE/adr-request.yml` | Auto-creates ADR draft |
| Task an agent can pick up | `.github/ISSUE_TEMPLATE/agent-task.yml` | Becomes `tasks/open/SMO-NNNN.yml` |

Humans use the agent-task template too — the contract is uniform. The only difference is branch naming.

## Branch naming

- Humans: `human/<your-gh-handle>/<short-slug>`
- Agents: `agent/SMO-NNNN-<short-slug>`
- Hot-fix on a release: `hotfix/v<X.Y.Z>/<slug>`

## Commits

- [Conventional Commits 1.0](https://www.conventionalcommits.org/en/v1.0.0/) — enforced by `ci-commit-lint`.
- Signed via gitsign — enforced by `ci-sign-verify`.
- Scope after `type` should map to a top-level directory: `feat(modules):`, `fix(config/hooks):`, `docs(adr):`, `ci(workflows):`, etc.

## Before you open a PR

Run the self-check:

```bash
pre-commit run --all-files
python scripts/audit/verify-chain.py --db docs/audit/audit.db
python scripts/policy/check-protected-paths.py --base origin/main --head HEAD
bash scripts/verify/verify-manifests.sh
```

All must exit 0.

## ADR requirement

Architectural changes (new public interface, new component, change to a safety default, change to the build pipeline shape) require a matching ADR in `docs/adr/NNNN-<slug>.md` before the implementation PR. Use `docs/adr/0000-template.md`. Reference the ADR file path in the PR body.

## Tests

Every code change ships new or updated tests. See AGENTS.md §7 for the test placement matrix.

## Review

- Default: 1 CODEOWNERS approval.
- Sensitive paths (per [policies/sensitive-change-labels.yml](policies/sensitive-change-labels.yml)): 2 approvals from 2 distinct CODEOWNERS teams — enforced by `.github/rulesets/protected-paths.json`.
- All conversations must be resolved before merge.
- Mergify queues the PR once approvals + checks are green.

## Releases

- Tag `vX.Y.Z` on `main`.
- `release-slsa.yml` generates SLSA L2+ in-toto provenance.
- `release-cosign-sign.yml` signs ISO + SBOM + provenance keylessly via OIDC.
- `release-publish.yml` attaches all artifacts to the GitHub Release.

## Code of Conduct

This project follows the [Contributor Covenant 2.1](CODE_OF_CONDUCT.md).

## Questions

Open a Discussion or reach out at `community@shikshan-mantra.example`.
