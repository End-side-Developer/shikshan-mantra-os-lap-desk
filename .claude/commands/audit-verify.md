---
description: Verify the docs/audit/audit.db hash-chained log
allowed-tools: Bash, Read
---

Run the `audit-verify` skill:
```bash
python scripts/audit/verify-chain.py --db docs/audit/audit.db
python scripts/audit/verify-chain.py --since-commit origin/main
```

Report: the highest verified `sequence_number`, total rows, count added since `origin/main`, and verdict (CLEAN / BROKEN). On BROKEN, follow `docs/security/incident-response.md` — do not attempt repair.
