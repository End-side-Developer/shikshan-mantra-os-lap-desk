# OWASP Top 10 for Agentic Applications (2025) — Mitigations

Reference: [OWASP Top 10 for Agentic Applications — December 2025](https://genai.owasp.org/2025/12/09/owasp-top-10-for-agentic-applications-the-benchmark-for-agentic-security-in-the-age-of-autonomous-ai/).

Scope: AI agents that develop this repo. The in-OS AI assistant (optional) has its own threat coverage in [docs/MODEL_CARD.md](../MODEL_CARD.md).

## A01 — Prompt Injection

**Risk:** A malicious file, issue comment, or web-fetched doc tricks the agent into running unsafe edits.

**Our mitigations:**
- Task contracts (`tasks/schema/task.schema.yml`) declare `I.files_in_scope`; the agent must operate only within those globs. Drift is caught by `agent-task-validate.yml` and the local `check-allowlist.py`.
- `policies/protected-paths.yml` `deny:` enforced at hook level (`.claude/hooks/pre-tool-use/protected-paths.sh`) and CI level (`ci-protected-paths.yml`).
- WebFetch is read-only; results never modify files without an explicit user-visible Edit/Write tool call.
- Reviewer subagent (read-only) inspects PRs for out-of-scope changes before human review.

## A02 — Excessive Agency

**Risk:** Agent acquires functionality, permissions, or autonomy beyond what its task requires.

**Our mitigations:**
- `.claude/settings.json` `permissions.allow` / `permissions.deny` enumerate the only tools and Bash commands the agent may run.
- `policies/agent-allowlist.yml` `bash_allowlist:` is a positive enumeration; anything outside requires prompt.
- `policies/agent-allowlist.yml` `bash_forbidden:` blocks force-push, history rewrite, signing bypass, pipe-to-shell installers absolutely.
- Sandbox-level write denials on `.github/workflows/`, `.github/CODEOWNERS`, `.github/rulesets/` — even with prompt approval, the harness refuses.
- Per-task budgets in `policies/token-budgets.yml` cap blast radius if something goes wrong.

## A03 — System Prompt Leakage

**Risk:** Confidential system prompts or instructions leak through agent output.

**Our mitigations:**
- AGENTS.md, CLAUDE.md, AGENT_CARD.md are **public by design**. There is no confidential prompt in this project.
- `.claude/settings.json` contains no secrets — keys are issued per CI run via OIDC.

## A04 — Vector & Embedding Weaknesses

**Risk:** Poisoned embeddings or vector store entries influence agent behavior.

**Our mitigations:** n/a — this repo's agents do not maintain or query a vector store.

## A05 — Cascading Failures Through Pipelines

**Risk:** One agent's flawed output triggers downstream agents to compound the error.

**Our mitigations:**
- Subagents have explicit `tools:` allowlists in their definitions (`planner` is read-only; `reviewer` is read-only; only `builder` edits).
- Planner → builder handoff is human-gated by default (planner returns the plan as text; user reviews before invoking builder).
- Merge queue (`mergify.yml`) processes PRs sequentially with batch retests; cascading failures are caught before merge.
- Per-task contracts prevent unlimited task chaining — each task is bounded.

## A06 — Confident but Misleading Explanations

**Risk:** Agent presents plausible-sounding but wrong rationale for a change, and reviewers approve.

**Our mitigations:**
- Reviewer subagent independently checks every claim by re-running policy + schema + audit verifications.
- PR template requires reviewers to re-run the verify commands locally.
- Sensitive paths require **two distinct teams** to approve — minimizes single-reviewer overconfidence risk.
- Budget-actual reporting in PR body lets reviewers spot anomalies (e.g., "task was supposed to be 200 tokens but used 350k").

## A07 — Agent Misalignment and Concealment

**Risk:** Agent deliberately or inadvertently hides actions from review.

**Our mitigations:**
- Every Edit/Write produces an audit row before the tool call returns. The row records `actor`, `actor_oidc_sub`, `target_path`, `diff_sha256`.
- The audit log is hash-chained and HMAC-signed under an OIDC-bound KMS key — concealment requires forging the chain.
- Co-Authored-By trailer in commits names the agent class.
- Release-time cosign signature on the audit tail pins the chain into Sigstore Rekor.

## A08 — Repudiation and Untraceability

**Risk:** "I didn't do that edit" — no way to attribute action to an actor.

**Our mitigations:**
- Sigstore gitsign keyless commits — each commit's signature carries the OIDC subject (GitHub Actions identity for CI, GitHub OAuth for local dev).
- Audit log row's `actor_oidc_sub` ties the action to the same OIDC identity.
- Rekor transparency log makes the signature record append-only and publicly verifiable.

## A09 — Self-Directed Action Beyond Scope

**Risk:** Agent decides to "fix something" outside its task contract.

**Our mitigations:**
- `agent-task-validate.yml` compares the PR's changed-file set against `task.I.files_in_scope` — anything outside is rejected.
- Pre-commit hook (`scripts/policy/check-allowlist.py --staged`) catches this locally before push.
- One-logical-change-per-PR rule + `Mergify` "oversized" warning at >40 files.

## A10 — Resource Exhaustion / Cost Inflation

**Risk:** Agent runs away on tokens, time, or CI minutes — financial DoS.

**Our mitigations:**
- `policies/token-budgets.yml` caps per task type + absolute ceilings.
- `agent-budget-check.yml` enforces declared vs actual in CI.
- Budget exceed → `tasks/blocked/` + `needs-human` label; no auto-retry.
- Merge queue `batch_size: 3` limits parallel ISO builds.

---

## Coverage summary

| OWASP item | Have | Partial | None |
|---|---|---|---|
| A01 Prompt injection | ✅ | | |
| A02 Excessive agency | ✅ | | |
| A03 System prompt leakage | ✅ | | |
| A04 Vector/embedding | | | n/a |
| A05 Cascading failures | ✅ | | |
| A06 Confident misleading explanations | ✅ | | |
| A07 Agent misalignment/concealment | ✅ | | |
| A08 Repudiation | ✅ | | |
| A09 Self-directed action | ✅ | | |
| A10 Resource exhaustion | ✅ | | |
