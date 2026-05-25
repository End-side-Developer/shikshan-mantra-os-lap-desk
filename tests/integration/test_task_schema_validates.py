"""tests/integration/test_task_schema_validates.py

Every example task contract under tasks/examples/ must validate against
tasks/schema/task.schema.yml. Regression test for the schema itself.
"""
from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from jsonschema import Draft202012Validator

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SCHEMA_PATH = REPO_ROOT / "tasks" / "schema" / "task.schema.yml"
EXAMPLES = list((REPO_ROOT / "tasks" / "examples").glob("*.yml"))


@pytest.fixture(scope="module")
def schema():
    return yaml.safe_load(SCHEMA_PATH.read_text(encoding="utf-8"))


@pytest.mark.parametrize("example", EXAMPLES, ids=[p.name for p in EXAMPLES])
def test_example_validates(example: Path, schema: dict):
    instance = yaml.safe_load(example.read_text(encoding="utf-8"))
    Draft202012Validator(schema).validate(instance)


def test_schema_itself_is_valid_jsonschema(schema):
    Draft202012Validator.check_schema(schema)
