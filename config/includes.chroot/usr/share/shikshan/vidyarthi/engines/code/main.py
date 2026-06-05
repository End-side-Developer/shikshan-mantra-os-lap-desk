# SPDX-License-Identifier: GPL-2.0-or-later
"""Vidyarthi code engine — JSON-RPC 2.0 over stdio (ADR-0011, ADR-0019, SMO-0801).

Executes Python 3 submissions in a child subprocess, grades via stdin/stdout
exact-match per code.schema.json test_cases. Pure stdlib only.
"""

import io
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import yaml

# Force UTF-8 stdout so Hindi feedback serialises correctly on all platforms.
if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", line_buffering=True)

ENGINE_ID = "code"
ENGINE_VERSION = "0.1.0"
DEFAULT_TIMEOUT_S = 10.0

_exercise = None
_bundle_path = None

PASS_FEEDBACK = {
    "en": "All test cases passed. Well done!",
    "hi": "सभी टेस्ट केस पास हो गए। शाबाश!",
}

FAIL_FEEDBACK_TMPL = {
    "en": "Some test cases failed.",
    "hi": "कुछ टेस्ट केस विफल हो गए।",
}

TIMEOUT_FEEDBACK = {
    "en": "Execution timed out. Check for infinite loops.",
    "hi": "निष्पादन समय समाप्त हो गया। अनंत लूप की जाँच करें।",
}

SYNTAX_FEEDBACK = {
    "en": "SyntaxError: your code could not be parsed.",
    "hi": "SyntaxError: आपके कोड को पार्स नहीं किया जा सका।",
}

NO_EXERCISE_FEEDBACK = {
    "en": "No exercise loaded.",
    "hi": "कोई अभ्यास लोड नहीं किया गया।",
}


def _respond(req_id, result=None, error=None):
    msg = {"jsonrpc": "2.0", "id": req_id}
    if error:
        msg["error"] = error
    else:
        msg["result"] = result
    sys.stdout.write(json.dumps(msg) + "\n")
    sys.stdout.flush()


def _err(code, message, data=None):
    e = {"code": code, "message": message}
    if data:
        e["data"] = data
    return e


def _handle_init(params, req_id):
    global _bundle_path
    _bundle_path = pathlib.Path(params.get("bundle_path", "/module"))
    _respond(
        req_id,
        {
            "ok": True,
            "engine_id": ENGINE_ID,
            "engine_version": ENGINE_VERSION,
            "capabilities": ["grade"],
        },
    )


def _handle_load_exercise(params, req_id):
    global _exercise
    ex_id = params.get("exercise_id", "")
    ex_path = _bundle_path / "content" / "exercises" / f"{ex_id}.yml"
    if not ex_path.exists():
        _respond(req_id, error=_err(-32002, "exercise not found", {"id": ex_id}))
        return
    with ex_path.open(encoding="utf-8") as f:
        _exercise = yaml.safe_load(f)
    prompt = _exercise.get("prompt", {})
    _respond(
        req_id,
        {
            "exercise_id": _exercise.get("id", ex_id),
            "prompt": prompt,
            "starter": _exercise.get("starter_code", ""),
            "metadata": {"language": _exercise.get("language", "python")},
        },
    )


def _run_test_case(code_path, test_case, timeout_s):
    """Run code_path with test_case input; return (stdout, stderr, timed_out)."""
    try:
        proc = subprocess.run(
            [sys.executable, str(code_path)],
            input=test_case.get("input", ""),
            capture_output=True,
            text=True,
            timeout=timeout_s,
        )
        return proc.stdout, proc.stderr, False
    except subprocess.TimeoutExpired:
        return "", "", True


def _grade_exercise(submission_code):
    """Grade submission_code against the loaded exercise's test_cases.

    Returns (score, success, feedback_dict) where score is 0 or 1.
    Raises ValueError on syntax error (caller converts to score=0).
    """
    # Compile-time syntax check before spawning any subprocesses.
    try:
        compile(submission_code, "<submission>", "exec")
    except SyntaxError as exc:
        feedback = dict(SYNTAX_FEEDBACK)
        feedback["en"] = f"SyntaxError: {exc}"
        return 0, False, feedback

    test_cases = _exercise.get("test_cases", [])
    if not test_cases:
        return 1, True, dict(PASS_FEEDBACK)

    max_ms = _exercise.get("max_execution_ms", DEFAULT_TIMEOUT_S * 1000)
    timeout_s = max(0.1, min(max_ms / 1000.0, 30.0))

    tmp = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".py", delete=False, encoding="utf-8"
        ) as tmp:
            tmp.write(submission_code)
            tmp_path = pathlib.Path(tmp.name)

        for tc in test_cases:
            stdout, _stderr, timed_out = _run_test_case(tmp_path, tc, timeout_s)
            if timed_out:
                return None, None, None  # signal timeout to caller

            expected = tc.get("expected_output", "").strip()
            actual = stdout.strip()
            if actual != expected:
                hidden = tc.get("hidden", False)
                feedback = dict(FAIL_FEEDBACK_TMPL)
                if not hidden:
                    feedback["en"] = (
                        f"Some test cases failed. " f"Expected: {expected!r}, got: {actual!r}"
                    )
                return 0, False, feedback

    finally:
        if tmp is not None:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass

    return 1, True, dict(PASS_FEEDBACK)


def _handle_grade(params, req_id):
    if _exercise is None:
        _respond(req_id, error=_err(-32600, "no exercise loaded"))
        return
    submission = params.get("submission", {})
    code = submission if isinstance(submission, str) else submission.get("code", "")

    score, success, feedback = _grade_exercise(code)

    if score is None:
        # timeout signalled
        _respond(req_id, error=_err(-32003, "execution timeout", {"feedback": TIMEOUT_FEEDBACK}))
        return

    _respond(
        req_id,
        {
            "score": score,
            "success": success,
            "feedback": feedback,
            "xapi_statements": [],
        },
    )


def _dispatch(line):
    try:
        req = json.loads(line)
    except json.JSONDecodeError as exc:
        _respond(None, error=_err(-32700, f"parse error: {exc}"))
        return False
    req_id = req.get("id")
    method = req.get("method", "")
    params = req.get("params", {})
    if method == "init":
        _handle_init(params, req_id)
    elif method == "load_exercise":
        _handle_load_exercise(params, req_id)
    elif method == "grade":
        _handle_grade(params, req_id)
    elif method == "shutdown":
        _respond(req_id, {"ok": True})
        return True
    else:
        _respond(req_id, error=_err(-32601, f"method not found: {method}"))
    return False


if __name__ == "__main__":
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        if _dispatch(line):
            break
