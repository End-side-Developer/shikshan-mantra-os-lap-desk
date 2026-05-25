# NIST AI RMF — Control Mapping

This repo's controls mapped to [NIST AI RMF 1.0](https://www.nist.gov/itl/ai-risk-management-framework) and [NIST AI 600-1](https://www.nist.gov/publications/artificial-intelligence-risk-management-framework-generative-artificial-intelligence) (generative-AI profile).

Scope: the AI agents that develop this repo. Not the optional in-OS AI assistant (covered in `docs/MODEL_CARD.md`).

## Govern

| RMF subcategory | Our evidence |
|---|---|
| GOVERN 1.1 — Policies for AI risk are established | [AGENTS.md](../../AGENTS.md), [policies/protected-paths.yml](../../policies/protected-paths.yml), [policies/agent-allowlist.yml](../../policies/agent-allowlist.yml), [policies/token-budgets.yml](../../policies/token-budgets.yml) |
| GOVERN 1.3 — Roles and responsibilities | [AGENT_CARD.md](../../AGENT_CARD.md), [.github/CODEOWNERS](../../.github/CODEOWNERS), [policies/escalation-matrix.yml](../../policies/escalation-matrix.yml) |
| GOVERN 2.1 — Change-management process | ADRs ([docs/adr/](../adr/)), PR + CODEOWNERS + Rulesets, `tasks/` queue |
| GOVERN 5.1 — Documentation maintained | This `docs/` tree, periodic JSONL audit exports |
| GOVERN 6.1 — Stakeholder engagement | `.github/ISSUE_TEMPLATE/*` (community can file), Discussions, Code of Conduct |

## Map

| RMF subcategory | Our evidence |
|---|---|
| MAP 1.1 — Context, scope, intended use | [README.md](../../README.md), [PLAN.md](../../PLAN.md), [AGENT_CARD.md](../../AGENT_CARD.md) "Scope (paths)" |
| MAP 2.1 — System purpose | AGENT_CARD per-agent rows |
| MAP 4.1 — Risks identified | [docs/architecture/threat-model.md](../architecture/threat-model.md), [docs/governance/owasp-agentic-top10.md](owasp-agentic-top10.md) |
| MAP 5.1 — Impact assessment | threat-model.md "Residual risk" section |

## Measure

| RMF subcategory | Our evidence |
|---|---|
| MEASURE 1.1 — Metrics for evaluation | Required CI checks ([.github/workflows/](../runbooks/github-workflows-bootstrap.md)), `agent-budget-check` actual-vs-declared |
| MEASURE 2.7 — Trustworthy AI characteristics tested | Audit chain integrity (`ci-audit-chain`), SBOM + CVE gates, reproducibility test |
| MEASURE 2.8 — Performance against deployment | Lintian + QEMU smoke tests, 2 GB-RAM ceiling enforced in `ci-qemu-*` |
| MEASURE 3.1 — Mechanisms for tracking risk over time | `docs/audit/audit.db` hash-chained log, periodic JSONL exports |

## Manage

| RMF subcategory | Our evidence |
|---|---|
| MANAGE 1.3 — Risk-management actions documented | ADRs, incident-response runbook, escalation matrix |
| MANAGE 2.2 — Resources for response | On-call links in `policies/escalation-matrix.yml`, runbooks in `docs/runbooks/` |
| MANAGE 4.1 — Post-deployment monitoring | Audit log + `ci-audit-chain` + release-tail cosign signing |

## NIST AI 600-1 (generative-AI) specifics

| 600-1 risk | Our mitigation |
|---|---|
| Confabulation | Reviewer subagent must run before merge on sensitive paths; human two-team approval is required (not just one); agents cannot self-approve |
| Data privacy | No PII flows into the repo; admin policy defaults `ai_provider_mode: off` for the in-OS assistant |
| Environmental impact | Token + time budgets in `policies/token-budgets.yml`; `agent-budget-check` enforces |
| Harmful bias | Hi+En parity for UI strings; content review for `modules/core/` via `@shikshan/content` + `@shikshan/safety` CODEOWNERS |
| Human-AI configuration | `AGENT_CARD.md` + per-task contract makes the agent boundary explicit |
| Information integrity | gitsign + audit chain + SLSA + Cosign + Rekor |
| Information security | OWASP Agentic Top 10 mapping in [docs/architecture/threat-model.md](../architecture/threat-model.md) |
| Intellectual property | License scan (`ci-license-scan`), SPDX in every module manifest |
| Obscene / illegal content | Module proposal gate via `@shikshan/safety`; default school-safe DNS + browser policies |
| Toxicity, hate, bias | Same as above |
| Value-chain risk | SLSA provenance pins build origin; reproducibility test detects supply-chain anomalies |
