#!/usr/bin/env python3
# scripts/dev/vendor-sync.py
#
# Vendor-sync tool for Shikshan Mantra OS, per ADR-0003
# (docs/adr/0003-vendor-strategy.md) and task SMO-0104.
#
# Subcommands:
#   check  -- load and schema-validate vendor/MANIFEST.yml; exit non-zero on
#             any validation failure.
#   pull   -- clone each manifest entry into vendor/<name>/ at its pinned
#             commit. Refuses to run without --confirm-network.
#   verify -- for each materialised vendor/<name>/, assert HEAD matches the
#             pinned SHA in MANIFEST. Exits non-zero on any mismatch.
#
# Imports are limited to Python stdlib + PyYAML + jsonschema, per the task
# contract. No network library is imported; network access is only ever
# achieved via subprocess calls to the local `git` binary, gated by
# --confirm-network in `pull` mode.
#
# Exit codes (documented per scripts/README.md convention):
#   0   success
#   1   schema validation failed, manifest unreadable, or sync mismatch
#   2   misuse (e.g. `pull` invoked without --confirm-network)
"""Vendor manifest check / pull / verify tool for Shikshan Mantra OS."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Iterable, Sequence

import yaml
from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError

LOG_PREFIX = "[vendor-sync]"

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_MANIFEST = REPO_ROOT / "vendor" / "MANIFEST.yml"
DEFAULT_SCHEMA = (
    REPO_ROOT
    / "modules"
    / "catalogs"
    / "schemas"
    / "vendor-manifest.schema.json"
)
DEFAULT_VENDOR_ROOT = REPO_ROOT / "vendor"


def _log(msg: str) -> None:
    """Emit a pipeline-diffable log line on stdout."""
    print(f"{LOG_PREFIX} {msg}")


def _err(msg: str) -> None:
    """Emit a pipeline-diffable log line on stderr."""
    print(f"{LOG_PREFIX} {msg}", file=sys.stderr)


def load_manifest(manifest_path: Path) -> dict[str, Any]:
    """Read a YAML manifest from disk and return the parsed object."""
    if not manifest_path.exists():
        raise FileNotFoundError(f"manifest not found: {manifest_path}")
    data = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    if data is None:
        # Treat an empty file as an empty mapping for downstream schema check.
        data = {}
    if not isinstance(data, dict):
        raise ValueError(
            f"manifest root must be a mapping, got {type(data).__name__}"
        )
    return data


def load_validator(schema_path: Path) -> Draft202012Validator:
    """Load and self-check the vendor-manifest schema."""
    if not schema_path.exists():
        raise FileNotFoundError(f"schema not found: {schema_path}")
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(
        schema, format_checker=Draft202012Validator.FORMAT_CHECKER
    )


def validate_manifest(
    manifest: dict[str, Any], validator: Draft202012Validator
) -> list[ValidationError]:
    """Return all schema errors for ``manifest`` (empty list if clean)."""
    return sorted(validator.iter_errors(manifest), key=lambda e: list(e.path))


def _iter_entries(manifest: dict[str, Any]) -> Iterable[dict[str, Any]]:
    """Yield each upstream entry from a parsed manifest."""
    for entry in manifest.get("upstreams", []) or []:
        if isinstance(entry, dict):
            yield entry


def _select_entries(
    manifest: dict[str, Any], only: str | None
) -> list[dict[str, Any]]:
    """Filter entries by ``--only NAME`` if provided."""
    entries = list(_iter_entries(manifest))
    if only is None:
        return entries
    return [e for e in entries if e.get("name") == only]


def cmd_check(args: argparse.Namespace) -> int:
    """Subcommand: validate the manifest against the schema."""
    manifest_path = Path(args.manifest)
    schema_path = Path(args.schema)

    try:
        manifest = load_manifest(manifest_path)
        validator = load_validator(schema_path)
    except (FileNotFoundError, ValueError, json.JSONDecodeError) as exc:
        _err(f"check: {exc}")
        return 1
    except yaml.YAMLError as exc:
        _err(f"check: manifest is not valid YAML: {exc}")
        return 1

    errors = validate_manifest(manifest, validator)
    entries = list(_iter_entries(manifest))

    if errors:
        _err(
            f"check: {manifest_path} FAILED schema validation "
            f"({len(errors)} error(s))"
        )
        for err in errors:
            path = "/".join(str(p) for p in err.path) or "<root>"
            _err(f"  at {path}: {err.message}")
        return 1

    _log(f"check: {manifest_path} OK ({len(entries)} upstream entry/entries)")
    for entry in entries:
        _log(
            f"  - {entry.get('name', '<unnamed>')} "
            f"@ {entry.get('pinned_commit', '<no-sha>')[:12]} "
            f"({entry.get('license', '<no-license>')})"
        )
    return 0


def _run_git(
    cmd: Sequence[str], cwd: Path | None = None
) -> subprocess.CompletedProcess[str]:
    """Run a git subprocess and return the completed process."""
    return subprocess.run(
        ["git", *cmd],
        cwd=str(cwd) if cwd is not None else None,
        check=False,
        capture_output=True,
        text=True,
    )


def _pull_entry(entry: dict[str, Any], vendor_root: Path) -> bool:
    """Clone and check out a single entry. Return True on success."""
    name = entry["name"]
    url = entry["upstream_url"]
    sha = entry["pinned_commit"]
    dest = vendor_root / name

    if (dest / ".git").exists():
        _log(f"pull: {name}: clone already present, skipping clone step")
    else:
        dest.parent.mkdir(parents=True, exist_ok=True)
        _log(f"pull: {name}: cloning {url} (depth=1) -> {dest}")
        clone = _run_git(["clone", "--depth=1", url, str(dest)])
        if clone.returncode != 0:
            _err(f"pull: {name}: git clone failed: {clone.stderr.strip()}")
            return False

    _log(f"pull: {name}: fetching pinned commit {sha[:12]}")
    fetch = _run_git(["fetch", "origin", sha], cwd=dest)
    if fetch.returncode != 0:
        _err(f"pull: {name}: git fetch failed: {fetch.stderr.strip()}")
        return False

    _log(f"pull: {name}: checking out {sha[:12]}")
    checkout = _run_git(["checkout", sha], cwd=dest)
    if checkout.returncode != 0:
        _err(f"pull: {name}: git checkout failed: {checkout.stderr.strip()}")
        return False

    return True


def cmd_pull(args: argparse.Namespace) -> int:
    """Subcommand: materialise vendor clones at their pinned commits."""
    if not args.confirm_network:
        _err(
            "pull: refuses to run without --confirm-network. This subcommand "
            "performs network git clones; pass --confirm-network to proceed."
        )
        return 2

    manifest_path = Path(args.manifest)
    schema_path = Path(args.schema)
    vendor_root = Path(args.vendor_root)

    try:
        manifest = load_manifest(manifest_path)
        validator = load_validator(schema_path)
    except (FileNotFoundError, ValueError, json.JSONDecodeError) as exc:
        _err(f"pull: {exc}")
        return 1
    except yaml.YAMLError as exc:
        _err(f"pull: manifest is not valid YAML: {exc}")
        return 1

    errors = validate_manifest(manifest, validator)
    if errors:
        _err(
            "pull: refuses to run against an invalid manifest "
            f"({len(errors)} schema error(s)); run `check` for details"
        )
        return 1

    entries = _select_entries(manifest, args.only)
    if args.only is not None and not entries:
        _err(f"pull: --only={args.only!r} matched no manifest entry")
        return 1

    failures = 0
    for entry in entries:
        if not _pull_entry(entry, vendor_root):
            failures += 1

    if failures:
        _err(f"pull: {failures} entry/entries failed")
        return 1

    _log(f"pull: {len(entries)} entry/entries materialised at pinned commits")
    return 0


def _verify_entry(entry: dict[str, Any], vendor_root: Path) -> tuple[bool, str]:
    """Verify a single entry. Return (ok, message)."""
    name = entry["name"]
    expected = entry["pinned_commit"]
    dest = vendor_root / name

    if not (dest / ".git").exists():
        return False, f"{name}: not materialised (no {dest}/.git)"

    proc = _run_git(["rev-parse", "HEAD"], cwd=dest)
    if proc.returncode != 0:
        return False, f"{name}: git rev-parse HEAD failed: {proc.stderr.strip()}"

    head = proc.stdout.strip()
    if head != expected:
        return (
            False,
            f"{name}: HEAD={head[:12]} does NOT match "
            f"pinned_commit={expected[:12]}",
        )
    return True, f"{name}: HEAD matches pinned_commit {expected[:12]}"


def cmd_verify(args: argparse.Namespace) -> int:
    """Subcommand: assert each clone's HEAD matches its pinned SHA."""
    manifest_path = Path(args.manifest)
    schema_path = Path(args.schema)
    vendor_root = Path(args.vendor_root)

    try:
        manifest = load_manifest(manifest_path)
        validator = load_validator(schema_path)
    except (FileNotFoundError, ValueError, json.JSONDecodeError) as exc:
        _err(f"verify: {exc}")
        return 1
    except yaml.YAMLError as exc:
        _err(f"verify: manifest is not valid YAML: {exc}")
        return 1

    errors = validate_manifest(manifest, validator)
    if errors:
        _err(
            "verify: refuses to run against an invalid manifest "
            f"({len(errors)} schema error(s)); run `check` for details"
        )
        return 1

    entries = _select_entries(manifest, args.only)
    if args.only is not None and not entries:
        _err(f"verify: --only={args.only!r} matched no manifest entry")
        return 1

    mismatches = 0
    checked = 0
    for entry in entries:
        ok, message = _verify_entry(entry, vendor_root)
        if ok:
            _log(f"verify: {message}")
            checked += 1
        else:
            _err(f"verify: {message}")
            mismatches += 1

    if mismatches:
        _err(
            f"verify: {mismatches} mismatch(es) across "
            f"{len(entries)} entry/entries"
        )
        return 1

    _log(f"verify: {checked} entry/entries match their pinned commit")
    return 0


def build_parser() -> argparse.ArgumentParser:
    """Construct the top-level argparse parser."""
    parser = argparse.ArgumentParser(
        prog="vendor-sync",
        description=(
            "Vendor manifest tool: check / pull / verify "
            "vendor/MANIFEST.yml per ADR-0003."
        ),
    )
    sub = parser.add_subparsers(dest="subcommand", required=True)

    def _add_common(sp: argparse.ArgumentParser) -> None:
        sp.add_argument(
            "--manifest",
            default=str(DEFAULT_MANIFEST),
            help="Path to vendor manifest YAML (default: vendor/MANIFEST.yml)",
        )
        sp.add_argument(
            "--schema",
            default=str(DEFAULT_SCHEMA),
            help=(
                "Path to vendor-manifest JSON Schema "
                "(default: modules/catalogs/schemas/vendor-manifest.schema.json)"
            ),
        )

    sp_check = sub.add_parser(
        "check", help="Validate manifest against schema."
    )
    _add_common(sp_check)
    sp_check.set_defaults(func=cmd_check)

    sp_pull = sub.add_parser(
        "pull",
        help="Clone manifest entries at pinned commits (requires network).",
    )
    _add_common(sp_pull)
    sp_pull.add_argument(
        "--vendor-root",
        default=str(DEFAULT_VENDOR_ROOT),
        help="Directory under which vendor/<name>/ clones are written.",
    )
    sp_pull.add_argument(
        "--confirm-network",
        action="store_true",
        help="Required gate: opt in to network git operations.",
    )
    sp_pull.add_argument(
        "--only",
        default=None,
        help="Restrict to a single manifest entry by name.",
    )
    sp_pull.set_defaults(func=cmd_pull)

    sp_verify = sub.add_parser(
        "verify",
        help="Assert each materialised clone's HEAD matches its pinned SHA.",
    )
    _add_common(sp_verify)
    sp_verify.add_argument(
        "--vendor-root",
        default=str(DEFAULT_VENDOR_ROOT),
        help="Directory under which vendor/<name>/ clones live.",
    )
    sp_verify.add_argument(
        "--only",
        default=None,
        help="Restrict to a single manifest entry by name.",
    )
    sp_verify.set_defaults(func=cmd_verify)

    return parser


def main(argv: list[str] | None = None) -> int:
    """Top-level entry point. Returns a process exit code."""
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":  # pragma: no cover - thin wrapper
    sys.exit(main())
