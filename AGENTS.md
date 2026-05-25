# AGENTS.md — Shikshan Mantra OS

This is the universal contract for every AI agent (Claude Code, Copilot, Gemini, Cursor, Aider, Codex, Devin, Cline, Jules, or any future system) working in this repository. Conforms to the [agents.md](https://agents.md) specification under the Linux Foundation Agentic AI Foundation.

> **Read-First, Read-Always.** Before any tool call that edits or writes a file, you must have read this file, the project [PLAN.md](PLAN.md), [policies/protected-paths.yml](policies/protected-paths.yml), and the ADR linked from your task. If you cannot satisfy a constraint below, stop and escalate per §11.

---

## 1. Project Snapshot

Shikshan Mantra OS is an open-source education OS built on Debian 13.5 "trixie" using `live-build`, targeting 64-bit low-end devices with 2 GB RAM. v1 ships a live USB image, a Calamares install-to-disk path, LXQt as the default desktop with IceWM as a rescue/ultra-low-resource mode, Kolibri for offline learning, signed module catalogs, local SQLite progress, Hindi + English UI parity, school-safe web filtering with admin override, and AI as a learning assistant (no required local LLM on 2 GB devices).

The repository is largely AI-implemented and human-reviewed. This file defines what an AI agent may do, must do, must not do, and how its work is audited.

## 2. Read-First

Mandatory reading for every task, in this order:

1. [PLAN.md](PLAN.md) — canonical product spec
2. This file (AGENTS.md)
3. [policies/protected-paths.yml](policies/protected-paths.yml)
4. [policies/agent-allowlist.yml](policies/agent-allowlist.yml)
5. The ADR referenced by your task (`linked_adr` in [tasks/in-progress/SMO-NNNN.yml](tasks/))
6. The task contract itself ([tasks/schema/task.schema.yml](tasks/schema/task.schema.yml) defines the format)

Tool-specific addenda are subordinate to this file:
- Claude Code: [CLAUDE.md](CLAUDE.md)
- GitHub Copilot: [.github/copilot-instructions.md](.github/copilot-instructions.md)

Closer files override farther files (per agents.md spec); nested AGENTS.md files in subdirectories take precedence over this root file for paths under them.

## 3. Protected Paths

You may **not** edit any path matching the `deny:` patterns in [policies/protected-paths.yml](policies/protected-paths.yml). If a task requires touching a protected path:

1. Stop the edit attempt.
2. Append an incident row to the audit log via [scripts/audit/append-entry.py](scripts/audit/append-entry.py) with `action: "blocked-protected-path"`.
3. Move your task file to `tasks/blocked/` and apply label `needs-human`.
4. Ping the owners listed in [policies/escalation-matrix.yml](policies/escalation-matrix.yml).

Overrides require: PR label `allowlist-override` + two distinct human reviewers from two distinct teams (see §10).

## 4. Allowed Paths

You may freely propose edits to paths in [policies/agent-allowlist.yml](policies/agent-allowlist.yml), subject to:
- The intersection with `I.files_in_scope` from your task contract.
- `append_only:` paths in the allowlist (you may not delete or rewrite history in those files).

If a path is in neither list, treat it as protected.

## 5. Workflow Contract

```
Issue (template agent-task.yml) → label `ready-for-agent`
   → Agent claims: tasks/open/SMO-NNNN.yml → tasks/in-progress/
   → Branch agent/SMO-NNNN-<short-slug>
   → Edits (each Edit/Write triggers audit hook)
   → Local pre-commit (gitleaks, shellcheck, yamllint, schema-validate, protected-paths)
   → Commit: Conventional Commits + gitsign keyless via OIDC
   → PR open (PULL_REQUEST_TEMPLATE checklist completed)
   → Required checks fire (see .github/rulesets/main-branch.json)
   → CODEOWNERS approval (2 distinct teams for sensitive paths)
   → Mergify queues → Merge queue → squash-merge to main with signed merge commit
   → tasks/in-progress/SMO-NNNN.yml → tasks/completed/
```

Branch naming: `agent/SMO-NNNN-<short-slug>` (regex-enforced by `ci-lint.yml`).
One logical change per PR. Multi-purpose PRs will be rejected.

## 6. ADR Requirement

Any change that introduces, removes, or alters an architectural component, a public interface (module manifest, catalog manifest, policy schema, progress record, sync protocol), a build-time choice, or a security/safety default requires a matching ADR in [docs/adr/NNNN-*.md](docs/adr/) **before** the implementation PR. Use [docs/adr/0000-template.md](docs/adr/0000-template.md). The implementation PR must reference its ADR by relative path.

Non-architectural changes (typo fixes, test additions, package list version bumps, runbook edits) do not need ADRs but still need tests where applicable.

## 7. Test Requirement

Every code change ships new or updated tests. Tests live under [tests/](tests/). Coverage may not regress; the `agent-budget-check` workflow enforces this. Specifically:

- Manifest changes → [tests/integration/](tests/integration/) JSON-Schema validation.
- live-build hook changes → [tests/smoke/](tests/smoke/) shell tests + relevant [tests/qemu/](tests/qemu/) script.
- Module additions → fixture under [tests/fixtures/](tests/fixtures/) + manifest-validate test.
- Policy changes → [tests/integration/](tests/integration/) policy parser test.

If you cannot write a meaningful test, document why in the PR body and label `needs-test-review`.

## 8. Commit & Signing

- **Format:** [Conventional Commits 1.0](https://www.conventionalcommits.org/en/v1.0.0/). Types in use: `feat`, `fix`, `chore`, `docs`, `refactor`, `perf`, `test`, `ci`, `build`, `security`, `adr`. Scopes follow top-level dirs (e.g., `feat(modules):`, `fix(config/hooks):`).
- **Signing:** Every commit must be signed via [gitsign](https://docs.sigstore.dev) keyless OIDC. Long-lived GPG keys are not accepted. The `ci-sign-verify` workflow rejects unsigned commits.
- **Authorship:** Agent commits include a trailer:
  ```
  Co-Authored-By: <agent-id> <noreply@anthropic.com>
  ```
  Human-author + agent-co-author is the expected pattern.

## 9. Audit Hook

Every `Edit`, `Write`, or `Delete` you perform fires [.claude/hooks/post-tool-use/audit-append.sh](.claude/hooks/post-tool-use/audit-append.sh), which calls [scripts/audit/append-entry.py](scripts/audit/append-entry.py) to write a hash-chained row into [docs/audit/audit.db](docs/audit/audit.db). Before pushing, you must:

```bash
python scripts/audit/verify-chain.py --db docs/audit/audit.db
```

A non-zero exit means a chain break — do not push. Investigate per [docs/security/incident-response.md](docs/security/incident-response.md).

Schema and HMAC details: [docs/audit/audit-log-spec.md](docs/audit/audit-log-spec.md).

## 10. Token & Time Budgets

Declared in the `R:` block of your task contract; hard caps come from [policies/token-budgets.yml](policies/token-budgets.yml). Exceed a budget → stop, move task to `tasks/blocked/`, label `needs-human`. Do not retry around a budget; the budget is the budget.

Per-task hard ceilings:
- `max_tokens: 400000`
- `max_wall_minutes: 120`
- `max_files_changed: 40`
- `max_diff_lines: 1500`

## 11. Escalation (Ψ Recovery)

| Trigger | Action |
|---|---|
| Budget exceeded | Move task to `tasks/blocked/`, label `needs-human` |
| Protected-path hit | Abort edit, audit row with `action: "blocked-protected-path"`, ping CODEOWNERS |
| Tests fail after 2 attempts | Open PR as draft, label `needs-help` |
| Audit chain break detected | Stop all work, open security incident issue, page security team |
| Ambiguous requirement | Stop, comment on issue requesting clarification, do not guess |

Escalation contacts: [policies/escalation-matrix.yml](policies/escalation-matrix.yml).

## 12. Forbidden Actions

You may never:
- Force-push to any branch you didn't create
- Rewrite history on `main` or any protected branch
- Edit anything under [.github/workflows/](.github/workflows/), [.github/rulesets/](.github/rulesets/), [.github/CODEOWNERS](.github/CODEOWNERS), [policies/](policies/), [scripts/audit/](scripts/audit/), or [config/bootloaders/](config/bootloaders/) without the `allowlist-override` label
- Commit unreviewed binary blobs (any non-text file >100 KB requires human approval)
- Add `curl | sh`, `wget | bash`, or any pipe-to-shell installer pattern
- Disable a pre-commit hook, CI check, or signature verification
- Skip hooks (`--no-verify`), bypass signing (`--no-gpg-sign`), or use `-c commit.gpgsign=false`
- Touch [LICENSE](LICENSE), [SECURITY.md](SECURITY.md), [AGENTS.md](AGENTS.md), or [AGENT_CARD.md](AGENT_CARD.md)
- Introduce a network-dependent step in the ISO build without a corresponding pinned-snapshot ADR
- Add or modify a default-installed package without an ADR

## 13. Safety Defaults (cannot regress)

- **School-safe filtering on by default** (DNS + Firefox/Chromium enterprise policies + optional E2Guardian)
- **Hindi + English UI parity** for every user-visible string change
- **2 GB RAM ceiling** for the default profile; no service added without low-RAM impact analysis
- **Offline-first** — anything requiring network must degrade gracefully without it
- **Signed module catalogs only** — no unsigned catalog may be loaded
- **No telemetry** without explicit opt-in declared in the admin policy file

## 14. Verification Self-Check (run before opening PR)

```bash
# Audit chain integrity
python scripts/audit/verify-chain.py --db docs/audit/audit.db

# Protected-path policy
python scripts/policy/check-protected-paths.py --base origin/main --head HEAD

# Allowlist conformance vs task contract
python scripts/policy/check-allowlist.py --task tasks/in-progress/SMO-NNNN.yml --diff

# Manifest schema validation
bash scripts/verify/verify-manifests.sh

# Local pre-commit (full)
pre-commit run --all-files

# If you touched anything in config/ — clean build sanity (optional, slow):
bash scripts/build/build-iso.sh --quick
```

All must exit 0 before you open the PR.

## 15. Glossary & Pointers

- Architecture: [docs/architecture/](docs/architecture/)
- Threat model: [docs/architecture/threat-model.md](docs/architecture/threat-model.md)
- Security policy: [docs/security/](docs/security/)
- Runbooks: [docs/runbooks/](docs/runbooks/)
- Governance mappings (NIST AI RMF, ISO 42001, OWASP Agentic Top 10): [docs/governance/](docs/governance/)
- Model card (for any model used by the OS, not for agents writing code): [docs/MODEL_CARD.md](docs/MODEL_CARD.md)
- Agent card (capabilities/scope of agents working on this repo): [AGENT_CARD.md](AGENT_CARD.md)
- Glossary: [docs/glossary.md](docs/glossary.md)

---

**By performing any tool call in this repository you affirm that you have read and will follow this contract.** Violations are auditable, attributable to the agent's OIDC subject, and grounds for revoking the agent's credential per [docs/runbooks/revoke-agent-credential.md](docs/runbooks/revoke-agent-credential.md).
