# ISO/IEC 42001 — Annex A Control Mapping

This repo's controls mapped to [ISO/IEC 42001:2023 — Information technology — Artificial intelligence — Management system](https://www.iso.org/standard/42001). Scope is the AI-agent development surface that builds Shikshan Mantra OS.

Not all 38 Annex A controls are applicable to a greenfield open-source repository; the table below covers those that are.

## A.2 — Policies related to AI

| Control | Our evidence |
|---|---|
| A.2.2 AI policy | [AGENTS.md](../../AGENTS.md) — top-level agent contract |
| A.2.3 Alignment with other policies | AGENTS.md cross-references SECURITY.md, LICENSE, CODE_OF_CONDUCT.md |
| A.2.4 Review of AI policy | ADR process for any AGENTS.md change; `touches-policy` requires governance + security |

## A.3 — Internal organization

| Control | Our evidence |
|---|---|
| A.3.2 Roles and responsibilities | [AGENT_CARD.md](../../AGENT_CARD.md), [.github/CODEOWNERS](../../.github/CODEOWNERS), [policies/escalation-matrix.yml](../../policies/escalation-matrix.yml) |
| A.3.3 Reporting of concerns | `.github/ISSUE_TEMPLATE/security-incident.yml`; SECURITY.md private reporting path |

## A.4 — Resources for AI systems

| Control | Our evidence |
|---|---|
| A.4.2 Resource documentation | This `docs/` tree; AGENT_CARD per-agent budget |
| A.4.3 Data resources | No training data in this repo; module content is governed by per-module licenses |
| A.4.4 Tooling resources | `.claude/`, `.pre-commit-config.yaml`, `scripts/` |
| A.4.5 System and computing resources | `policies/token-budgets.yml`, GitHub-hosted runners |
| A.4.6 Human resources | CODEOWNERS team structure + Code of Conduct |

## A.5 — Impact assessment

| Control | Our evidence |
|---|---|
| A.5.2 AI system impact assessment process | Each ADR's "Decision Drivers" + "Consequences" sections |
| A.5.3 Documentation of AI system impact assessments | `docs/adr/` |
| A.5.4 Assessing AI system impact on individuals/groups | [docs/architecture/threat-model.md](../architecture/threat-model.md) "Residual risk" |
| A.5.5 Assessing societal impacts | Safety defaults section in AGENTS.md §13; `@shikshan/safety` team review on safety-defaults touches |

## A.6 — AI system life cycle

| Control | Our evidence |
|---|---|
| A.6.2.2 Objectives for responsible development | AGENTS.md §13 (safety defaults) |
| A.6.2.3 Processes for responsible design and development | `tasks/` queue + planner/builder/reviewer subagents + ADR-gated changes |
| A.6.2.4 Requirements and specification | Task contracts (`tasks/schema/task.schema.yml`), PLAN.md, ADRs |
| A.6.2.5 Documentation of AI system design and development | `docs/architecture/`, `docs/adr/`, `AGENT_CARD.md`, audit log |
| A.6.2.6 AI system verification and validation | All `ci-*` workflows; reviewer subagent; reproducibility check |
| A.6.2.7 AI system deployment | Release workflows (slsa, cosign, publish) gated by ruleset |
| A.6.2.8 AI system operation and monitoring | Audit log + post-merge `ci-audit-chain` + release-tail signature |

## A.7 — Data for AI systems

| Control | Our evidence |
|---|---|
| A.7.2 Data for development and enhancement | n/a — we do not train models in this repo |
| A.7.3 Acquisition of data | Module content governance via module-proposal template + signed catalogs |
| A.7.4 Quality of data | `lint-manifest` skill + `ci-schema-validate` workflow |
| A.7.5 Data provenance | SBOM (CycloneDX) for software; per-module `checksum` + `signature` for content |

## A.8 — Information for interested parties

| Control | Our evidence |
|---|---|
| A.8.2 System documentation and information for users | README.md, docs/runbooks/ |
| A.8.3 External reporting | SECURITY.md, GitHub Discussions, Issue templates |
| A.8.4 Communication of incidents | docs/security/incident-response.md, coordinated disclosure window in SECURITY.md |
| A.8.5 Information for interested parties | This `docs/governance/` directory + public release notes |

## A.9 — Use of AI systems

| Control | Our evidence |
|---|---|
| A.9.2 Processes for responsible use | AGENTS.md §3-§13 |
| A.9.3 Objectives for responsible use | AGENTS.md §13 + safety-defaults label |
| A.9.4 Intended use of the AI system | AGENT_CARD per-agent "Scope (paths)" + "Out-of-scope work" |

## A.10 — Third-party and customer relationships

| Control | Our evidence |
|---|---|
| A.10.2 Allocating responsibilities | CODEOWNERS, escalation matrix |
| A.10.3 Suppliers | SBOM tracks every Debian package; community catalogs declared by `trust_level` |
| A.10.4 Customers | Not commercial; community channel is Discussions |
