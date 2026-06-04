# SPDX-License-Identifier: GPL-2.0-or-later
"""JSON-RPC 2.0 client for the Vidyarthi engine subprocess (SMO-0611).

GTK-free. Speaks the protocol from docs/architecture/vidyarthi-engine-rpc.md to
``engines/sql/main.py`` over stdio: one JSON object per line each way.

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

# Engine binary lives at <vidyarthi>/engines/sql/main.py, two levels up from
# this src/ file — true for both the installed tree and the repo checkout.
_ENGINE_DIR = pathlib.Path(__file__).resolve().parent.parent / "engines" / "sql"
_ENGINE_MAIN = _ENGINE_DIR / "main.py"
_SANDBOX_PROFILE = _ENGINE_DIR / "sandbox.bwrap"


class EngineError(RuntimeError):
    """Raised when the engine returns a JSON-RPC error or dies unexpectedly."""


class EngineClient:
    """Drive one engine subprocess for the lifetime of an exercise session."""

    def __init__(self, sandbox: str | bool = "auto"):
        self._sandbox = sandbox
        self._proc: subprocess.Popen | None = None
        self._next_id = 0

    # ── lifecycle ────────────────────────────────────────────────────────────
    def init(self, bundle_path) -> dict:
        """Spawn the engine (binding ``bundle_path`` when sandboxed) and init."""
        bundle = pathlib.Path(bundle_path).resolve()
        cmd = self._build_command(bundle)
        self._proc = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            bufsize=1,
        )
        return self._call("init", {"engine_id": "sql", "bundle_path": str(bundle)})

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
        if not self._use_sandbox():
            python = sys.executable or "python3"
            return [python, str(_ENGINE_MAIN)]

        bwrap = shutil.which("bwrap")
        cmd: list[str] = [bwrap]
        for raw in _read_profile_lines():
            tokens = raw.split()
            # Drop ro-binds whose source is absent on this host (e.g. /lib64).
            if len(tokens) == 3 and tokens[0] == "--ro-bind":
                if not pathlib.Path(tokens[1]).exists():
                    continue
            cmd.extend(tokens)
        cmd += ["--ro-bind", str(_ENGINE_DIR), str(_ENGINE_DIR)]
        cmd += ["--ro-bind", str(bundle), str(bundle)]
        cmd += ["/usr/bin/python3", str(_ENGINE_MAIN)]
        return cmd


def _read_profile_lines() -> list[str]:
    if not _SANDBOX_PROFILE.exists():
        return []
    lines = []
    for line in _SANDBOX_PROFILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            lines.append(line)
    return lines
