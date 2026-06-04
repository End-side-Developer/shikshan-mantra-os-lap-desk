# SPDX-License-Identifier: GPL-2.0-or-later
"""Unit tests for ExerciseSession orchestration (SMO-0611)."""

import sqlite3

import pytest
from session import EngineError, ExerciseSession


def test_session_run_correct():
    with ExerciseSession("sql-basics", "01-select", sandbox=False) as s:
        assert "en" in s.prompt
        result = s.run("SELECT * FROM employees;")
        assert result["score"] == 100
        assert result["success"] is True


def test_session_submit_writes_xapi(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    with ExerciseSession("sql-basics", "01-select", sandbox=False) as s:
        result = s.submit("SELECT * FROM employees;")
    assert result["score"] == 100
    assert "xapi_id" in result

    db = tmp_path / "shikshan" / "learner.db"
    assert db.exists()
    con = sqlite3.connect(str(db))
    try:
        (count,) = con.execute(
            "SELECT count(*) FROM statements " "WHERE verb_id = ? AND object_id = ?",
            (
                "http://adlnet.gov/expapi/verbs/scored",
                "vidyarthi://sql-basics/01-select",
            ),
        ).fetchone()
    finally:
        con.close()
    assert count == 1


def test_session_unknown_module_raises():
    with pytest.raises(EngineError):
        ExerciseSession("no-such-module", "01-select", sandbox=False).open()
