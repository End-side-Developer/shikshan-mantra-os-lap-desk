"""Shikshan Mantra OS content backend — phase-1 FastAPI app.

A single ``GET /health`` endpoint per ADR-0017 decision #6. No auth, no
catalog, no content — those are deferred to follow-up plans. ``__version__``
is the single source of truth for both the package version and the /health
payload, so the two cannot drift (see tests/test_health.py).
"""

from __future__ import annotations

from fastapi import FastAPI

__version__ = "0.1.0"

app = FastAPI(title="Shikshan Mantra OS content backend", version=__version__)


@app.get("/health")
def health() -> dict[str, str]:
    """Liveness probe. Contract locked by ADR-0017: 200 + this exact body."""
    return {"status": "ok", "version": __version__}
