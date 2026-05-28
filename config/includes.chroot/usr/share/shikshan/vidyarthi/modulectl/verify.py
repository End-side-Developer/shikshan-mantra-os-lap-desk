# SPDX-License-Identifier: GPL-2.0-or-later
"""verify — check manifest schema + cosign signature (SMO-0580)."""

import json
import pathlib

import yaml

_SCHEMA_DIR = pathlib.Path("/usr/share/shikshan/schemas")
# When running from repo: __file__ is under
# config/includes.chroot/usr/share/shikshan/vidyarthi/modulectl/
# parents[6] = repo root
_DEV_SCHEMA_DIR = pathlib.Path(__file__).parents[7] / "modules/catalogs/schemas"
# Fallback: also check relative to the chroot root
_CHROOT_SCHEMA_DIR = pathlib.Path(__file__).parents[4] / "schemas"


def _schema_dir():
    for d in (_SCHEMA_DIR, _DEV_SCHEMA_DIR, _CHROOT_SCHEMA_DIR):
        if (d / "module.schema.json").exists():
            return d
    return _DEV_SCHEMA_DIR


def validate_manifest(bundle_path: pathlib.Path) -> list[str]:
    """Return list of validation errors (empty = pass)."""
    errors = []
    manifest_path = bundle_path / "manifest.yml"
    if not manifest_path.exists():
        return [f"manifest.yml not found in {bundle_path}"]

    with manifest_path.open(encoding="utf-8") as f:
        manifest = yaml.safe_load(f)

    schema_path = _schema_dir() / "module.schema.json"
    if not schema_path.exists():
        return [f"module schema not found at {schema_path}"]

    with schema_path.open() as f:
        schema = json.load(f)

    try:
        from jsonschema import ValidationError, validate

        validate(instance=manifest, schema=schema)
    except ImportError:
        errors.append("jsonschema not installed; schema validation skipped")
    except ValidationError as exc:
        errors.append(f"manifest validation error: {exc.message}")

    return errors


def verify_signature(bundle_path: pathlib.Path) -> list[str]:
    """Verify cosign signature. Returns errors list (empty = pass or sig absent)."""
    manifest_path = bundle_path / "manifest.yml"
    with manifest_path.open(encoding="utf-8") as f:
        manifest = yaml.safe_load(f)

    sig = manifest.get("signature")
    if not sig:
        return ["signature field is null — module is unsigned (dev mode only)"]

    # Future: call cosign verify with catalog key.
    return ["cosign verification not yet implemented in CLI v0.1 (SMO-0580)"]
