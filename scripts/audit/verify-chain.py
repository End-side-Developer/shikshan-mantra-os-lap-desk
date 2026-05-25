#!/usr/bin/env python3
"""Verify the integrity of the hash-chained audit log.

Walks docs/audit/audit.db in sequence_number order and asserts:
  - sequence_number is gap-free
  - prev_entry_hash of row N == entry_hash of row N-1 (GENESIS for row 1)
  - entry_hash recomputes to the stored value
  - HMAC verifies under the key version active at row's ts_utc

See docs/audit/audit-log-spec.md.

Exit codes:
    0  chain verifies clean
    1  CLI usage error
    2  DB open / schema error
    3  HMAC key unavailable
    4  chain break detected (details on stderr)
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


def _canonical_json(d: dict) -> bytes:
    return json.dumps(d, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _sha256_hex(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _parse_iso(ts: str) -> datetime:
    return datetime.strptime(ts, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)


def _load_keys(repo_root: Path) -> dict:
    with (repo_root / "docs" / "audit" / "keys.json").open("r", encoding="utf-8") as fh:
        return json.load(fh)


def _key_bytes_for_version(keys: dict, version: int, strict: bool) -> bytes:
    in_ci = os.environ.get("CI") == "true" or os.environ.get("GITHUB_ACTIONS") == "true"
    env_var = f"SHIKSHAN_AUDIT_HMAC_KEY_V{version}"
    raw = os.environ.get(env_var)
    if raw:
        return raw.encode("utf-8")
    # Convention: latest active version may also live in SHIKSHAN_AUDIT_HMAC_KEY
    active_latest = max((k["version"] for k in keys["keys"] if k.get("active_until") is None), default=None)
    if version == active_latest:
        raw = os.environ.get("SHIKSHAN_AUDIT_HMAC_KEY")
        if raw:
            return raw.encode("utf-8")
    if strict:
        raise RuntimeError(f"--strict requires {env_var} to be set (OIDC→KMS)")
    if in_ci:
        raise RuntimeError(f"CI run requires {env_var}; OIDC→KMS step missing")
    dev = os.environ.get("SHIKSHAN_AUDIT_DEV_KEY")
    if dev:
        return dev.encode("utf-8")
    return b"INSECURE-DEV-FALLBACK-DO-NOT-USE-IN-CI"


def _resolve_pr_commits(repo_root: Path, since: str) -> set[str] | None:
    """Return the set of commit SHAs added since `since` ref, or None on failure."""
    import subprocess
    try:
        out = subprocess.run(
            ["git", "rev-list", f"{since}..HEAD"],
            cwd=str(repo_root), capture_output=True, text=True, check=True,
        )
        return {line.strip() for line in out.stdout.splitlines() if line.strip()}
    except Exception:
        return None


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="Verify audit-log chain integrity")
    ap.add_argument("--db", type=Path, default=DEFAULT_DB)
    ap.add_argument("--strict", action="store_true",
                    help="Require OIDC-bound KMS keys; reject dev-fallback rows")
    ap.add_argument("--since-commit", default=None,
                    help="Only verify rows whose commit_sha is in `git rev-list <since>..HEAD`")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args(argv)

    if not args.db.exists():
        # Empty repo case: nothing to verify is OK.
        if not args.quiet:
            print(f"[audit] no DB at {args.db}; treating as empty (OK)")
        return 0

    try:
        keys = _load_keys(REPO_ROOT)
    except FileNotFoundError as exc:
        print(f"[audit] keys.json missing: {exc}", file=sys.stderr)
        return 3

    try:
        conn = sqlite3.connect(f"file:{args.db}?mode=ro", uri=True)
    except sqlite3.Error as exc:
        print(f"[audit] DB open failed: {exc}", file=sys.stderr)
        return 2

    target_shas: set[str] | None = None
    if args.since_commit:
        target_shas = _resolve_pr_commits(REPO_ROOT, args.since_commit)
        if target_shas is None:
            print(f"[audit] could not resolve commits since {args.since_commit}", file=sys.stderr)
            return 1

    try:
        rows = conn.execute(
            "SELECT sequence_number, ts_utc, actor, actor_oidc_sub, action, "
            "target_path, diff_sha256, task_id, pr_number, commit_sha, "
            "key_version, prev_entry_hash, entry_hash, hmac "
            "FROM audit_entries ORDER BY sequence_number ASC"
        ).fetchall()
    except sqlite3.Error as exc:
        print(f"[audit] DB read failed: {exc}", file=sys.stderr)
        return 2
    finally:
        conn.close()

    expected_prev = GENESIS
    expected_seq = 1
    verified = 0
    skipped = 0

    for row in rows:
        (seq, ts_utc, actor, oidc_sub, action, target_path, diff_sha256,
         task_id, pr_number, commit_sha, key_version, prev_hash, stored_entry, stored_hmac) = row

        if seq != expected_seq:
            print(f"[audit] CHAIN BREAK: sequence gap at row {seq} (expected {expected_seq})",
                  file=sys.stderr)
            return 4
        if prev_hash != expected_prev:
            print(f"[audit] CHAIN BREAK: prev_entry_hash mismatch at row {seq}", file=sys.stderr)
            return 4

        # Skip if filtering by --since-commit and this row isn't in scope
        if target_shas is not None and (commit_sha is None or commit_sha not in target_shas):
            # Still advance the chain expectations
            expected_prev = stored_entry
            expected_seq = seq + 1
            skipped += 1
            continue

        # Recompute entry_hash
        row_for_hash = {
            "sequence_number": seq,
            "ts_utc": ts_utc,
            "actor": actor,
            "actor_oidc_sub": oidc_sub,
            "action": action,
            "target_path": target_path,
            "diff_sha256": diff_sha256,
            "task_id": task_id,
            "pr_number": pr_number,
            "commit_sha": commit_sha,
            "key_version": key_version,
            "prev_entry_hash": prev_hash,
        }
        computed = _sha256_hex(_canonical_json(row_for_hash))
        if computed != stored_entry:
            print(f"[audit] CHAIN BREAK: entry_hash mismatch at row {seq} "
                  f"(stored={stored_entry[:12]}..., computed={computed[:12]}...)",
                  file=sys.stderr)
            return 4

        # Verify HMAC
        try:
            key_bytes = _key_bytes_for_version(keys, key_version, args.strict)
        except RuntimeError as exc:
            print(f"[audit] {exc}", file=sys.stderr)
            return 3
        expected_hmac = hmac.new(key_bytes, stored_entry.encode("utf-8"), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected_hmac, stored_hmac):
            print(f"[audit] CHAIN BREAK: HMAC mismatch at row {seq} (key_version={key_version})",
                  file=sys.stderr)
            return 4

        expected_prev = stored_entry
        expected_seq = seq + 1
        verified += 1

    if not args.quiet:
        total = verified + skipped
        print(f"[audit] OK: chain clean across {total} row(s) "
              f"(verified={verified}, skipped={skipped})")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
