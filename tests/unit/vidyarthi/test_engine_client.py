# SPDX-License-Identifier: GPL-2.0-or-later
"""Unit tests for the JSON-RPC engine client (SMO-0611).

Drives the real engine subprocess directly (sandbox off so it runs on Windows).
"""

import catalog
import pytest
from engine_client import EngineClient, EngineError

BUNDLE = catalog.resolve_bundle_path("sql-basics")


def test_init_load_grade_correct():
    with EngineClient(sandbox=False) as eng:
        init = eng.init(BUNDLE)
        assert init.get("ok") is True
        loaded = eng.load_exercise("01-select")
        assert "en" in loaded["prompt"]
        assert loaded["starter"]  # starter SQL present
        result = eng.grade("SELECT * FROM employees;")
        assert result["score"] == 100
        assert result["success"] is True
        # Engine never emits xAPI — the frontend owns that.
        assert result["xapi_statements"] == []


def test_grade_incorrect_partial_score():
    with EngineClient(sandbox=False) as eng:
        eng.init(BUNDLE)
        eng.load_exercise("01-select")
        result = eng.grade("SELECT id FROM employees;")
        assert result["success"] is False
        assert 0 <= result["score"] < 100


def test_load_unknown_exercise_raises():
    with EngineClient(sandbox=False) as eng:
        eng.init(BUNDLE)
        with pytest.raises(EngineError):
            eng.load_exercise("99-nope")
