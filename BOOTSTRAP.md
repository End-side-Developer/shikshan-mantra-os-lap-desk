# Bootstrap — Final Human-Only Steps

The enterprise AI-controlled scaffold for Shikshan Mantra OS is complete, but several files **could not be written by the scaffolding agent** because the harness sandbox enforces our own `policies/protected-paths.yml` deny list. This is correct: those files are precisely the ones that should be created by a human, signed, and protected from agent modification forever after.

Complete these steps **once**, by a human, then the strict-mode governance is live and every subsequent change (agent or human) must go through the contract in [AGENTS.md](AGENTS.md).

## Quick reference — what's still pending

Each row below points at a runbook with the exact contents to commit.

| # | What to create | Runbook |
|---|---|---|
| 1 | `.github/CODEOWNERS` (rename from `.github/CODEOWNERS.template`) | inline below |
| 2 | `.github/rulesets/{main-branch,protected-paths,release-tags}.json` + README | [docs/runbooks/github-rulesets-bootstrap.md](docs/runbooks/github-rulesets-bootstrap.md) |
| 3 | All `.github/workflows/*.yml` (28 files) | [docs/runbooks/github-workflows-bootstrap.md](docs/runbooks/github-workflows-bootstrap.md) |
| 4 | `docs/adr/{0000-template,0001-debian-live-build,0002-audit-log-storage}.md` | [docs/runbooks/seed-adrs-bootstrap.md](docs/runbooks/seed-adrs-bootstrap.md) |
| 5 | `config/bootloaders/README.md` + `config/packages.chroot/README.md` + `config/includes.chroot/etc/firefox/policies/policies.json` | [docs/runbooks/protected-config-bootstrap.md](docs/runbooks/protected-config-bootstrap.md) |
| 6 | `scripts/policy/{check-protected-paths,check-allowlist,check-budget}.py` + `scripts/verify/verify-slsa.sh` + their README | [docs/runbooks/policy-scripts-bootstrap.md](docs/runbooks/policy-scripts-bootstrap.md) |
| 7 | Import GitHub Rulesets into the org | end of runbook #2 |

## Order matters

Do them in this order so each step has its prerequisites:

1. **#4 first** (seed ADRs) — these document foundational decisions that everything else references.
2. **#6** (policy scripts) — pre-commit hooks need them present.
3. **#1** (CODEOWNERS) — needed before opening any PR with sensitive-path touches.
4. **#5** (protected-config readmes + Firefox policy).
5. **#3** (workflows) — before pushing to GitHub.
6. **#2 + #7** (rulesets created locally, then imported into the org).

## CODEOWNERS — single git mv

```bash
git mv .github/CODEOWNERS.template .github/CODEOWNERS
git commit -S -m "ci(codeowners): activate two-team review on sensitive paths"
```

The agent could not write `.github/CODEOWNERS` directly because the sandbox treats it as security-sensitive metadata. The content lives in `.template` and is otherwise identical.

## After the bootstrap

Verify the scaffold by filing the example task `tasks/examples/SMO-9001-add-module-manifest.yml` as a real issue, letting Claude Code execute it, and confirming:

- Audit chain has new entries (`python scripts/audit/verify-chain.py`)
- PR carries all required-status checks
- Protected-paths gate blocks an attempted edit to `.github/workflows/`
- SLSA attestation verifies on the merge artifact (after first release)

## Why this works the way it does

This pattern — "agent scaffolds the bulk; human seeds the protected core" — is the *correct* shape for an AI-controlled repository. The strict mode is real, not theatre: the sandbox refused to write the files that protect agents from themselves. Treat the runbooks above as the human-only initialization ritual that the rest of the repo's lifecycle never repeats.
