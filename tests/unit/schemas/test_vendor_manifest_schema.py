"""tests/unit/schemas/test_vendor_manifest_schema.py

Schema regression tests for vendor/MANIFEST.yml (per ADR-0003).

Enumerates the four fixtures under tests/fixtures/vendor-manifest/ via
``pytest.mark.parametrize``:

* ``valid-*.yml``  -> must parse as YAML and validate clean against
  ``modules/catalogs/schemas/vendor-manifest.schema.json``.
* ``invalid-*.yml`` -> must parse as YAML and produce at least one
  ``jsonschema`` ValidationError.

Uses Draft 2020-12 (matching the schema's ``$schema``) and ``format`` checking
(so ``upstream_url`` / ``last_synced`` are exercised as URI / date-time).
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml
from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
SCHEMA_PATH = (
    REPO_ROOT
    / "modules"
    / "catalogs"
    / "schemas"
    / "vendor-manifest.schema.json"
)
FIXTURES_DIR = (
    Path(__file__).resolve().parent.parent.parent
    / "fixtures"
    / "vendor-manifest"
)


@pytest.fixture(scope="module")
def validator() -> Draft202012Validator:
    """Load and self-check the vendor-manifest schema once per test module."""
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    format_checker = Draft202012Validator.FORMAT_CHECKER
    return Draft202012Validator(schema, format_checker=format_checker)


def _load_fixture(name: str) -> dict:
    fx = FIXTURES_DIR / name
    assert fx.exists(), f"fixture missing: {fx}"
    return yaml.safe_load(fx.read_text(encoding="utf-8"))


@pytest.mark.parametrize(
    "fixture_name",
    [
        "valid-minimal.yml",
        "valid-multi.yml",
    ],
)
def test_valid_fixture_passes(
    validator: Draft202012Validator, fixture_name: str
) -> None:
    """Each valid-*.yml fixture must parse and validate without errors."""
    instance = _load_fixture(fixture_name)
    errors = sorted(validator.iter_errors(instance), key=lambda e: e.path)
    assert errors == [], (
        f"expected {fixture_name} to validate clean, got "
        f"{[(list(e.path), e.message) for e in errors]}"
    )


@pytest.mark.parametrize(
    "fixture_name",
    [
        "invalid-missing-sha.yml",
        "invalid-bad-license.yml",
    ],
)
def test_invalid_fixture_fails(
    validator: Draft202012Validator, fixture_name: str
) -> None:
    """Each invalid-*.yml fixture must yield at least one ValidationError."""
    instance = _load_fixture(fixture_name)
    errors = list(validator.iter_errors(instance))
    assert errors, (
        f"expected {fixture_name} to fail validation, "
        "but no errors were reported"
    )
    # Sanity: every reported item really is a ValidationError.
    assert all(isinstance(e, ValidationError) for e in errors)
