"""tests/unit/scripts/dev/test_vendor_sync.py

Unit tests for scripts/dev/vendor-sync.py (task SMO-0104).

Covers the four contract scenarios:

1. ``check`` exits 0 on a valid manifest fixture.
2. ``check`` exits non-zero on a manifest missing ``pinned_commit``
   (``invalid-missing-sha.yml``).
3. ``pull`` refuses without ``--confirm-network`` and exits 2 with the right
   error message on stderr.
4. ``verify`` detects a SHA mismatch by mocking ``git rev-parse HEAD``.

All ``subprocess.run`` calls are monkey-patched; no real network, no real git
invocation. Matches the style of tests/unit/schemas/test_vendor_manifest_schema.py.
"""
from __future__ import annotations

import importlib.util
import subprocess
from pathlib import Path
from typing import Any, Callable, Sequence

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
SCRIPT_PATH = REPO_ROOT / "scripts" / "dev" / "vendor-sync.py"
SCHEMA_PATH = (
    REPO_ROOT
    / "modules"
    / "catalogs"
    / "schemas"
    / "vendor-manifest.schema.json"
)
FIXTURES_DIR = REPO_ROOT / "tests" / "fixtures" / "vendor-manifest"


def _load_module() -> Any:
    """Import scripts/dev/vendor-sync.py despite its hyphenated filename."""
    spec = importlib.util.spec_from_file_location(
        "vendor_sync", str(SCRIPT_PATH)
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def vendor_sync() -> Any:
    """Imported vendor-sync module, shared across tests in this file."""
    return _load_module()


def _common_args(manifest: Path) -> list[str]:
    return ["--manifest", str(manifest), "--schema", str(SCHEMA_PATH)]


def test_check_valid_manifest_exits_zero(
    vendor_sync: Any, capsys: pytest.CaptureFixture[str]
) -> None:
    """A clean manifest fixture must pass `check` with exit code 0."""
    fixture = FIXTURES_DIR / "valid-minimal.yml"
    assert fixture.exists(), f"fixture missing: {fixture}"
    rc = vendor_sync.main(["check", *_common_args(fixture)])
    assert rc == 0
    captured = capsys.readouterr()
    assert "OK" in captured.out
    assert "FAILED" not in captured.err


def test_check_missing_sha_exits_nonzero(
    vendor_sync: Any, capsys: pytest.CaptureFixture[str]
) -> None:
    """invalid-missing-sha.yml must fail `check` with a non-zero exit."""
    fixture = FIXTURES_DIR / "invalid-missing-sha.yml"
    assert fixture.exists(), f"fixture missing: {fixture}"
    rc = vendor_sync.main(["check", *_common_args(fixture)])
    assert rc != 0
    captured = capsys.readouterr()
    assert "FAILED schema validation" in captured.err
    # The specific failure must mention the missing pinned_commit field.
    assert "pinned_commit" in captured.err


def test_pull_without_confirm_network_exits_two(
    vendor_sync: Any, capsys: pytest.CaptureFixture[str]
) -> None:
    """`pull` without --confirm-network must exit 2 with a clear stderr message."""
    fixture = FIXTURES_DIR / "valid-minimal.yml"
    rc = vendor_sync.main(["pull", *_common_args(fixture)])
    assert rc == 2
    captured = capsys.readouterr()
    assert "--confirm-network" in captured.err
    assert "refuses to run" in captured.err


def _make_fake_run(
    head_sha: str,
) -> Callable[..., subprocess.CompletedProcess[str]]:
    """Build a fake subprocess.run that returns ``head_sha`` for rev-parse HEAD."""

    def fake_run(
        argv: Sequence[str],
        *args: Any,
        **kwargs: Any,
    ) -> subprocess.CompletedProcess[str]:
        # vendor-sync invokes ["git", "rev-parse", "HEAD"] for verify.
        assert argv[0] == "git", f"unexpected non-git invocation: {argv!r}"
        if list(argv[1:3]) == ["rev-parse", "HEAD"]:
            return subprocess.CompletedProcess(
                args=list(argv), returncode=0, stdout=head_sha + "\n", stderr=""
            )
        # Any other git call inside this test path is unexpected.
        return subprocess.CompletedProcess(
            args=list(argv), returncode=0, stdout="", stderr=""
        )

    return fake_run


def test_verify_detects_sha_mismatch(
    vendor_sync: Any,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """`verify` must exit non-zero when HEAD does not match pinned_commit."""
    fixture = FIXTURES_DIR / "valid-minimal.yml"
    # Materialise a fake clone directory with a .git marker so the entry
    # is considered "present" by _verify_entry.
    vendor_root = tmp_path / "vendor"
    fake_clone = vendor_root / "example-upstream"
    (fake_clone / ".git").mkdir(parents=True)

    # The valid-minimal fixture pins 0123...4567; return a different SHA.
    mismatched_sha = "deadbeef" * 5  # 40 hex chars, clearly different
    monkeypatch.setattr(
        vendor_sync.subprocess, "run", _make_fake_run(mismatched_sha)
    )

    rc = vendor_sync.main(
        [
            "verify",
            *_common_args(fixture),
            "--vendor-root",
            str(vendor_root),
        ]
    )
    assert rc != 0
    captured = capsys.readouterr()
    assert "does NOT match" in captured.err
    assert "mismatch" in captured.err.lower()


def test_verify_passes_on_matching_sha(
    vendor_sync: Any,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """`verify` must exit 0 when HEAD matches pinned_commit (sanity)."""
    fixture = FIXTURES_DIR / "valid-minimal.yml"
    vendor_root = tmp_path / "vendor"
    fake_clone = vendor_root / "example-upstream"
    (fake_clone / ".git").mkdir(parents=True)

    pinned_sha = "0123456789abcdef0123456789abcdef01234567"
    monkeypatch.setattr(
        vendor_sync.subprocess, "run", _make_fake_run(pinned_sha)
    )

    rc = vendor_sync.main(
        [
            "verify",
            *_common_args(fixture),
            "--vendor-root",
            str(vendor_root),
        ]
    )
    assert rc == 0
    captured = capsys.readouterr()
    assert "matches pinned_commit" in captured.out
