# SPDX-License-Identifier: GPL-2.0-or-later
"""Unit tests for catalog resolution (SMO-0611)."""

import catalog


def test_resolve_bundle_path_sql_basics():
    bundle = catalog.resolve_bundle_path("sql-basics")
    assert bundle is not None
    assert bundle.name == "sql-basics"
    assert (bundle / "manifest.yml").exists()


def test_resolve_bundle_path_unknown():
    assert catalog.resolve_bundle_path("does-not-exist") is None


def test_list_exercises_order_and_stems():
    exercises = catalog.list_exercises("sql-basics")
    ids = [e["exercise_id"] for e in exercises]
    assert ids == ["01-select", "02-where", "03-join"]
    # exercise_id is the file stem, NOT the YAML id: field.
    assert all("id" not in e or e["exercise_id"] != "select-all" for e in exercises)


def test_list_exercises_unknown_module():
    assert catalog.list_exercises("does-not-exist") == []


def test_load_exercise_spec_has_prompt_and_hints():
    spec = catalog.load_exercise_spec("sql-basics", "01-select")
    assert spec is not None
    assert spec["id"] == "select-all"  # internal id differs from the stem
    assert "en" in spec["prompt"]
    assert spec["hints"]
