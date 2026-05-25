#!/usr/bin/env python3
"""Append a hash-chained, HMAC-signed row to docs/audit/audit.db.

See docs/audit/audit-log-spec.md for the full protocol. This script is the
ONLY supported writer for audit.db. Direct edits are blocked by
policies/protected-paths.yml.

Exit codes:
    0  success
    1  CLI usage error
    2  DB locked or schema mismatch
    3  HMAC key unavailable or signing failed
    4  prior-row inconsistency detected (refuse to append on a broken chain)
"""
from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

GENESIS = "GENESIS"
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_DB = REPO_ROOT / "docs" / "audit" / "audit.db"

SCHEMA_SQL = """
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
  key_version      INTEGER NOT NULL,
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
"""

VALID_ACTIONS = {
    "edit", "write", "delete", "commit", "merge", "release",
    "override", "blocked-protected-path", "budget-exceeded",
    "audit-incident", "key-rotation",
}


def _canonical_json(d: dict) -> bytes:
    """Sorted-keys, no-whitespace, UTF-8 canonical JSON for hashing."""
    return json.dumps(d, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _sha256_hex(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _load_keys(repo_root: Path) -> dict:
    keys_file = repo_root / "docs" / "audit" / "keys.json"
    with keys_file.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def _resolve_hmac_key(keys: dict, strict: bool) -> tuple[int, bytes]:
    """Resolve the HMAC key for signing the next row.

    Production: ask cloud KMS via OIDC. We can't call KMS from this stub, so:
    - CI (env CI=true or GITHUB_ACTIONS=true): MUST have SHIKSHAN_AUDIT_HMAC_KEY env
      delivered by the OIDC-bound KMS step in the workflow.
    - Local-dev: fall back to SHIKSHAN_AUDIT_DEV_KEY env (must be present;
      typically a per-developer secret stored outside the repo).

    Returns: (key_version, key_bytes)
    """
    active = [k for k in keys["keys"] if k.get("active_until") is None]
    if not active:
        raise RuntimeError("no active HMAC key version in docs/audit/keys.json")
    key_version = max(k["version"] for k in active)

    in_ci = os.environ.get("CI") == "true" or os.environ.get("GITHUB_ACTIONS") == "true"
    if in_ci:
        raw = os.environ.get("SHIKSHAN_AUDIT_HMAC_KEY")
        if not raw:
            raise RuntimeError("CI run but SHIKSHAN_AUDIT_HMAC_KEY env not set (OIDC→KMS step missing)")
        return key_version, raw.encode("utf-8")

    if strict:
        raise RuntimeError("--strict requires CI-issued OIDC-bound HMAC key; refusing in dev mode")

    raw = os.environ.get("SHIKSHAN_AUDIT_DEV_KEY")
    if not raw:
        # Last-resort dev fallback: deterministic-but-warned key. This is INSECURE
        # and only acceptable for first-time local bootstrap before any real
        # commits exist. CI rejects rows signed under this key.
        print(
            "[audit] WARNING: no SHIKSHAN_AUDIT_DEV_KEY set; using insecure dev fallback. "
            "Set the env var to a per-developer secret. CI will reject rows signed by this key.",
            file=sys.stderr,
        )
        raw = "INSECURE-DEV-FALLBACK-DO-NOT-USE-IN-CI"
    return key_version, raw.encode("utf-8")


def _open_db(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path), timeout=30.0, isolation_level="IMMEDIATE")
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.executescript(SCHEMA_SQL)
    return conn


def _previous(conn: sqlite3.Connection) -> tuple[int, str]:
    cur = conn.execute(
        "SELECT sequence_number, entry_hash FROM audit_entries "
        "ORDER BY sequence_number DESC LIMIT 1"
    )
    row = cur.fetchone()
    if row is None:
        return 0, GENESIS
    return int(row[0]), str(row[1])


def _hash_diff(diff_file: Path | None) -> str:
    if diff_file is None:
        return _sha256_hex(b"")
    if not diff_file.exists():
        raise FileNotFoundError(f"--diff-file does not exist: {diff_file}")
    h = hashlib.sha256()
    with diff_file.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="Append a row to the audit log")
    ap.add_argument("--db", type=Path, default=DEFAULT_DB)
    ap.add_argument("--actor", required=True,
                    help="agent:<id> or human:<gh-handle>")
    ap.add_argument("--actor-oidc-sub", default=None)
    ap.add_argument("--action", required=True, choices=sorted(VALID_ACTIONS))
    ap.add_argument("--target", required=True, help="repo-relative POSIX path")
    ap.add_argument("--diff-file", type=Path, default=None,
                    help="file containing the unified diff (sha256'd)")
    ap.add_argument("--task-id", default=None)
    ap.add_argument("--pr-number", type=int, default=None)
    ap.add_argument("--commit-sha", default=None)
    ap.add_argument("--strict", action="store_true",
                    help="Require OIDC-bound KMS key; refuse dev fallback")
    args = ap.parse_args(argv)

    if not (args.actor.startswith("agent:") or args.actor.startswith("human:")):
        print("[audit] --actor must start with 'agent:' or 'human:'", file=sys.stderr)
        return 1

    try:
        keys = _load_keys(REPO_ROOT)
        key_version, key_bytes = _resolve_hmac_key(keys, strict=args.strict)
    except Exception as exc:
        print(f"[audit] key resolution failed: {exc}", file=sys.stderr)
        return 3

    try:
        conn = _open_db(args.db)
    except sqlite3.Error as exc:
        print(f"[audit] DB open failed: {exc}", file=sys.stderr)
        return 2

    try:
        prev_seq, prev_hash = _previous(conn)
        diff_sha = _hash_diff(args.diff_file)

        row = {
            "sequence_number": prev_seq + 1,
            "ts_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "actor": args.actor,
            "actor_oidc_sub": args.actor_oidc_sub,
            "action": args.action,
            "target_path": args.target,
            "diff_sha256": diff_sha,
            "task_id": args.task_id,
            "pr_number": args.pr_number,
            "commit_sha": args.commit_sha,
            "key_version": key_version,
            "prev_entry_hash": prev_hash,
        }
        entry_hash = _sha256_hex(_canonical_json(row))
        row_hmac = hmac.new(key_bytes, entry_hash.encode("utf-8"), hashlib.sha256).hexdigest()

        conn.execute(
            """INSERT INTO audit_entries (
                ts_utc, actor, actor_oidc_sub, action, target_path,
                diff_sha256, task_id, pr_number, commit_sha,
                key_version, prev_entry_hash, entry_hash, hmac
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                row["ts_utc"], row["actor"], row["actor_oidc_sub"],
                row["action"], row["target_path"], row["diff_sha256"],
                row["task_id"], row["pr_number"], row["commit_sha"],
                row["key_version"], row["prev_entry_hash"], entry_hash, row_hmac,
            ),
        )
        conn.commit()
        print(f"[audit] appended #{row['sequence_number']} {row['action']} {row['target_path']}")
        return 0
    except sqlite3.IntegrityError as exc:
        print(f"[audit] integrity error (append-only trigger?): {exc}", file=sys.stderr)
        return 4
    except Exception as exc:  # noqa: BLE001
        print(f"[audit] append failed: {exc}", file=sys.stderr)
        return 2
    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
