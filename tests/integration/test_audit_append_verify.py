"""tests/integration/test_audit_append_verify.py

End-to-end test of the audit subsystem: append rows, then verify the chain
is clean. Uses a per-test temporary database to avoid polluting the real
docs/audit/audit.db.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
APPEND = REPO_ROOT / "scripts" / "audit" / "append-entry.py"
VERIFY = REPO_ROOT / "scripts" / "audit" / "verify-chain.py"


@pytest.fixture
def tmp_db(tmp_path, monkeypatch):
    db = tmp_path / "audit.db"
    monkeypatch.setenv("SHIKSHAN_AUDIT_DEV_KEY", "test-key-do-not-use-in-ci")
    monkeypatch.delenv("CI", raising=False)
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
    return db


def _append(db, **kw):
    cmd = [sys.executable, str(APPEND), "--db", str(db)]
    for k, v in kw.items():
        cmd.extend([f"--{k.replace('_', '-')}", str(v)])
    return subprocess.run(cmd, capture_output=True, text=True)


def _verify(db, *extra):
    return subprocess.run(
        [sys.executable, str(VERIFY), "--db", str(db), *extra],
        capture_output=True, text=True,
    )


def test_first_row_is_genesis(tmp_db):
    r = _append(tmp_db, actor="agent:test", action="edit", target="foo.txt")
    assert r.returncode == 0, r.stderr
    r = _verify(tmp_db)
    assert r.returncode == 0, r.stderr


def test_three_rows_verify_clean(tmp_db):
    for i in range(3):
        r = _append(tmp_db, actor="agent:test", action="edit", target=f"f{i}.txt")
        assert r.returncode == 0
    r = _verify(tmp_db)
    assert r.returncode == 0
    assert "OK" in r.stdout


def test_invalid_action_rejected(tmp_db):
    r = _append(tmp_db, actor="agent:test", action="not-a-real-action", target="x")
    assert r.returncode != 0


def test_actor_must_be_prefixed(tmp_db):
    r = _append(tmp_db, actor="just-a-name", action="edit", target="x")
    assert r.returncode != 0
    assert "agent:" in r.stderr or "human:" in r.stderr
