# scripts/audit/

Audit-log writer, verifier, and exporter for [docs/audit/audit.db](../../docs/audit/audit.db).

| Script | Purpose |
|---|---|
| [`append-entry.py`](append-entry.py) | Append a hash-chained, HMAC-signed row. **Only supported writer.** |
| [`verify-chain.py`](verify-chain.py) | Walk the chain and assert integrity (sequence, link, hash, HMAC). |
| [`export-jsonl.py`](export-jsonl.py) | Dump (or incrementally append from `--since-seq`) to a dated JSONL snapshot under `docs/audit/exports/`. |

## Why these scripts live in `policies/protected-paths.yml` `deny:`

Self-modifying auditors are not auditors. Any change to these scripts must be reviewed by two distinct teams (security + governance) per `policies/sensitive-change-labels.yml` `touches-audit`.

## Environment

| Variable | Where set | Purpose |
|---|---|---|
| `SHIKSHAN_AUDIT_HMAC_KEY` | CI step that talks to OIDC→KMS | Active key for new rows |
| `SHIKSHAN_AUDIT_HMAC_KEY_V<n>` | Same as above, for historical key versions | Used by `verify-chain.py` to validate rows signed under rotated keys |
| `SHIKSHAN_AUDIT_DEV_KEY` | Developer shell (per-developer secret) | Local-only signing; CI rejects |
| `CI` / `GITHUB_ACTIONS` | Set automatically in GH Actions | Switches `append-entry.py` into "must have OIDC-bound key" mode |

## Spec

The complete protocol lives at [docs/audit/audit-log-spec.md](../../docs/audit/audit-log-spec.md). When in doubt, that file is canonical.
