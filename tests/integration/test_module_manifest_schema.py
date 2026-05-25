"""tests/integration/test_module_manifest_schema.py

Schema regression tests for module manifests. Asserts:
- The valid fixture validates clean.
- The Hi/En parity violation fixture is rejected.
- Every modules/core/*/manifest.yml that exists validates.
"""
from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from jsonschema import Draft202012Validator, ValidationError

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SCHEMA = REPO_ROOT / "modules" / "catalogs" / "schemas" / "module.schema.json"
FIXTURES = REPO_ROOT / "tests" / "fixtures" / "manifests"


@pytest.fixture(scope="module")
def validator():
    import json
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


def test_valid_fixture_passes(validator):
    fx = FIXTURES / "ai-literacy-basics.manifest.yml"
    instance = yaml.safe_load(fx.read_text(encoding="utf-8"))
    validator.validate(instance)


def test_missing_hindi_title_rejected(validator):
    fx = FIXTURES / "invalid-no-hindi-title.manifest.yml"
    instance = yaml.safe_load(fx.read_text(encoding="utf-8"))
    with pytest.raises(ValidationError):
        validator.validate(instance)


@pytest.mark.parametrize(
    "path",
    list((REPO_ROOT / "modules" / "core").glob("*/manifest.yml")),
    ids=lambda p: p.parent.name if p else "none",
)
def test_real_module_manifests_validate(validator, path: Path):
    instance = yaml.safe_load(path.read_text(encoding="utf-8"))
    validator.validate(instance)
