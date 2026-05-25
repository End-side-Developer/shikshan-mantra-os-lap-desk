# docs/audit/

Hash-chained audit log for every state-changing action in this repository.

| File | Purpose |
|---|---|
| [audit-log-spec.md](audit-log-spec.md) | Schema, signing, append/verify protocol, threat coverage |
| `audit.db` | SQLite database (created on first append; gitignored placeholder) |
| `exports/` | Periodic JSONL snapshots — immutable, append-only per allowlist |
| `keys.json` | Public key version table (HMAC key versions, not the keys themselves) |

## Operating

```bash
# Append (normally called via .claude/hooks/post-tool-use/audit-append.sh)
python scripts/audit/append-entry.py \
  --actor agent:claude-code --action edit \
  --target config/hooks/live/0010-locale.hook.chroot \
  --diff-file /tmp/diff.patch --task-id SMO-0042

# Verify the whole chain
python scripts/audit/verify-chain.py --db docs/audit/audit.db

# Verify only rows added since main
python scripts/audit/verify-chain.py --since-commit origin/main

# Export JSONL snapshot for offline review
python scripts/audit/export-jsonl.py --out docs/audit/exports/$(date -u +%F).jsonl
```

## Why this file is so locked down

- `audit.db` is in `policies/protected-paths.yml` `deny:` — direct edits are aborted.
- `.gitattributes` marks it `binary -diff -merge` — git refuses to merge concurrent changes silently.
- `scripts/audit/**` is also in `deny:` — the auditor cannot rewrite itself.
- See [audit-log-spec.md § Recovery](audit-log-spec.md#recovery) for what to do if a verification fails.
