#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""vidyarthi-run — headless exercise runner (SMO-0612).

GTK-free terminal driver over the same catalog/session/engine path the GTK app
uses.  This is the fast end-to-end test loop: it works on the Windows dev box
(pure python3 + sqlite3), in CI, and on the OS VM — no GTK, no ISO.

Usage:
    vidyarthi-run --list
    vidyarthi-run sql-basics 01-select
    vidyarthi-run sql-basics 01-select --sql "SELECT * FROM employees;"
    vidyarthi-run sql-basics 01-select --sql-file answer.sql --submit

Exit status: 0 when graded with score 100 (or for --list / prompt display),
1 otherwise.
"""

from __future__ import annotations

import argparse
import pathlib
import sys

# Running as a script puts this src/ dir on sys.path, so sibling imports resolve
# both from the installed tree and the repo checkout.
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import catalog  # noqa: E402
from session import EngineError, ExerciseSession  # noqa: E402


def _en(d: dict, fallback: str = "") -> str:
    if isinstance(d, dict):
        return d.get("en", fallback)
    return d or fallback


def cmd_list() -> int:
    modules = catalog.list_modules()
    if not modules:
        print("No modules in catalog.", file=sys.stderr)
        return 1
    for mod in modules:
        print(f"{mod['id']}  ({_en(mod['title'], mod['id'])})")
        for ex in catalog.list_exercises(mod["id"]):
            print(f"    {ex['exercise_id']}  — {ex['title']}")
    return 0


def _print_feedback(result: dict) -> None:
    score = result.get("score", 0)
    success = result.get("success", False)
    print(f"\nscore={score} success={str(success).lower()}")
    for fb in result.get("feedback", []):
        mark = "PASS" if fb.get("passed") else "FAIL"
        msg = _en(fb.get("message", {}))
        print(f"  [{mark}] {msg}")


def cmd_run(args) -> int:
    sql = args.sql
    if args.sql_file:
        sql = pathlib.Path(args.sql_file).read_text(encoding="utf-8")

    try:
        with ExerciseSession(args.module, args.exercise, sandbox="auto") as session:
            print(f"Exercise : {args.module}/{args.exercise}")
            print(f"Prompt   : {_en(session.prompt)}")
            if sql is None:
                print(f"Starter  : {session.starter!r}")
                print("(no --sql provided; nothing graded)")
                return 0
            print(f"Submission:\n{sql.strip()}")
            result = session.submit(sql) if args.submit else session.run(sql)
            _print_feedback(result)
            if args.submit and "xapi_id" in result:
                print(f"  xAPI statement recorded: {result['xapi_id']}")
            return 0 if result.get("score", 0) == 100 else 1
    except EngineError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


def main(argv=None) -> int:
    p = argparse.ArgumentParser(
        prog="vidyarthi-run",
        description="Headless Vidyarthi exercise runner.",
    )
    p.add_argument("--list", action="store_true", help="List modules and exercises")
    p.add_argument("module", nargs="?", help="Module id, e.g. sql-basics")
    p.add_argument("exercise", nargs="?", help="Exercise id (file stem), e.g. 01-select")
    g = p.add_mutually_exclusive_group()
    g.add_argument("--sql", help="Submission SQL as a string")
    g.add_argument("--sql-file", help="Read submission SQL from a file")
    p.add_argument(
        "--submit",
        action="store_true",
        help="Record a scored xAPI statement (default: grade only)",
    )
    args = p.parse_args(argv)

    if args.list:
        return cmd_list()
    if not args.module or not args.exercise:
        p.error("module and exercise are required (or use --list)")
    return cmd_run(args)


if __name__ == "__main__":
    sys.exit(main())
