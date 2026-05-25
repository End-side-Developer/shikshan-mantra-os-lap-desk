# Audit Log Specification

## Purpose

Every state-changing action by any agent or human in this repository must produce a tamper-evident record. The audit log answers:

- **Who** performed an action (agent OIDC subject or human GitHub handle)
- **What** changed (path, action, diff hash)
- **When** (RFC3339 UTC timestamp + monotonic sequence number)
- **Why** (linked task / PR / commit)
- **Integrity** (each row hash-linked to the previous; HMAC over the row)

## Storage

**File:** [docs/audit/audit.db](audit.db) (SQLite ≥ 3.45)

**Why SQLite (ADR-0002):**
- Append-only enforced at the DB layer via triggers
- Concurrent-write safe (WAL mode)
- Indexed verification (orders of magnitude faster than walking JSONL)
- No external infrastructure for a greenfield repo
- Small binary footprint; periodic JSONL export keeps human review easy

**Exports:** Periodic JSONL snapshots at `docs/audit/exports/YYYY-MM-DD.jsonl` for offline review and long-term archival. Exports are in [policies/agent-allowlist.yml](../../policies/agent-allowlist.yml) `append_only:`.

## Schema

```sql
CREATE TABLE IF NOT EXISTS audit_entries (
  sequence_number  INTEGER PRIMARY KEY AUTOINCREMENT,
  ts_utc           TEXT    NOT NULL,
  actor            TEXT    NOT NULL,
  actor_oidc_sub   TEXT,
  action           TEXT    NOT NULL,
  target_path      TEXT    NOT NULL,
  diff_sha256      TEXT    NOT NULL,
  task_id          TEXT,
  pr_number        INTEGER,
  commit_sha       TEXT,
  prev_entry_hash  TEXT    NOT NULL,
  entry_hash       TEXT    NOT NULL,
  hmac             TEXT    NOT NULL
);

CREATE TRIGGER IF NOT EXISTS no_update
  BEFORE UPDATE ON audit_entries
  BEGIN SELECT RAISE(ABORT, 'audit_entries is append-only'); END;

CREATE TRIGGER IF NOT EXISTS no_delete
  BEFORE DELETE ON audit_entries
  BEGIN SELECT RAISE(ABORT, 'audit_entries is append-only'); END;

CREATE INDEX IF NOT EXISTS idx_audit_target ON audit_entries(target_path);
CREATE INDEX IF NOT EXISTS idx_audit_actor  ON audit_entries(actor);
CREATE INDEX IF NOT EXISTS idx_audit_task   ON audit_entries(task_id);
CREATE INDEX IF NOT EXISTS idx_audit_pr     ON audit_entries(pr_number);
```

### Field semantics

| Field | Format | Notes |
|---|---|---|
| `sequence_number` | autoincrement INT | Strictly monotonic; gap = chain break |
| `ts_utc` | RFC3339 with `Z` suffix | e.g., `2026-05-25T14:23:01Z` |
| `actor` | `agent:<id>` \| `human:<gh-handle>` | E.g., `agent:claude-code`, `human:alice` |
| `actor_oidc_sub` | string \| NULL | Sigstore OIDC `sub` claim when available |
| `action` | enum | `edit`, `write`, `delete`, `commit`, `merge`, `release`, `override`, `blocked-protected-path`, `budget-exceeded`, `audit-incident` |
| `target_path` | repo-relative POSIX path | e.g., `config/hooks/live/0010-locale.hook.chroot` |
| `diff_sha256` | hex(64) | SHA-256 of the unified diff text (empty diff → `e3b0c4...b855`) |
| `task_id` | `SMO-NNNN` \| NULL | From task contract |
| `pr_number` | INT \| NULL | When attributable |
| `commit_sha` | hex(40) \| NULL | When attributable |
| `prev_entry_hash` | hex(64) | `GENESIS` for row 1 |
| `entry_hash` | hex(64) | `sha256(canonical_json(row_without_entry_hash_and_hmac))` |
| `hmac` | hex(64) | `HMAC-SHA256(entry_hash, key)` |

### Canonical JSON for hashing

Sort keys; UTF-8; no whitespace; numbers in decimal; booleans `true`/`false`; nulls `null`. Use [scripts/audit/append-entry.py](../../scripts/audit/append-entry.py) `_canonical_json()` as the reference implementation.

## HMAC key custody

- **Never stored in the repository.**
- Issued **per CI run** via GitHub OIDC → cloud KMS (KMS provider chosen by the deploying org; production default: AWS KMS with key policy restricting `kms:Sign` to GitHub OIDC subject `repo:shikshan-mantra/shikshan-mantra-os:ref:refs/heads/*`).
- Local-developer runs use a developer-bound key released to OIDC subject matching their GitHub OAuth token; verified by `verify-chain.py --strict` only in CI.
- Key rotation: quarterly; per [docs/runbooks/rotate-signing-key.md](../runbooks/rotate-signing-key.md).
- A rotation event appends a row with `action: "key-rotation"` and `target_path: "docs/audit/audit.db"`; the new key signs that row and all subsequent rows. `verify-chain.py` handles multi-key verification by maintaining a key version table out-of-band (`docs/audit/keys.json` — public key versions only).

## Release-time tail signing

On every `vX.Y.Z` tag, `release-cosign-sign.yml` runs:

```bash
TAIL_HASH=$(sqlite3 docs/audit/audit.db "SELECT entry_hash FROM audit_entries ORDER BY sequence_number DESC LIMIT 1;")
echo "$TAIL_HASH" > /tmp/audit-tail.txt
cosign sign-blob --bundle docs/audit/exports/${TAG}.audit-tail.bundle /tmp/audit-tail.txt
```

Verification at any future point:

```bash
cosign verify-blob \
  --bundle docs/audit/exports/${TAG}.audit-tail.bundle \
  --certificate-identity-regexp '^https://github.com/shikshan-mantra/.+' \
  --certificate-oidc-issuer 'https://token.actions.githubusercontent.com' \
  /tmp/audit-tail.txt
```

## Append protocol

1. Agent/human triggers an Edit/Write/Delete tool call.
2. Post-tool-use hook ([.claude/hooks/post-tool-use/audit-append.sh](../../.claude/hooks/post-tool-use/audit-append.sh)) runs:
   ```bash
   python scripts/audit/append-entry.py \
     --actor "$AGENT_ID" \
     --action "$ACTION" \
     --target "$TARGET_PATH" \
     --diff-file "$DIFF_FILE" \
     --task-id "$TASK_ID"
   ```
3. `append-entry.py`:
   1. Opens audit.db in WAL mode, takes advisory lock.
   2. Selects `MAX(sequence_number)` and the prior row's `entry_hash`.
   3. Computes `diff_sha256 = sha256(diff_file)`.
   4. Assembles the row dict, canonical-JSONs it, hashes → `entry_hash`.
   5. Signs `entry_hash` via OIDC-bound KMS → `hmac`.
   6. Inserts row. Commits. Releases lock.
   7. On any error: prints to stderr, exits non-zero (the hook then aborts the tool call's side-effect by reverting).

## Verification protocol

`verify-chain.py` walks rows in `sequence_number` order, asserting:
- `prev_entry_hash` of row N equals `entry_hash` of row N-1 (with `GENESIS` for row 1)
- Recomputed `entry_hash` matches stored value
- HMAC verifies against the key version active at `ts_utc` (per `docs/audit/keys.json`)
- No gaps in `sequence_number`

`--since-commit <sha>` mode restricts the walk to rows added by commits not in `<sha>`'s ancestry (useful for PR review).

`--strict` mode additionally requires OIDC-bound KMS signing (CI only — fails on developer-bound keys).

## CI integration

- `ci-audit-chain.yml` runs `verify-chain.py --strict` on every PR touching `docs/audit/**`.
- `release-cosign-sign.yml` signs the tail hash and bundles the signature.
- A nightly workflow (`cron-audit-monthly-export.yml`, in Phase 7) exports a fresh JSONL snapshot and opens a PR with the new export.

## Recovery

If `verify-chain.py` reports a break:
1. Stop all merges to `main` (label `security-incident` blocks Mergify per `.github/mergify.yml`).
2. Open security incident issue from template.
3. Walk forensic checklist in [docs/security/incident-response.md](../security/incident-response.md).
4. Determine: was the break a benign developer mistake (e.g., manual DB edit) or a malicious tamper? Manual edits to `audit.db` are blocked by `protected-paths.yml` + git filter (`-diff -merge`), so the suspicious-by-default assumption holds.
5. If malicious: rotate HMAC key, revoke agent credentials per [docs/runbooks/revoke-agent-credential.md](../runbooks/revoke-agent-credential.md), and back-walk to the last verified-good `entry_hash` (latest signed tail-bundle).

## Threat coverage

- **Tampering with rows:** detected by HMAC mismatch.
- **Reordering rows:** detected by `prev_entry_hash` mismatch.
- **Deletion of rows:** detected by `sequence_number` gap.
- **Forged key:** mitigated by OIDC-bound KMS — agent never holds the raw key; impersonation requires compromising GitHub OIDC issuance.
- **Replay across keys:** key version table records active range per key; an HMAC computed under key vN cannot replay as key vN+1.
- **DB substitution attack:** release-time tail-signing pins the last `entry_hash` into a cosign bundle; substituting the entire DB at a future date would require a Sigstore certificate from the original tag-time OIDC subject (rotated tokens).

## Non-goals (and why)

- **No row-level encryption.** Audit data is intended to be reviewable; integrity, not confidentiality, is the property we need.
- **No external log shipper (e.g., Splunk, Loki) in v1.** Adding one is fine via a downstream consumer of the JSONL exports; not part of the core spec.
- **No append from human-only commits without the hook.** Humans who bypass the local pre-commit hook will have their commits' edits not recorded. The post-merge `ci-audit-chain.yml` cross-references commit diffs against rows added in the PR; gaps trigger `audit-incident`. The mitigation is procedural (CONTRIBUTING.md mandates the hook), not cryptographic — humans can always Git-bypass; the system's strength is the deterrent + post-hoc detection.
