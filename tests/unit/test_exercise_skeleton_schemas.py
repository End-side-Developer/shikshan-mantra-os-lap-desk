"""
tests/unit/test_exercise_skeleton_schemas.py

Smoke tests for the skeleton exercise schemas: quiz, code, web, ctf.
(SMO-0512..0515) Verifies valid fixtures pass and required-field
mutations are rejected. Full per-engine tests arrive with each engine.

Run: python -m pytest tests/unit/test_exercise_skeleton_schemas.py -v
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

REPO = pathlib.Path(__file__).parent.parent.parent
EXERCISES = REPO / "modules/catalogs/schemas/exercises"


def load(name):
    with (EXERCISES / name).open() as f:
        schema = json.load(f)
    ValidatorClass = validator_for(schema)
    ValidatorClass.check_schema(schema)
    return schema


QUIZ_SCHEMA = load("quiz.schema.json")
CODE_SCHEMA = load("code.schema.json")
WEB_SCHEMA = load("web.schema.json")
CTF_SCHEMA = load("ctf.schema.json")

# ── Quiz ──────────────────────────────────────────────────────────────────────

VALID_QUIZ = {
    "id": "what-is-sql",
    "version": "1.0.0",
    "prompt": {"en": "What does SQL stand for?", "hi": "SQL का अर्थ क्या है?"},
    "kind": "mcq",
    "choices": [
        {"id": "a", "text": {"en": "Structured Query Language", "hi": "संरचित क्वेरी भाषा"}},
        {"id": "b", "text": {"en": "Simple Query Logic", "hi": "सरल क्वेरी तर्क"}},
    ],
    "correct_answer": "a",
    "locale": ["en", "hi"],
}


class TestQuizSchema:
    def test_valid_mcq(self):
        validate(instance=VALID_QUIZ, schema=QUIZ_SCHEMA)

    def test_true_false_kind(self):
        m = {**VALID_QUIZ, "kind": "true-false", "correct_answer": True}
        del m["choices"]
        validate(instance=m, schema=QUIZ_SCHEMA)

    def test_fill_blank_kind(self):
        m = {**VALID_QUIZ, "kind": "fill-blank", "correct_answer": ["SQL", "sql"]}
        del m["choices"]
        validate(instance=m, schema=QUIZ_SCHEMA)

    def test_with_explanation(self):
        m = copy.deepcopy(VALID_QUIZ)
        m["explanation"] = {
            "en": "SQL = Structured Query Language.",
            "hi": "SQL = संरचित क्वेरी भाषा।",
        }
        validate(instance=m, schema=QUIZ_SCHEMA)

    def test_unknown_kind_rejected(self):
        m = {**VALID_QUIZ, "kind": "drag-drop"}
        with pytest.raises(ValidationError):
            validate(instance=m, schema=QUIZ_SCHEMA)

    def test_missing_hi_prompt_rejected(self):
        m = copy.deepcopy(VALID_QUIZ)
        del m["prompt"]["hi"]
        with pytest.raises(ValidationError):
            validate(instance=m, schema=QUIZ_SCHEMA)

    def test_additional_property_rejected(self):
        m = {**VALID_QUIZ, "secret": "field"}
        with pytest.raises(ValidationError):
            validate(instance=m, schema=QUIZ_SCHEMA)


# ── Code ──────────────────────────────────────────────────────────────────────

VALID_CODE = {
    "id": "hello-world",
    "version": "1.0.0",
    "prompt": {"en": "Print 'Hello, World!'", "hi": "'Hello, World!' प्रिंट करें"},
    "language": "python",
    "starter_code": "# write your code here\n",
    "test_cases": [{"input": "", "expected_output": "Hello, World!"}],
    "locale": ["en", "hi"],
}


class TestCodeSchema:
    def test_valid(self):
        validate(instance=VALID_CODE, schema=CODE_SCHEMA)

    def test_hidden_test_case(self):
        m = copy.deepcopy(VALID_CODE)
        m["test_cases"].append({"input": "", "expected_output": "Hello, World!", "hidden": True})
        validate(instance=m, schema=CODE_SCHEMA)

    def test_unsupported_language_rejected(self):
        m = {**VALID_CODE, "language": "javascript"}
        with pytest.raises(ValidationError):
            validate(instance=m, schema=CODE_SCHEMA)

    def test_empty_test_cases_rejected(self):
        m = {**VALID_CODE, "test_cases": []}
        with pytest.raises(ValidationError):
            validate(instance=m, schema=CODE_SCHEMA)

    def test_additional_property_rejected(self):
        m = {**VALID_CODE, "extra": True}
        with pytest.raises(ValidationError):
            validate(instance=m, schema=CODE_SCHEMA)


# ── Web ───────────────────────────────────────────────────────────────────────

VALID_WEB = {
    "id": "my-first-heading",
    "version": "1.0.0",
    "prompt": {"en": "Add an <h1> tag.", "hi": "<h1> टैग जोड़ें।"},
    "starter": {"html": "<html></html>", "css": "", "js": ""},
    "assertions": [
        {
            "kind": "dom_contains_selector",
            "selector": "h1",
            "message": {"en": "Must have an h1 element.", "hi": "h1 तत्व होना चाहिए।"},
        }
    ],
    "locale": ["en", "hi"],
}


class TestWebSchema:
    def test_valid(self):
        validate(instance=VALID_WEB, schema=WEB_SCHEMA)

    def test_all_assertion_kinds(self):
        for kind in (
            "dom_contains_selector",
            "dom_element_text",
            "dom_element_count",
            "no_js_error",
            "css_property",
        ):
            m = copy.deepcopy(VALID_WEB)
            m["assertions"] = [{"kind": kind, "message": {"en": "msg", "hi": "संदेश"}}]
            validate(instance=m, schema=WEB_SCHEMA)

    def test_empty_assertions_rejected(self):
        m = {**VALID_WEB, "assertions": []}
        with pytest.raises(ValidationError):
            validate(instance=m, schema=WEB_SCHEMA)

    def test_unknown_assertion_rejected(self):
        m = copy.deepcopy(VALID_WEB)
        m["assertions"] = [{"kind": "magic", "message": {"en": "x", "hi": "x"}}]
        with pytest.raises(ValidationError):
            validate(instance=m, schema=WEB_SCHEMA)

    def test_additional_property_rejected(self):
        m = {**VALID_WEB, "extra": "field"}
        with pytest.raises(ValidationError):
            validate(instance=m, schema=WEB_SCHEMA)


# ── CTF ───────────────────────────────────────────────────────────────────────

VALID_CTF = {
    "id": "find-the-flag",
    "version": "1.0.0",
    "prompt": {"en": "Find the hidden flag.", "hi": "छिपा हुआ फ्लैग खोजें।"},
    "flag_format": "^SMO\\{[A-Za-z0-9_]+\\}$",
    "scenario": {
        "container_image": "ghcr.io/shikshan/ctf-basic:1.0.0",
        "objective": {"en": "Read /flag.txt", "hi": "/flag.txt पढ़ें"},
        "exposed_ports": [8080],
    },
    "locale": ["en", "hi"],
}


class TestCtfSchema:
    def test_valid(self):
        validate(instance=VALID_CTF, schema=CTF_SCHEMA)

    def test_without_exposed_ports(self):
        m = copy.deepcopy(VALID_CTF)
        del m["scenario"]["exposed_ports"]
        validate(instance=m, schema=CTF_SCHEMA)

    def test_missing_flag_format_rejected(self):
        m = copy.deepcopy(VALID_CTF)
        del m["flag_format"]
        with pytest.raises(ValidationError):
            validate(instance=m, schema=CTF_SCHEMA)

    def test_missing_container_image_rejected(self):
        m = copy.deepcopy(VALID_CTF)
        del m["scenario"]["container_image"]
        with pytest.raises(ValidationError):
            validate(instance=m, schema=CTF_SCHEMA)

    def test_additional_property_rejected(self):
        m = {**VALID_CTF, "bounty": 100}
        with pytest.raises(ValidationError):
            validate(instance=m, schema=CTF_SCHEMA)
