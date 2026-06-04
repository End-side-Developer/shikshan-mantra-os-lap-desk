# SPDX-License-Identifier: GPL-2.0-or-later
"""ExerciseSession — orchestrates one exercise end-to-end (SMO-0611).

GTK-free glue over catalog + engine_client + xapi.  This is the single code
path that both the GTK window and the headless runner drive, so testing the
session exercises the whole real pipeline (engine subprocess included).
"""

from __future__ import annotations

import catalog
import xapi
from engine_client import EngineClient, EngineError

__all__ = ["ExerciseSession", "EngineError"]


class ExerciseSession:
    """A live engine session bound to one (module, exercise)."""

    def __init__(self, module_id: str, exercise_id: str, sandbox="auto"):
        self.module_id = module_id
        self.exercise_id = exercise_id
        self._client = EngineClient(sandbox=sandbox)
        self.prompt: dict = {}
        self.starter: str = ""
        self.hints: list = []
        self._open = False

    # ── lifecycle ────────────────────────────────────────────────────────────
    def open(self) -> "ExerciseSession":
        bundle = catalog.resolve_bundle_path(self.module_id)
        if bundle is None:
            raise EngineError(f"module not found: {self.module_id}")
        self._client.init(bundle)
        loaded = self._client.load_exercise(self.exercise_id)
        spec = catalog.load_exercise_spec(self.module_id, self.exercise_id) or {}
        self.prompt = loaded.get("prompt") or spec.get("prompt", {})
        self.starter = loaded.get("starter", spec.get("starter_sql", ""))
        self.hints = spec.get("hints", [])
        self._open = True
        return self

    def close(self) -> None:
        if self._open:
            self._client.shutdown()
            self._open = False

    def __enter__(self) -> "ExerciseSession":
        return self.open()

    def __exit__(self, *_exc) -> None:
        self.close()

    # ── grading ──────────────────────────────────────────────────────────────
    def run(self, sql: str) -> dict:
        """Grade a submission without persisting telemetry (the [Run] button)."""
        if not self._open:
            self.open()
        return self._client.grade(sql)

    def submit(self, sql: str) -> dict:
        """Grade and record a scored xAPI statement (the [Submit] button)."""
        result = self.run(sql)
        result["xapi_id"] = xapi.record_scored(
            self.module_id,
            self.exercise_id,
            result.get("score", 0),
            result.get("success", False),
        )
        return result
