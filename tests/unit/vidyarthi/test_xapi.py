# SPDX-License-Identifier: GPL-2.0-or-later
"""Unit tests for the xAPI writer (SMO-0611)."""

import json
import sqlite3

import xapi


def test_record_scored_explicit_path(tmp_path):
    db = tmp_path / "learner.db"
    sid = xapi.record_scored("sql-basics", "01-select", 100, True, db_path=db)

    con = sqlite3.connect(str(db))
    try:
        row = con.execute("SELECT id, verb_id, object_id, statement FROM statements").fetchone()
    finally:
        con.close()

    assert row[0] == sid
    assert row[1] == "http://adlnet.gov/expapi/verbs/scored"
    assert row[2] == "vidyarthi://sql-basics/01-select"
    stmt = json.loads(row[3])
    assert stmt["result"]["score"]["raw"] == 100
    assert stmt["result"]["success"] is True


def test_record_scored_honours_xdg(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    xapi.record_scored("sql-basics", "02-where", 0, False)
    assert (tmp_path / "shikshan" / "learner.db").exists()


def test_two_statements_distinct_ids(tmp_path):
    db = tmp_path / "learner.db"
    a = xapi.record_scored("sql-basics", "01-select", 100, True, db_path=db)
    b = xapi.record_scored("sql-basics", "01-select", 100, True, db_path=db)
    assert a != b
    con = sqlite3.connect(str(db))
    try:
        (count,) = con.execute("SELECT count(*) FROM statements").fetchone()
    finally:
        con.close()
    assert count == 2
