<!--
Thanks for the PR. AGENTS.md §5 (Workflow Contract) applies to humans and
agents alike. Fill in every section below. Any missing section will block
the agent-task-validate workflow.
-->

## Summary

<!-- One paragraph. Why this change exists, not what it does. -->

## Linked task / issue

- Task: `tasks/in-progress/SMO-NNNN.yml`
- Issue: #
- ADR (required if architectural): `docs/adr/NNNN-<slug>.md`

## Type

- [ ] feat
- [ ] fix
- [ ] chore
- [ ] docs
- [ ] refactor
- [ ] perf
- [ ] test
- [ ] ci
- [ ] build
- [ ] security
- [ ] adr

## Checklist (AGENTS.md §14)

- [ ] I read `AGENTS.md`, `policies/protected-paths.yml`, and the linked ADR.
- [ ] All changed paths are in `policies/agent-allowlist.yml` ∩ `task.I.files_in_scope`.
- [ ] No changed path matches `policies/protected-paths.yml` `deny:` (or the `allowlist-override` label is applied with explicit two-team approval).
- [ ] Tests added/updated for every code change. Coverage does not regress.
- [ ] An ADR exists for any architectural change, and this PR references it.
- [ ] All commits are signed via gitsign (keyless OIDC).
- [ ] PR title and every commit message use Conventional Commits.
- [ ] `pre-commit run --all-files` passes locally.
- [ ] `python scripts/audit/verify-chain.py` exits 0 locally.
- [ ] `python scripts/policy/check-protected-paths.py --base origin/main --head HEAD` exits 0.
- [ ] `bash scripts/verify/verify-manifests.sh` exits 0.
- [ ] If UI strings changed: Hindi + English parity verified.
- [ ] If a network dependency was added to the build: ADR cites the snapshot/pin source.

## Budget actual vs declared

<!-- The agent-budget-check workflow reads this. Format: `key: actual / declared`. -->

```yaml
tokens:        ___ / ___
wall_minutes:  ___ / ___
files_changed: ___ / ___
diff_lines:    ___ / ___
```

## Audit references

- Last `sequence_number` added by this PR: `___`
- Audit-chain verify command output (paste):
  ```
  ```

## SLSA provenance

This PR does not produce a release artifact. SLSA provenance is generated at `vX.Y.Z` tag time by `release-slsa.yml`.

## How a reviewer can re-verify locally

```bash
gh pr checkout <this-pr>
pre-commit run --all-files
python scripts/audit/verify-chain.py --since-commit origin/main
python scripts/policy/check-protected-paths.py --base origin/main --head HEAD
bash scripts/verify/verify-manifests.sh
```

---

🤖 _Generated/assisted by an AI agent per AGENTS.md. Co-Authored-By trailer in commits names the agent._
