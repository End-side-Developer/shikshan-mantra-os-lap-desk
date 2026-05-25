# AGENT_CARD.md — Agents Authorized to Work in This Repository

This card documents every AI agent class permitted to perform tool calls in Shikshan Mantra OS, their scope, their owner, and their revocation procedure. Modeled on the "model card" pattern (Mitchell et al., 2019) extended for agentic systems, and on the EU AI Act Annex IV documentation requirements for high-risk AI systems.

> Adding, removing, or modifying an entry below requires an ADR ([docs/adr/](docs/adr/)) and two-team approval. This file is in [policies/protected-paths.yml](policies/protected-paths.yml) `deny:` list.

---

## Registered Agents

### claude-code (Anthropic Claude family)

| Field | Value |
|---|---|
| Agent ID | `agent:claude-code` |
| Model class | Claude Opus / Sonnet / Haiku (any version ≥ 4.0) |
| Owner | @shikshan/devex |
| Authorized via | Sigstore OIDC subject `https://api.anthropic.com/.well-known/...` |
| Scope (paths) | Per [policies/agent-allowlist.yml](policies/agent-allowlist.yml) ∩ task `I.files_in_scope` |
| Forbidden | Per [AGENTS.md §12](AGENTS.md) and [policies/protected-paths.yml](policies/protected-paths.yml) |
| Budget per task | tokens ≤ 400k, wall ≤ 120 min, files ≤ 40, diff lines ≤ 1500 |
| Evidence trail | [docs/audit/audit.db](docs/audit/audit.db), gitsign signatures, SLSA provenance on releases |
| Escalation | [policies/escalation-matrix.yml](policies/escalation-matrix.yml) |
| Revocation runbook | [docs/runbooks/revoke-agent-credential.md](docs/runbooks/revoke-agent-credential.md) |

### copilot (GitHub Copilot, including Workspace and Coding Agent)

| Field | Value |
|---|---|
| Agent ID | `agent:copilot` |
| Model class | OpenAI / Microsoft models as exposed via GitHub Copilot |
| Owner | @shikshan/devex |
| Authorized via | GitHub OIDC subject `https://token.actions.githubusercontent.com` for Copilot Coding Agent runs |
| Scope (paths) | Same as claude-code |
| Forbidden | Same as claude-code |
| Budget per task | Same as claude-code |
| Evidence trail | Same as claude-code |
| Configuration | [.github/copilot-instructions.md](.github/copilot-instructions.md) (mirrors AGENTS.md §3-§13) |

### human (any maintainer)

| Field | Value |
|---|---|
| Actor ID format | `human:<gh-handle>` |
| Authorized via | GitHub OIDC + 2FA + commit signing (gitsign or hardware-key-backed GPG) |
| Scope (paths) | Full repo; sensitive paths require CODEOWNERS team membership |
| Audit | Same audit hook applies; humans are not exempt |

---

## Capability Boundaries (applies to all agent entries above)

**Allowed tools (when present in agent's harness):**
Read, Glob, Grep, Edit, Write, Bash (only commands in `policies/agent-allowlist.yml` `bash_allowlist:` once populated), TodoWrite, WebFetch (read-only), WebSearch.

**Disallowed tools / actions:**
- Any tool that modifies repository settings, branch protection rules, secrets, or webhooks
- Any tool that opens network sockets to non-allowlisted hosts
- Any tool that executes downloaded code (`curl | sh`, `pip install` from URL, etc.)
- Force-push, history rewrite, tag deletion
- Modifying [.github/](.github/) workflows, rulesets, or CODEOWNERS without `allowlist-override` label and two-team approval

**Out-of-scope work** (do not attempt; escalate):
- Anything requiring access to signing keys
- Anything requiring access to release credentials
- Production deployment actions
- User data handling outside fixture data

---

## Governance Mappings

This card satisfies the following control mappings:
- NIST AI RMF — Govern 1.3, Map 2.1, Measure 2.7, Manage 1.3 ([docs/governance/ai-rmf-mapping.md](docs/governance/ai-rmf-mapping.md))
- ISO/IEC 42001 — Annex A.6.2.4, A.6.2.5, A.6.2.6 ([docs/governance/iso42001-controls.md](docs/governance/iso42001-controls.md))
- OWASP Agentic Top 10 (2025) — A02 Excessive Agency, A07 System Prompt Leakage ([docs/governance/owasp-agentic-top10.md](docs/governance/owasp-agentic-top10.md))

---

## Change History

| Date | Change | ADR |
|---|---|---|
| 2026-05-25 | Initial card with claude-code, copilot, human entries | [docs/adr/0001-debian-live-build.md](docs/adr/0001-debian-live-build.md) (companion governance ADR pending) |
