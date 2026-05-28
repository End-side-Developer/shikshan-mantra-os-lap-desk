# SPDX-License-Identifier: GPL-2.0-or-later
"""Vidyarthi SQL engine — JSON-RPC 2.0 over stdio (ADR-0011, SMO-0560)."""

import json
import sqlite3
import sys
import pathlib
import yaml

ENGINE_ID = "sql"
ENGINE_VERSION = "0.1.0"

_exercise = None
_bundle_path = None


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
    _respond(req_id, {"ok": True, "engine_version": ENGINE_VERSION, "capabilities": []})


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
            "prompt": prompt,
            "starter": _exercise.get("starter_sql", ""),
            "metadata": {"fixtures": _exercise.get("fixtures", [])},
        },
    )


def _grade_exercise(submission):
    fixtures = _exercise.get("fixtures", [])
    con = sqlite3.connect(":memory:")
    try:
        for fix_path in fixtures:
            sql_file = _bundle_path / fix_path
            if sql_file.exists():
                con.executescript(sql_file.read_text(encoding="utf-8"))
        try:
            cur = con.execute(submission)
            rows = [dict(zip([d[0] for d in cur.description], r)) for r in cur.fetchall()]
        except sqlite3.Error as exc:
            return (
                0,
                False,
                [
                    {
                        "assertion_index": 0,
                        "passed": False,
                        "message": {"en": str(exc), "hi": str(exc)},
                    }
                ],
            )
        assertions = _exercise.get("assertions", [])
        passed = 0
        feedback = []
        for i, a in enumerate(assertions):
            ok = _check_assertion(a, rows)
            feedback.append(
                {
                    "assertion_index": i,
                    "passed": ok,
                    "message": a.get("message", {"en": "", "hi": ""}),
                }
            )
            if ok:
                passed += 1
        score = int((passed / len(assertions)) * 100) if assertions else 0
        return score, score == 100, feedback
    finally:
        con.close()


def _check_assertion(a, rows):
    kind = a.get("kind")
    if kind == "no_error":
        return True
    if kind == "row_count":
        return len(rows) == a.get("expected", 0)
    if kind == "column_names":
        if not rows:
            return False
        return set(rows[0].keys()) == set(a.get("expected", []))
    if kind == "result_equals":
        return rows == a.get("expected", [])
    if kind == "result_contains_row":
        return a.get("expected") in rows
    return True


def _handle_grade(params, req_id):
    if _exercise is None:
        _respond(req_id, error=_err(-32600, "no exercise loaded"))
        return
    submission = params.get("submission", "")
    score, success, feedback = _grade_exercise(submission)
    _respond(
        req_id, {"score": score, "success": success, "feedback": feedback, "xapi_statements": []}
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
