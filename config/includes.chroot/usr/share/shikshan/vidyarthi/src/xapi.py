# SPDX-License-Identifier: GPL-2.0-or-later
"""xAPI telemetry writer (SMO-0611, ADR-0014).

GTK-free. The SQL engine returns ``xapi_statements: []`` — the frontend owns
statement emission.  Statements are appended to a local SQLite store; nothing
leaves the device (local-only by decision; see docs/architecture/progress-store.md).

Schema matches the one proven in tests/e2e/test_vidyarthi_sql_mvp.sh stage 7.
"""

from __future__ import annotations

import datetime
import json
import os
import pathlib
import sqlite3
import uuid

_VERB_SCORED = "http://adlnet.gov/expapi/verbs/scored"


def learner_db_path() -> pathlib.Path:
    """``$XDG_DATA_HOME``/shikshan/learner.db, falling back to ~/.local/share."""
    xdg = os.environ.get("XDG_DATA_HOME")
    base = pathlib.Path(xdg) if xdg else pathlib.Path.home() / ".local" / "share"
    return base / "shikshan" / "learner.db"


def _connect(db_path: pathlib.Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(db_path))
    con.execute(
        """CREATE TABLE IF NOT EXISTS statements (
            id        TEXT PRIMARY KEY,
            stored_at TEXT NOT NULL,
            verb_id   TEXT NOT NULL,
            object_id TEXT NOT NULL,
            statement TEXT NOT NULL)"""
    )
    return con


def record_scored(
    module_id: str,
    exercise_id: str,
    score: int,
    success: bool,
    db_path: pathlib.Path | None = None,
) -> str:
    """Append a ``scored`` xAPI statement; return its UUID."""
    db_path = db_path or learner_db_path()
    sid = str(uuid.uuid4())
    object_id = f"vidyarthi://{module_id}/{exercise_id}"
    statement = {
        "id": sid,
        "verb": {"id": _VERB_SCORED, "display": {"en-US": "scored"}},
        "object": {"id": object_id},
        "result": {
            "score": {"raw": int(score), "min": 0, "max": 100},
            "success": bool(success),
        },
    }
    con = _connect(db_path)
    try:
        con.execute(
            "INSERT INTO statements VALUES (?,?,?,?,?)",
            (
                sid,
                datetime.datetime.now(datetime.timezone.utc).isoformat(),
                _VERB_SCORED,
                object_id,
                json.dumps(statement),
            ),
        )
        con.commit()
    finally:
        con.close()
    return sid
