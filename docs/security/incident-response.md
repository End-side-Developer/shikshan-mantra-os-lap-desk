# Incident Response Runbook

For internal use by maintainers. For external vulnerability reports, see [SECURITY.md](../../SECURITY.md).

## Trigger types

| Trigger | First responder | Severity floor |
|---|---|---|
| audit chain break | @shikshan/security | P0 |
| protected-path violation | @shikshan/security + @shikshan/governance | P1 |
| signing failure (cosign/gitsign) | @shikshan/security + @shikshan/release-managers | P1 |
| budget exceeded (suspicious pattern) | @shikshan/maintainers | P2 |
| unknown-path attempt | @shikshan/governance | P2 |

Severity escalates one level if the same trigger fires again within 7 days.

## Universal first steps (any trigger)

1. **Open a `security-incident` issue** from `.github/ISSUE_TEMPLATE/security-incident.yml`. This auto-applies labels that block Mergify per `.github/mergify.yml`.
2. **Freeze merges to `main`** — Mergify is already blocked by the label; additionally close any open `automerge`-labeled PRs that touch related paths.
3. **Page the on-call** — see `policies/escalation-matrix.yml#oncall`.
4. **Take a snapshot** of `docs/audit/audit.db` and the latest export under `docs/audit/exports/` to your forensic workstation.

## Per-trigger playbooks

### Audit chain break (P0)

1. Run locally on the snapshot:
   ```bash
   python scripts/audit/verify-chain.py --db /tmp/audit.db.snapshot
   ```
   Note the failing `sequence_number` and the type of break (gap / prev_entry_hash mismatch / entry_hash mismatch / HMAC mismatch).
2. Compare with the latest signed tail bundle: `cosign verify-blob --bundle docs/audit/exports/<latest-tag>.audit-tail.bundle docs/audit/exports/<latest-tag>.audit-tail.txt`. The last known-good `entry_hash` is the rollback target.
3. Determine cause:
   - **Manual edit:** developer bypassed `protected-paths.yml`. Check `git log -p docs/audit/audit.db`. Revert the offending commit; reset the HMAC by appending a `key-rotation` audit row signed under a new key version (`docs/audit/keys.json`).
   - **HMAC key compromise:** rotate the OIDC-bound KMS key immediately per [rotate-signing-key.md](../runbooks/rotate-signing-key.md). Reissue audit rows from rollback target forward.
   - **Genuine tamper:** treat as a confirmed breach. Initiate full credential revocation per [revoke-agent-credential.md](../runbooks/revoke-agent-credential.md) and per-developer GPG/OIDC rotation. File a public security advisory.
4. Post-mortem within 5 business days; ADR if process changes result.

### Protected-path violation (P1)

1. Identify the PR / commit that attempted the edit. The audit row `action: "blocked-protected-path"` records it.
2. Check whether the attempt was malicious or a genuine misconfigured task contract:
   - Malicious → revoke the agent credential, page security.
   - Misconfigured → close the task, file a new task with corrected `I.files_in_scope`; no credential action needed.
3. If the override label was applied (`allowlist-override`), verify the two-team approval was real and not a self-approval. GitHub's PR review history is the source of truth.

### Signing failure (P1)

1. Reproduce locally: `cosign verify-blob --bundle <bundle> <artifact>`.
2. Common causes:
   - Cosign Sigstore root rotation (rare; check sigstore.dev/security/announcements/)
   - Rekor temporary outage (retry after 5min; if persistent, page Sigstore on-call link in escalation matrix)
   - Workflow OIDC subject changed (e.g., repo was renamed) — update `cosign verify --certificate-identity-regexp`
3. Do not relax verification on the consumer side — fix the producer side.

### Budget exceeded (P2)

1. Pull the audit rows for the offending task: `python scripts/audit/export-jsonl.py --since-seq <N>` and grep by `task_id`.
2. Check for runaway tool use (Bash loops, recursive Read, etc.).
3. Patterns to flag for security review:
   - Token spend >2× declared on multiple tasks from the same agent
   - Time spend that exceeds the task type's `absolute_ceiling`
   - Files-changed bursts not explained by the plan
4. If pattern suggests prompt injection, escalate to P1 audit-chain-equivalent procedure.

### Unknown-path attempt (P2)

A path was attempted that is in neither allowlist nor deny list. This usually means the allowlist needs updating, not that something is wrong. Action:
1. Open a `touches-policy` PR adding the path (or its parent glob) to `policies/agent-allowlist.yml`.
2. If the path looks suspicious (e.g., `/etc/shadow`, `/home/...`), treat as P1 protected-path-violation instead.

## Communication

- Internal: post in `#security-incidents` Slack channel (when set up), tag oncall.
- External: only after the incident is contained. Coordinate with @shikshan/governance for any public messaging. For confirmed breaches affecting users, follow the 90-day coordinated-disclosure window from SECURITY.md.

## After every incident

- Add a row to `docs/security/incident-log.md` (created on first incident): date, trigger, severity, root cause, action taken, ADR ID if policy changed.
- If a policy file changed, the change itself goes through `touches-policy` two-team review.
- If an agent credential was revoked, update `AGENT_CARD.md`.
