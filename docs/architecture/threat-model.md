# Threat Model

Threats organized by STRIDE per component, with OWASP Top 10 for Agentic Applications (2025) mappings for the AI-development surface.

## Components

| ID | Component | Trust boundary |
|---|---|---|
| C1 | live-build pipeline (CI) | GitHub Actions runner |
| C2 | Module catalog (official + community) | Catalog publisher's signing key |
| C3 | Local launcher + verifier (on-device) | OS root |
| C4 | Progress store (SQLite) | User homedir / persistence partition |
| C5 | Sync client (optional) | Per-school bearer token |
| C6 | AI assistant (optional) | Local/server/cloud provider |
| C7 | AI-development surface (this repo) | GitHub OIDC + agent contract |

## STRIDE per component

### C1 — live-build pipeline

| Threat | Vector | Mitigation |
|---|---|---|
| Spoofing | Malicious PR that injects a hook running at chroot | `policies/protected-paths.yml` denies edits under `config/bootloaders/`, `config/archives/*.key.*`, `config/packages.chroot/`; remaining `config/hooks/` reviewed by `platform` team |
| Tampering | Tamper with `snapshot.debian.org` pin | Pin URL pre-validated in CI; reproducible build re-pulls and diffs SHA-256 |
| Repudiation | "I didn't add that package" | gitsign signed commits + `docs/audit/audit.db` row per Edit/Write |
| Info disclosure | Secret leaked to ISO | Gitleaks + TruffleHog gate; no secrets ever live in ISO (admin policy on disk is non-secret) |
| DoS | Malicious hook that never returns | live-build timeout in `ci-build-iso.yml` (60min) |
| EoP | Hook escalates inside chroot | live-build runs hooks as root in chroot but the chroot is destroyed after build; runtime image has no setuid surprises (lintian gate) |

### C2 — Module catalog

| Threat | Vector | Mitigation |
|---|---|---|
| Spoofing | Fake catalog claiming `official` trust | Catalog `signature` verified against the OS root key; `trust_level` is decided by the OS root key, not the catalog |
| Tampering | Module content modified after publish | `module.checksum` validates content tree on each launch |
| Repudiation | Publisher denies issuing a catalog | Cosign Rekor entry pins the signature timeline |
| Info disclosure | n/a (catalog is public) | — |
| DoS | Large catalog that hangs the launcher | Catalog size cap in `policy.yml`; verifier streaming, not buffer-all |
| EoP | Malicious module escalates from sandbox | Module content_type restricted to web/PDF/Blockly/Python in jail; native apps via `required_apps` debian packages only (vetted) |

### C3 — Local launcher + verifier

| Threat | Vector | Mitigation |
|---|---|---|
| Tampering | User modifies on-disk content to bypass `checksum` | Re-verify on every launch; admin policy can enforce `verify_on_every_launch: true` |
| EoP | Launcher runs unsandboxed | Web content under Firefox kiosk profile with `policies.json` lockdown; native via Firejail (deferred to Phase 2 ADR) |

### C4 — Progress store

| Threat | Vector | Mitigation |
|---|---|---|
| Info disclosure | Persistence partition stolen | LUKS encryption when admin policy requires |
| Tampering | Student manually edits scores | Acceptable risk; progress is for the learner, not high-stakes assessment |

### C5 — Sync client

| Threat | Vector | Mitigation |
|---|---|---|
| Spoofing | Rogue server impersonates school endpoint | TLS pin (cert SPKI hash in admin policy); bearer token rotation runbook |
| Info disclosure | Sync exposes student data over the wire | Push-only by default; policy controls pull; only opaque `student_id_local`, no PII beyond display name |

### C6 — AI assistant

| Threat | Vector | Mitigation |
|---|---|---|
| Spoofing | Cloud provider returns harmful content | Content moderation layer per provider; admin policy can disable cloud tier entirely |
| Info disclosure | Student prompt leaks to provider | Admin policy declares `ai_provider_mode: off/local/server/cloud`; default is `off` for school deployments |

### C7 — AI-development surface

| Threat | Vector | Mitigation |
|---|---|---|
| Spoofing | Agent claims to be `agent:claude-code` when it isn't | Sigstore OIDC subject in audit row; gitsign on every commit |
| Tampering | Agent rewrites past audit rows | SQLite triggers + HMAC chain + release-tag cosign signature on tail |
| Repudiation | Agent denies an Edit | Hash-chained `docs/audit/audit.db` row per Edit/Write |
| Info disclosure | Agent exfiltrates secret via WebFetch | `bash_forbidden` denies pipe-to-shell; secrets gated by gitleaks; no secrets in repo |
| DoS | Agent exhausts CI minutes | `policies/token-budgets.yml` enforced by `agent-budget-check` |
| EoP | Agent modifies CI to relax checks | `.github/workflows/`, `.github/rulesets/`, CODEOWNERS, `policies/` all in `protected-paths.yml` deny list |

## OWASP Top 10 for Agentic Applications (2025) — Mappings

| OWASP item | Our mitigation |
|---|---|
| A01 Prompt injection | Agent task contracts (`tasks/schema/task.schema.yml`) define `I.files_in_scope`; protected-paths hook prevents drift; PR reviewer subagent catches anomalies |
| A02 Excessive agency | `policies/protected-paths.yml` `deny:` + `agent-allowlist.yml` + per-task `R:` budget + `bash_forbidden` + sandbox-level write denials on `.github/workflows/`, `.github/CODEOWNERS`, `.github/rulesets/` |
| A03 System prompt leakage | `AGENTS.md` is public by design; nothing in `CLAUDE.md` or `.claude/settings.json` is secret |
| A04 Vector / embedding weaknesses | n/a — no agent embeddings stored in this repo |
| A05 Cascading failures | `agent-task-validate` rejects out-of-scope PRs early; merge queue isolates failures |
| A06 Confident misleading explanations | Reviewer subagent + 2-person human review on sensitive paths; PR body must include actual vs declared budget |
| A07 System prompt leakage (dup of A03 in 2025 list) | See A03 |
| A08 Agent misalignment / concealment | Audit chain + `Co-Authored-By` agent attribution + sandbox-level write protections on CI directory |
| A09 Self-directed action beyond scope | Per-task `I.files_in_scope` enforced by `check-allowlist.py` in both pre-commit and CI |
| A10 Repudiation | gitsign + audit log + Rekor for every commit |

## Residual risk

- Human bypass of the local pre-commit hook (cannot be cryptographically prevented; mitigated by post-merge `ci-audit-chain.yml` cross-check)
- Compromise of GitHub OIDC issuance (out of our threat model — Microsoft/GitHub supply-chain)
- Supply-chain compromise of an upstream Debian package (mitigated by SBOM + Grype, but ultimately we follow Debian security)
- Compromise of a community catalog key (mitigated by `trust_level` gating and admin policy allowlist)
