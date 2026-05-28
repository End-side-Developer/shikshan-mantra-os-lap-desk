"""
tests/engines/test_sql_engine.py

Integration tests for the Vidyarthi SQL engine subprocess (SMO-0560).
Drives the engine via JSON-RPC 2.0 over stdin/stdout per ADR-0011.

Run: python -m pytest tests/engines/test_sql_engine.py -v
"""

import json
import pathlib
import subprocess
import sys

import pytest

REPO = pathlib.Path(__file__).parent.parent.parent
ENGINE = REPO / "config/includes.chroot/usr/share/shikshan/vidyarthi/engines/sql/main.py"
BUNDLE = REPO / "modules/core/sql-basics"


def send(proc, method, params=None, req_id=1):
    msg = {"jsonrpc": "2.0", "id": req_id, "method": method, "params": params or {}}
    proc.stdin.write(json.dumps(msg) + "\n")
    proc.stdin.flush()
    return json.loads(proc.stdout.readline())


@pytest.fixture
def engine():
    proc = subprocess.Popen(
        [sys.executable, str(ENGINE)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        text=True,
        bufsize=1,
    )
    resp = send(proc, "init", {"engine_id": "sql", "bundle_path": str(BUNDLE)}, req_id=0)
    assert resp["result"]["ok"] is True
    yield proc
    try:
        send(proc, "shutdown", req_id=99)
    except Exception:
        proc.terminate()
    proc.wait(timeout=5)


class TestSqlEngineLifecycle:
    def test_init_returns_engine_version(self, engine):
        resp = send(engine, "init", {"engine_id": "sql", "bundle_path": str(BUNDLE)}, req_id=10)
        assert "engine_version" in resp["result"]

    def test_load_exercise_01_select(self, engine):
        resp = send(engine, "load_exercise", {"exercise_id": "01-select"})
        assert "prompt" in resp["result"]
        assert "en" in resp["result"]["prompt"]

    def test_load_nonexistent_exercise_returns_32002(self, engine):
        resp = send(engine, "load_exercise", {"exercise_id": "99-missing"})
        assert resp["error"]["code"] == -32002

    def test_grade_correct_select_all(self, engine):
        send(engine, "load_exercise", {"exercise_id": "01-select"})
        resp = send(engine, "grade", {"submission": "SELECT * FROM employees"})
        result = resp["result"]
        assert result["score"] == 100
        assert result["success"] is True

    def test_grade_wrong_query_fails(self, engine):
        send(engine, "load_exercise", {"exercise_id": "01-select"})
        resp = send(engine, "grade", {"submission": "SELECT * FROM departments"})
        result = resp["result"]
        assert result["success"] is False

    def test_grade_syntax_error_returns_score_zero(self, engine):
        send(engine, "load_exercise", {"exercise_id": "01-select"})
        resp = send(engine, "grade", {"submission": "SELECTTTTT broken"})
        assert resp["result"]["score"] == 0

    def test_run_returns_32601(self, engine):
        resp = send(engine, "run", {"submission": "SELECT 1"})
        assert resp["error"]["code"] == -32601

    def test_shutdown_exits_within_5s(self):
        proc = subprocess.Popen(
            [sys.executable, str(ENGINE)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            text=True,
            bufsize=1,
        )
        send(proc, "init", {"bundle_path": str(BUNDLE)}, req_id=0)
        send(proc, "shutdown", req_id=1)
        rc = proc.wait(timeout=5)
        assert rc == 0
