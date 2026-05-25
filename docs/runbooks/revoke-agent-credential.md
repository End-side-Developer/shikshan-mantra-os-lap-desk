# Runbook — Revoke an Agent Credential

Used when an AI agent is suspected of compromise, misconfiguration, or sustained policy violation. Covers `claude-code`, `copilot`, and any future entry in [AGENT_CARD.md](../../AGENT_CARD.md).

## Authority

- Triggered by: `@shikshan/security` OR `@shikshan/governance`.
- Approved by: both, before the revocation is final.
- Logged in: `docs/audit/audit.db` (`action: "override"` for the AGENT_CARD edit; `action: "audit-incident"` for the trigger).

## Pre-revocation

1. **Freeze** — apply label `agent-frozen:<agent-id>` to all open PRs from that agent's branches (`agent/SMO-*` if it's claude-code; route-by-author for copilot). Mergify refuses queue entry on that label.
2. **Snapshot** — `python scripts/audit/export-jsonl.py --out docs/audit/exports/incident-$(date -u +%FT%TZ).jsonl`. Move the snapshot to forensic workstation.
3. **Open** the `security-incident` issue from the template; tick "trigger: other" with a free-text description.

## Revocation steps

### claude-code

1. **Revoke at the harness** — in the deploying org's Claude Code configuration, remove the agent's OIDC identity from any service account that signs CI commits. (For local-dev Claude Code, no action needed — the developer's OAuth + gitsign already attributes the human.)
2. **Update `AGENT_CARD.md`** — open a `touches-policy` PR moving the `claude-code` row to a new section "Revoked agents" with the date and reason. Requires governance + security approval.
3. **Update `.claude/settings.json`** — open a `touches-policy` PR; under `permissions.deny`, add `Edit(*)`, `Write(*)`, `Bash(*)`. Once merged, the harness refuses all tool calls from this agent class until the row is restored.
4. **Verify** — open a no-op PR and confirm any attempted edit is denied at the hook level.

### copilot

1. **Disable Copilot for the repository** in GitHub repo settings → Integrations.
2. **Update `AGENT_CARD.md`** as above.
3. **Update `.github/copilot-instructions.md`** to a single line: "Copilot is revoked for this repo as of YYYY-MM-DD; see AGENT_CARD.md."
4. Optionally rotate Copilot policy via `gh api`.

### human (rare)

If a human contributor must be removed:
1. Revoke org membership / repo write per the org's HR process.
2. Their past commits remain (signed and audited); they are not retroactively repudiated.
3. Update CODEOWNERS to remove the handle.

## Reinstatement

A revoked agent class returns only via:
- New ADR justifying the reinstatement and listing remediations (e.g., updated `policies/protected-paths.yml`, tightened budget caps)
- `touches-policy` PR with 2 approvals from governance + security
- A 30-day probation tracking dashboard (issue with weekly checkins)

## Post-revocation hygiene

- Audit-log review: walk `docs/audit/audit.db` for the 30 days prior, looking for the pattern that led to revocation. Document findings in `docs/security/incident-log.md`.
- Policy review: did `policies/protected-paths.yml` or `policies/agent-allowlist.yml` need to be tightened? Open a follow-up.
- Public communication: if the revocation followed a confirmed breach affecting users, follow the 90-day coordinated disclosure window per [SECURITY.md](../../SECURITY.md).
