"""Covers the /health contract locked by ADR-0017 (decision #6).

Run from vendor/backend/::

    pytest

``pythonpath = ["src"]`` and ``testpaths = ["tests"]`` in pyproject.toml make
this importable with no install step.
"""

from fastapi.testclient import TestClient

from smo_backend.app import __version__, app

client = TestClient(app)


def test_health_returns_ok_and_version() -> None:
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok", "version": "0.1.0"}


def test_health_version_matches_package() -> None:
    """Guard against the /health payload drifting from the package version."""
    assert client.get("/health").json()["version"] == __version__
