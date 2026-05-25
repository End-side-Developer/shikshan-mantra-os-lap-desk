---
name: audit-verify
description: Walk the docs/audit/audit.db hash-chained log and verify integrity. Use when an audit failure is reported, before pushing a branch, or when a maintainer asks "is the chain clean?".
---

# Skill: audit-verify

## When to use
- Pre-push (already wired as a `.pre-commit-config.yaml` pre-push hook)
- After a suspected force-push attempt
- Before tagging a release
- When `ci-audit-chain` fails on a PR

## Steps

1. **Full chain walk**
   ```bash
   python scripts/audit/verify-chain.py --db docs/audit/audit.db
   ```
   Exit 0 means clean.

2. **PR-scoped walk** (only rows added since main)
   ```bash
   python scripts/audit/verify-chain.py --since-commit origin/main
   ```

3. **CI-strict mode** (requires OIDC-bound HMAC key in env)
   ```bash
   SHIKSHAN_AUDIT_HMAC_KEY=<from-OIDC-KMS-step> \
   python scripts/audit/verify-chain.py --strict
   ```

## What to do if it fails

The script names the failing row. Stop everything and:

1. Apply label `security-incident` to any open PRs touching `docs/audit/**` — this blocks Mergify per `.github/mergify.yml`.
2. Open the security-incident issue from `.github/ISSUE_TEMPLATE/security-incident.yml`.
3. Walk `docs/security/incident-response.md`.
4. Do NOT attempt to "fix" the row by editing — that is itself a violation.

## Reference
- Full spec: [docs/audit/audit-log-spec.md](../../../docs/audit/audit-log-spec.md)
- Append script: [scripts/audit/append-entry.py](../../../scripts/audit/append-entry.py)
- Verify script: [scripts/audit/verify-chain.py](../../../scripts/audit/verify-chain.py)
