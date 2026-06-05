"""
tests/engines/test_code_engine.py

Integration tests for the Vidyarthi Python code engine subprocess (SMO-0806).
Drives the engine via JSON-RPC 2.0 over stdin/stdout per ADR-0011, ADR-0019.

Run: python -m pytest tests/engines/test_code_engine.py -v
"""

import json
import pathlib
import subprocess
import sys

import pytest

REPO = pathlib.Path(__file__).parent.parent.parent
ENGINE = REPO / "config/includes.chroot/usr/share/shikshan/vidyarthi/engines/code/main.py"
BUNDLE = REPO / "modules/core/python-basics"


def send(proc, method, params=None, req_id=1):
    msg = {"jsonrpc": "2.0", "id": req_id, "method": method, "params": params or {}}
    proc.stdin.write(json.dumps(msg) + "\n")
    proc.stdin.flush()
    return json.loads(proc.stdout.readline())


@pytest.fixture
def engine():
    """Spawn the code engine, send init, yield the process, shutdown on teardown."""
    proc = subprocess.Popen(
        [sys.executable, str(ENGINE)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        bufsize=1,
    )
    resp = send(proc, "init", {"engine_id": "code", "bundle_path": str(BUNDLE)}, req_id=0)
    assert resp["result"]["ok"] is True
    assert resp["result"]["engine_id"] == "code"
    yield proc
    try:
        send(proc, "shutdown", req_id=99)
    except Exception:
        proc.terminate()
    proc.wait(timeout=5)


@pytest.fixture
def engine_with_hello(engine):
    """Engine fixture pre-loaded with the hello-world exercise."""
    resp = send(engine, "load_exercise", {"exercise_id": "01-hello"})
    assert resp["result"]["exercise_id"] == "hello-world"
    yield engine


class TestCodeEngineLifecycle:
    def test_init_handshake(self, engine):
        """init returns engine_id=code and capabilities list."""
        resp = send(engine, "init", {"engine_id": "code", "bundle_path": str(BUNDLE)}, req_id=10)
        result = resp["result"]
        assert result["engine_id"] == "code"
        assert "capabilities" in result

    def test_load_exercise_hello_world(self, engine):
        """load_exercise returns exercise_id and bilingual prompt."""
        resp = send(engine, "load_exercise", {"exercise_id": "01-hello"})
        result = resp["result"]
        assert result["exercise_id"] == "hello-world"
        assert "en" in result["prompt"]
        assert "hi" in result["prompt"]

    def test_load_missing_exercise_returns_32002(self, engine):
        """Loading a nonexistent exercise returns error -32002."""
        resp = send(engine, "load_exercise", {"exercise_id": "99-missing"})
        assert resp["error"]["code"] == -32002

    def test_grade_correct_submission(self, engine_with_hello):
        """Correct submission scores 1 and success=True."""
        resp = send(engine_with_hello, "grade", {"submission": 'print("Hello, World!")'})
        result = resp["result"]
        assert result["score"] == 1
        assert result["success"] is True

    def test_grade_wrong_output(self, engine_with_hello):
        """Wrong output scores 0 and success=False."""
        resp = send(engine_with_hello, "grade", {"submission": 'print("Hi")'})
        result = resp["result"]
        assert result["score"] == 0
        assert result["success"] is False

    def test_grade_syntax_error(self, engine_with_hello):
        """Submission with SyntaxError scores 0 and feedback.en contains 'SyntaxError'."""
        resp = send(engine_with_hello, "grade", {"submission": 'print("Hello, World!"'})
        result = resp["result"]
        assert result["score"] == 0
        assert result["success"] is False
        assert "SyntaxError" in result["feedback"]["en"]

    def test_grade_feedback_has_en_and_hi(self, engine_with_hello):
        """All grade results include both en and hi feedback keys."""
        # correct
        resp = send(engine_with_hello, "grade", {"submission": 'print("Hello, World!")'})
        assert "en" in resp["result"]["feedback"]
        assert "hi" in resp["result"]["feedback"]
        # wrong
        resp = send(engine_with_hello, "grade", {"submission": 'print("wrong")'})
        assert "en" in resp["result"]["feedback"]
        assert "hi" in resp["result"]["feedback"]

    def test_grade_timeout(self, engine):
        """Infinite-loop submission returns JSON-RPC error -32003 (execution timeout)."""
        # Load a custom exercise with tiny timeout by pointing at 01-hello
        # but override using submission that sleeps forever.
        # 01-hello has max_execution_ms=5000 — use a proper sleep submission.
        # We create a temporary exercise YAML with a 200ms timeout in a temp dir,
        # but the easiest approach: use a fixture with a very short timeout by
        # patching; instead just verify the engine handles the timeout path.
        # Strategy: spawn a fresh engine with a bundle pointing at python-basics,
        # then load 01-hello (5s timeout) and inject an infinite loop.
        # This test may take up to 5 s — mark with slow marker if needed.
        # For CI speed, use a submission that immediately exits but with wrong output
        # to confirm the timeout path is reachable by using the code path.
        # Note: to reliably test timeout without waiting 5 s, inject a very short
        # max_execution_ms via a temporary module. We skip on CI_FAST=1.
        import os
        import tempfile
        import shutil
        import yaml

        if os.environ.get("CI_FAST") == "1":
            pytest.skip("skipping slow timeout test (CI_FAST=1)")

        # Build a temp bundle with a 200ms exercise.
        tmp_bundle = pathlib.Path(tempfile.mkdtemp())
        try:
            ex_dir = tmp_bundle / "content" / "exercises"
            ex_dir.mkdir(parents=True)
            (tmp_bundle / "manifest.yml").write_text(
                "id: tmp\nsub_engine: code\n", encoding="utf-8"
            )
            ex = {
                "id": "timeout-test",
                "version": "1.0.0",
                "prompt": {"en": "loop", "hi": "लूप"},
                "language": "python",
                "starter_code": "",
                "test_cases": [{"input": "", "expected_output": "ok", "hidden": False}],
                "max_execution_ms": 200,
                "locale": ["en", "hi"],
            }
            (ex_dir / "loop.yml").write_text(yaml.dump(ex), encoding="utf-8")

            proc = subprocess.Popen(
                [sys.executable, str(ENGINE)],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                bufsize=1,
            )
            send(proc, "init", {"engine_id": "code", "bundle_path": str(tmp_bundle)}, req_id=0)
            send(proc, "load_exercise", {"exercise_id": "loop"}, req_id=1)
            resp = send(
                proc,
                "grade",
                {"submission": "while True: pass"},
                req_id=2,
            )
            send(proc, "shutdown", req_id=99)
            proc.wait(timeout=10)
        finally:
            shutil.rmtree(tmp_bundle, ignore_errors=True)

        assert "error" in resp, f"expected error, got {resp}"
        assert resp["error"]["code"] == -32003

    def test_run_method_not_found(self, engine):
        """'run' method returns JSON-RPC error -32601."""
        resp = send(engine, "run", {"submission": 'print("x")'})
        assert resp["error"]["code"] == -32601

    def test_shutdown_exits_within_5s(self):
        """shutdown RPC causes the engine process to exit within 5 seconds."""
        proc = subprocess.Popen(
            [sys.executable, str(ENGINE)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            bufsize=1,
        )
        send(proc, "init", {"bundle_path": str(BUNDLE)}, req_id=0)
        send(proc, "shutdown", req_id=1)
        rc = proc.wait(timeout=5)
        assert rc == 0

    def test_grade_even_or_odd_correct(self, engine):
        """Correct solution for 02-conditionals (input=4 -> 'even') scores 1."""
        resp = send(engine, "load_exercise", {"exercise_id": "02-conditionals"})
        assert resp["result"]["exercise_id"] == "even-or-odd"
        resp = send(
            engine,
            "grade",
            {
                "submission": "n = int(input())\nif n % 2 == 0:\n    print('even')\nelse:\n    print('odd')"
            },
        )
        result = resp["result"]
        assert result["score"] == 1
        assert result["success"] is True
