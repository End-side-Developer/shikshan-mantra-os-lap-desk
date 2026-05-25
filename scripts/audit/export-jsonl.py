#!/usr/bin/env python3
"""Export docs/audit/audit.db to a dated JSONL snapshot.

The output is immutable (policies/agent-allowlist.yml append_only:) and
committed alongside the chain. Useful for offline review, long-term
archival, and feeding downstream consumers (Splunk, Loki, etc.).

Exit codes:
    0  success
    1  CLI usage error
    2  DB open / read error
    3  write error
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_DB = REPO_ROOT / "docs" / "audit" / "audit.db"
DEFAULT_OUT_DIR = REPO_ROOT / "docs" / "audit" / "exports"


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="Export audit.db to JSONL")
    ap.add_argument("--db", type=Path, default=DEFAULT_DB)
    ap.add_argument("--out", type=Path, default=None,
                    help="Output file path; default: docs/audit/exports/YYYY-MM-DD.jsonl")
    ap.add_argument("--since-seq", type=int, default=0,
                    help="Only export rows with sequence_number > this value")
    args = ap.parse_args(argv)

    if not args.db.exists():
        print(f"[export] no DB at {args.db}; nothing to export", file=sys.stderr)
        return 0

    out = args.out or (DEFAULT_OUT_DIR / f"{datetime.now(timezone.utc).strftime('%Y-%m-%d')}.jsonl")
    out.parent.mkdir(parents=True, exist_ok=True)
    if out.exists():
        print(f"[export] refusing to overwrite existing file {out}; "
              "exports are append-only — pick a new --out path",
              file=sys.stderr)
        return 1

    try:
        conn = sqlite3.connect(f"file:{args.db}?mode=ro", uri=True)
        rows = conn.execute(
            "SELECT sequence_number, ts_utc, actor, actor_oidc_sub, action, "
            "target_path, diff_sha256, task_id, pr_number, commit_sha, "
            "key_version, prev_entry_hash, entry_hash, hmac "
            "FROM audit_entries WHERE sequence_number > ? "
            "ORDER BY sequence_number ASC",
            (args.since_seq,),
        )
        n = 0
        with out.open("w", encoding="utf-8") as fh:
            for row in rows:
                entry = {
                    "sequence_number": row[0],
                    "ts_utc": row[1],
                    "actor": row[2],
                    "actor_oidc_sub": row[3],
                    "action": row[4],
                    "target_path": row[5],
                    "diff_sha256": row[6],
                    "task_id": row[7],
                    "pr_number": row[8],
                    "commit_sha": row[9],
                    "key_version": row[10],
                    "prev_entry_hash": row[11],
                    "entry_hash": row[12],
                    "hmac": row[13],
                }
                fh.write(json.dumps(entry, sort_keys=True, separators=(",", ":"), ensure_ascii=False))
                fh.write("\n")
                n += 1
        conn.close()
        print(f"[export] wrote {n} row(s) to {out}")
        return 0
    except sqlite3.Error as exc:
        print(f"[export] DB error: {exc}", file=sys.stderr)
        return 2
    except OSError as exc:
        print(f"[export] write error: {exc}", file=sys.stderr)
        return 3


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
