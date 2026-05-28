"""
tests/unit/test_sql_exercise_schema.py

Round-trip and mutation tests for modules/catalogs/schemas/exercises/sql.schema.json
(SMO-0511). Run: python -m pytest tests/unit/test_sql_exercise_schema.py -v
"""

import copy
import json
import pathlib
import pytest

try:
    from jsonschema import validate, ValidationError
    from jsonschema.validators import validator_for
except ImportError:
    pytest.skip("jsonschema not installed", allow_module_level=True)

REPO_ROOT = pathlib.Path(__file__).parent.parent.parent
SCHEMA_PATH = REPO_ROOT / "modules/catalogs/schemas/exercises/sql.schema.json"

with SCHEMA_PATH.open() as f:
    SCHEMA = json.load(f)

ValidatorClass = validator_for(SCHEMA)
ValidatorClass.check_schema(SCHEMA)

VALID = {
    "id": "select-basics",
    "version": "1.0.0",
    "prompt": {
        "en": "Write a SELECT query to get all employees.",
        "hi": "सभी कर्मचारियों को प्राप्त करने के लिए SELECT क्वेरी लिखें।",
    },
    "starter_sql": "SELECT ",
    "fixtures": ["fixtures/employees.sql"],
    "assertions": [
        {
            "kind": "no_error",
            "message": {"en": "Query must run without error.", "hi": "क्वेरी बिना त्रुटि चलनी चाहिए।"},
        },
        {
            "kind": "row_count",
            "expected": 5,
            "message": {"en": "Expected 5 rows.", "hi": "5 पंक्तियाँ अपेक्षित हैं।"},
        },
    ],
    "locale": ["en", "hi"],
}


class TestRoundTrip:
    def test_minimal_valid(self):
        validate(instance=VALID, schema=SCHEMA)

    def test_with_hints(self):
        m = copy.deepcopy(VALID)
        m["hints"] = [{"en": "Use SELECT *", "hi": "SELECT * उपयोग करें"}]
        validate(instance=m, schema=SCHEMA)

    def test_with_rubric(self):
        m = copy.deepcopy(VALID)
        m["rubric"] = {"pass_threshold": 80, "partial_credit": True}
        validate(instance=m, schema=SCHEMA)

    def test_with_max_execution_ms(self):
        m = copy.deepcopy(VALID)
        m["max_execution_ms"] = 3000
        validate(instance=m, schema=SCHEMA)

    def test_all_assertion_kinds(self):
        for kind in (
            "result_equals",
            "result_contains_row",
            "row_count",
            "column_names",
            "no_error",
            "query_matches_regex",
        ):
            m = copy.deepcopy(VALID)
            m["assertions"] = [{"kind": kind, "message": {"en": "msg", "hi": "संदेश"}}]
            validate(instance=m, schema=SCHEMA)

    def test_multiple_fixtures(self):
        m = copy.deepcopy(VALID)
        m["fixtures"] = ["fixtures/schema.sql", "fixtures/employees.sql"]
        validate(instance=m, schema=SCHEMA)

    def test_empty_starter_sql(self):
        m = copy.deepcopy(VALID)
        m["starter_sql"] = ""
        validate(instance=m, schema=SCHEMA)


class TestMutations:
    def test_missing_id_rejected(self):
        m = copy.deepcopy(VALID)
        del m["id"]
        with pytest.raises(ValidationError):
            validate(instance=m, schema=SCHEMA)

    def test_missing_hi_prompt_rejected(self):
        m = copy.deepcopy(VALID)
        del m["prompt"]["hi"]
        with pytest.raises(ValidationError):
            validate(instance=m, schema=SCHEMA)

    def test_empty_fixtures_rejected(self):
        m = copy.deepcopy(VALID)
        m["fixtures"] = []
        with pytest.raises(ValidationError):
            validate(instance=m, schema=SCHEMA)

    def test_empty_assertions_rejected(self):
        m = copy.deepcopy(VALID)
        m["assertions"] = []
        with pytest.raises(ValidationError):
            validate(instance=m, schema=SCHEMA)

    def test_unknown_assertion_kind_rejected(self):
        m = copy.deepcopy(VALID)
        m["assertions"] = [{"kind": "magic", "message": {"en": "x", "hi": "x"}}]
        with pytest.raises(ValidationError):
            validate(instance=m, schema=SCHEMA)

    def test_bad_version_rejected(self):
        m = copy.deepcopy(VALID)
        m["version"] = "v1"
        with pytest.raises(ValidationError):
            validate(instance=m, schema=SCHEMA)

    def test_max_execution_too_low_rejected(self):
        m = copy.deepcopy(VALID)
        m["max_execution_ms"] = 50
        with pytest.raises(ValidationError):
            validate(instance=m, schema=SCHEMA)

    def test_additional_property_rejected(self):
        m = {**VALID, "surprise": "field"}
        with pytest.raises(ValidationError):
            validate(instance=m, schema=SCHEMA)

    def test_missing_locale_rejected(self):
        m = copy.deepcopy(VALID)
        del m["locale"]
        with pytest.raises(ValidationError):
            validate(instance=m, schema=SCHEMA)
