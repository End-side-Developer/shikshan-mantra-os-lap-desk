# Runbook — Rotate Signing Keys

Covers: (1) the audit-log HMAC key (OIDC-bound KMS); (2) Debian archive keys mirrored in `config/archives/`. Cosign/gitsign keys are keyless and need no rotation.

## When to rotate

| Class | Cadence | Triggered also by |
|---|---|---|
| Audit-log HMAC | Quarterly | suspected key disclosure, KMS provider migration, change in OIDC-subject-allowed regex |
| Debian archive key | Per Debian's schedule | Debian security announcement |

## A) Audit-log HMAC rotation (OIDC-bound KMS key version)

This is the canonical rotation procedure.

### Preconditions

- You are on `@shikshan/security` AND have KMS-admin rights in the deploying org's cloud account.
- Current chain verifies clean: `python scripts/audit/verify-chain.py --strict`.

### Steps

1. **Create a new KMS key version**
   - AWS KMS example: `aws kms create-key --description "shikshan audit hmac v<N+1>"`
   - Bind its IAM/access policy to the same OIDC subject regex as v<N>.
   - Capture: `kms_key_arn_or_uri`, `version: <N+1>`.

2. **Open a `touches-audit` PR** that updates `docs/audit/keys.json`:
   ```json
   {
     "keys": [
       { "version": 1, "active_from": "...", "active_until": "2026-08-25T00:00:00Z", ... },
       { "version": 2, "active_from": "2026-08-25T00:00:00Z", "active_until": null, ... }
     ]
   }
   ```
   Requires 2 approvals (security + governance).

3. **Append a `key-rotation` audit row** signed under the OLD key (last act of v<N>):
   ```bash
   SHIKSHAN_AUDIT_HMAC_KEY=<v_N_value> \
   python scripts/audit/append-entry.py \
     --actor "human:<your-handle>" --action key-rotation \
     --target docs/audit/keys.json \
     --strict
   ```

4. **Update CI environment**: set `SHIKSHAN_AUDIT_HMAC_KEY` to v<N+1> in the OIDC→KMS workflow step (the workflow file itself is updated in the PR; no secret change needed because keys are issued per-run).

5. **Verify under both keys** (a successful walk proves rotation worked):
   ```bash
   SHIKSHAN_AUDIT_HMAC_KEY_V1=<v_N>   \
   SHIKSHAN_AUDIT_HMAC_KEY_V2=<v_N+1> \
   python scripts/audit/verify-chain.py --strict
   ```

6. **Schedule v<N> retirement**: after `active_until` passes + 30 days grace, remove v<N> from `keys.json` (separate `touches-audit` PR with one approval).

### Emergency rotation (suspected compromise)

- Skip step 6's grace; remove v<N> immediately.
- After step 4, file a P0 security-incident issue.
- Re-verify the chain twice — once before and once after the new key activates.
- Notify downstream consumers via release-notes if any audit-tail bundle signed under v<N> is in circulation.

## B) Debian archive key update

Debian publishes new archive keys through their security announcements list. When that happens:

1. Download the new key file from a trusted Debian mirror.
2. Verify its fingerprint against the Debian announcement (NOT against the file alone).
3. Open a `touches-signing` PR replacing `config/archives/debian.key.chroot`. Requires 2 approvals from `@shikshan/security` + `@shikshan/release-managers`, gpg-signed tag on the PR merge per `policies/sensitive-change-labels.yml`.
4. Reproducibility check (`ci-reproducible.yml`) will fail on the next nightly until both builds use the new key — expected; do not panic-revert.

## C) gitsign / cosign

- These are keyless. There is nothing to rotate locally.
- If the Sigstore root CA rotates (very rare), CI may temporarily fail — see [incident-response.md § signing-failure](../security/incident-response.md#signing-failure-p1).
