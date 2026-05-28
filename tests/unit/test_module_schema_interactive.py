"""
tests/unit/test_module_schema_interactive.py

Round-trip and mutation tests for the interactive-runner / quiz additions
to modules/catalogs/schemas/module.schema.json (SMO-0510).

Run: python -m pytest tests/unit/test_module_schema_interactive.py -v
Requires: jsonschema >= 4.18 (draft 2020-12 support), PyYAML
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
SCHEMA_PATH = REPO_ROOT / "modules/catalogs/schemas/module.schema.json"

with SCHEMA_PATH.open() as f:
    SCHEMA = json.load(f)

ValidatorClass = validator_for(SCHEMA)
ValidatorClass.check_schema(SCHEMA)


VALID_BASE = {
    "id": "sql-basics",
    "version": "1.0.0",
    "title": {"en": "SQL Basics", "hi": "SQL की मूल बातें"},
    "description": {"en": "Learn SQL from scratch.", "hi": "SQL सीखें।"},
    "language": ["en", "hi"],
    "age_band": "16-18",
    "difficulty": "beginner",
    "prerequisites": [],
    "outcomes": [{"en": "Write a SELECT query", "hi": "SELECT क्वेरी लिखें"}],
    "content_type": "html",
    "entrypoint": "index.html",
    "required_apps": [],
    "unlock_rules": [{"kind": "free"}],
    "license": "CC-BY-SA-4.0",
    "checksum": "sha256:" + "a" * 64,
}

VALID_INTERACTIVE_RUNNER = {
    **VALID_BASE,
    "content_type": "interactive-runner",
    "sub_engine": "sql",
    "entrypoint": "exercises/",
    "exercise_spec": {
        "fixtures": "fixtures/employees.sql",
        "exercises": ["01-select.yml", "02-where.yml"],
    },
}

VALID_QUIZ = {
    **VALID_BASE,
    "content_type": "quiz",
    "entrypoint": "quiz.yml",
}


class TestRoundTrip:
    def test_original_html_type_still_valid(self):
        validate(instance=VALID_BASE, schema=SCHEMA)

    def test_interactive_runner_valid(self):
        validate(instance=VALID_INTERACTIVE_RUNNER, schema=SCHEMA)

    def test_quiz_valid(self):
        validate(instance=VALID_QUIZ, schema=SCHEMA)

    def test_all_legacy_content_types_still_valid(self):
        for ct in ("html", "pdf", "video", "webxr", "blockly", "python", "jupyter"):
            m = {**VALID_BASE, "content_type": ct}
            validate(instance=m, schema=SCHEMA)

    def test_sub_engine_sql_accepted(self):
        validate(instance=VALID_INTERACTIVE_RUNNER, schema=SCHEMA)

    def test_sub_engine_all_values(self):
        for se in ("sql", "web", "code", "ctf", "quiz"):
            m = {**VALID_INTERACTIVE_RUNNER, "sub_engine": se}
            validate(instance=m, schema=SCHEMA)

    def test_exercise_spec_freeform_object(self):
        m = copy.deepcopy(VALID_INTERACTIVE_RUNNER)
        m["exercise_spec"]["extra_key"] = "anything"
        validate(instance=m, schema=SCHEMA)

    def test_interactive_runner_without_sub_engine_still_valid(self):
        # sub_engine is optional at schema level (policy enforces it)
        m = copy.deepcopy(VALID_INTERACTIVE_RUNNER)
        del m["sub_engine"]
        validate(instance=m, schema=SCHEMA)


class TestMutations:
    def test_unknown_content_type_rejected(self):
        m = {**VALID_BASE, "content_type": "network-sim"}
        with pytest.raises(ValidationError):
            validate(instance=m, schema=SCHEMA)

    def test_unknown_sub_engine_rejected(self):
        m = {**VALID_INTERACTIVE_RUNNER, "sub_engine": "unknown-engine"}
        with pytest.raises(ValidationError):
            validate(instance=m, schema=SCHEMA)

    def test_sub_engine_not_string_rejected(self):
        m = {**VALID_INTERACTIVE_RUNNER, "sub_engine": 42}
        with pytest.raises(ValidationError):
            validate(instance=m, schema=SCHEMA)

    def test_exercise_spec_not_object_rejected(self):
        m = {**VALID_INTERACTIVE_RUNNER, "exercise_spec": "not-an-object"}
        with pytest.raises(ValidationError):
            validate(instance=m, schema=SCHEMA)

    def test_missing_required_id_rejected(self):
        m = copy.deepcopy(VALID_INTERACTIVE_RUNNER)
        del m["id"]
        with pytest.raises(ValidationError):
            validate(instance=m, schema=SCHEMA)

    def test_missing_hi_title_rejected(self):
        m = copy.deepcopy(VALID_INTERACTIVE_RUNNER)
        del m["title"]["hi"]
        with pytest.raises(ValidationError):
            validate(instance=m, schema=SCHEMA)

    def test_bad_checksum_format_rejected(self):
        m = {**VALID_BASE, "checksum": "md5:abc123"}
        with pytest.raises(ValidationError):
            validate(instance=m, schema=SCHEMA)

    def test_additional_property_rejected(self):
        m = {**VALID_BASE, "unknown_field": "value"}
        with pytest.raises(ValidationError):
            validate(instance=m, schema=SCHEMA)
