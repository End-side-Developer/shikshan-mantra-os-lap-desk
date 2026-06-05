# SPDX-License-Identifier: GPL-2.0-or-later
"""JSON-RPC 2.0 client for the Vidyarthi engine subprocess (SMO-0611, SMO-0805).

GTK-free. Speaks the protocol from docs/architecture/vidyarthi-engine-rpc.md to
the appropriate engine subprocess (sql, code, …) over stdio: one JSON object per
line each way. The engine is selected by reading ``sub_engine`` from the module
manifest in the bundle at ``init()`` time (ADR-0019).

The engine is spawned directly by default.  On Linux, when ``bwrap`` is present
(and ``VIDYARTHI_SANDBOX`` is not ``0``), the engine is wrapped with the
``sandbox.bwrap`` namespace profile (ADR-0015).  Seccomp is left to the engine
host; this client provides the network/PID/IPC isolation that matters for the
"no network" guarantee.  Direct spawn keeps the dev/test path working on Windows.
"""

from __future__ import annotations

import json
import os
import pathlib
import platform
import shutil
import subprocess
import sys

import yaml

# Root of the engines directory: <vidyarthi>/engines/
_ENGINES_ROOT = pathlib.Path(__file__).resolve().parent.parent / "engines"
_SUPPORTED_SUB_ENGINES = frozenset({"sql", "code"})


def _engine_dirs(sub_engine: str) -> tuple[pathlib.Path, pathlib.Path]:
    """Return (engine_dir, sandbox_profile) for the given sub_engine."""
    if sub_engine not in _SUPPORTED_SUB_ENGINES:
        raise ValueError(
            f"unsupported sub_engine {sub_engine!r}; "
            f"supported: {sorted(_SUPPORTED_SUB_ENGINES)}"
        )
    engine_dir = _ENGINES_ROOT / sub_engine
    return engine_dir, engine_dir / "sandbox.bwrap"


def _read_sub_engine(bundle: pathlib.Path) -> str:
    """Read sub_engine from the module manifest; default to 'sql' if absent."""
    manifest = bundle / "manifest.yml"
    if manifest.exists():
        try:
            data = yaml.safe_load(manifest.read_text(encoding="utf-8")) or {}
            return data.get("sub_engine", "sql")
        except (OSError, yaml.YAMLError):
            pass
    return "sql"


class EngineError(RuntimeError):
    """Raised when the engine returns a JSON-RPC error or dies unexpectedly."""


class EngineClient:
    """Drive one engine subprocess for the lifetime of an exercise session."""

    def __init__(self, sandbox: str | bool = "auto"):
        self._sandbox = sandbox
        self._proc: subprocess.Popen | None = None
        self._next_id = 0
        self._sub_engine: str = "sql"
        self._engine_dir: pathlib.Path = _ENGINES_ROOT / "sql"
        self._sandbox_profile: pathlib.Path = _ENGINES_ROOT / "sql" / "sandbox.bwrap"

    # ── lifecycle ────────────────────────────────────────────────────────────
    def init(self, bundle_path) -> dict:
        """Spawn the engine (binding ``bundle_path`` when sandboxed) and init.

        Reads ``sub_engine`` from the module manifest inside bundle_path to
        select the correct engine binary (engines/sql/main.py, engines/code/main.py,
        etc.) — no caller change required (ADR-0019, SMO-0805).
        """
        bundle = pathlib.Path(bundle_path).resolve()
        self._sub_engine = _read_sub_engine(bundle)
        self._engine_dir, self._sandbox_profile = _engine_dirs(self._sub_engine)
        cmd = self._build_command(bundle)
        self._proc = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            bufsize=1,
        )
        return self._call("init", {"engine_id": self._sub_engine, "bundle_path": str(bundle)})

    def load_exercise(self, exercise_id: str) -> dict:
        return self._call("load_exercise", {"exercise_id": exercise_id})

    def grade(self, submission: str) -> dict:
        return self._call("grade", {"submission": submission})

    def shutdown(self) -> None:
        if self._proc is None:
            return
        try:
            self._call("shutdown", {})
        except EngineError:
            pass
        finally:
            self.close()

    def close(self) -> None:
        if self._proc is None:
            return
        try:
            if self._proc.stdin:
                self._proc.stdin.close()
            self._proc.wait(timeout=5)
        except Exception:
            self._proc.kill()
        finally:
            self._proc = None

    # ── context manager ──────────────────────────────────────────────────────
    def __enter__(self) -> "EngineClient":
        return self

    def __exit__(self, *_exc) -> None:
        self.shutdown()

    # ── internals ────────────────────────────────────────────────────────────
    def _call(self, method: str, params: dict) -> dict:
        if self._proc is None or self._proc.stdin is None or self._proc.stdout is None:
            raise EngineError("engine not started")
        self._next_id += 1
        req_id = self._next_id
        req = {"jsonrpc": "2.0", "id": req_id, "method": method, "params": params}
        try:
            self._proc.stdin.write(json.dumps(req) + "\n")
            self._proc.stdin.flush()
        except (BrokenPipeError, ValueError) as exc:
            raise EngineError(f"engine stdin closed: {exc}") from exc

        while True:
            line = self._proc.stdout.readline()
            if line == "":
                raise EngineError(
                    f"engine exited before answering {method!r} " f"(rc={self._proc.poll()})"
                )
            line = line.strip()
            if not line:
                continue
            try:
                msg = json.loads(line)
            except json.JSONDecodeError:
                continue  # ignore stray non-JSON output
            if msg.get("id") != req_id:
                continue
            if "error" in msg:
                err = msg["error"]
                raise EngineError(f"{method}: {err.get('message')} ({err.get('code')})")
            return msg.get("result", {})

    def _use_sandbox(self) -> bool:
        if self._sandbox is True:
            return shutil.which("bwrap") is not None
        if self._sandbox is False:
            return False
        # "auto"
        if os.environ.get("VIDYARTHI_SANDBOX") == "0":
            return False
        return platform.system() == "Linux" and shutil.which("bwrap") is not None

    def _build_command(self, bundle: pathlib.Path) -> list[str]:
        engine_main = self._engine_dir / "main.py"
        if not self._use_sandbox():
            python = sys.executable or "python3"
            return [python, str(engine_main)]

        bwrap = shutil.which("bwrap")
        cmd: list[str] = [bwrap]
        for raw in _read_profile_lines(self._sandbox_profile):
            tokens = raw.split()
            # Drop ro-binds whose source is absent on this host (e.g. /lib64).
            if len(tokens) == 3 and tokens[0] == "--ro-bind":
                if not pathlib.Path(tokens[1]).exists():
                    continue
            cmd.extend(tokens)
        cmd += ["--ro-bind", str(self._engine_dir), str(self._engine_dir)]
        cmd += ["--ro-bind", str(bundle), str(bundle)]
        cmd += ["/usr/bin/python3", str(engine_main)]
        return cmd


def _read_profile_lines(profile: pathlib.Path) -> list[str]:
    if not profile.exists():
        return []
    lines = []
    for line in profile.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            lines.append(line)
    return lines
