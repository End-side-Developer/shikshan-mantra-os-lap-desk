#!/usr/bin/env python3
"""Parse and validate all config/package-lists/*.list.chroot files.

Enforced invariants (SMO-0304):
  S3 - comments use `#` only; no list is empty; no duplicate package name
       within a single file; no duplicate package name across all files.
  S4 - the union of all lists contains no package from the deny set.
  S5 - the union contains at least one member from each REQUIRED_ONE_OF set,
       and at least one of REQUIRED_FONTS.

Runs as both an importable module (for pytest discovery) and an executable
script (`python3 tests/integration/test_package_lists_parse.py`). Exits with
status 1 and prints `FAIL: <reason>` lines on any failure; prints `PASS` and
summary counts on success.
"""

from __future__ import annotations

import pathlib
import re
import sys
from collections import defaultdict

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
LISTS_GLOB = "config/package-lists/*.list.chroot"
DENY_PACKAGES = {"gnome-shell", "plasma-desktop", "chromium", "vlc"}
REQUIRED_ONE_OF = [
    {"lxqt-core"},
    {"icewm"},
    {"calamares"},
    {"kolibri"},
]
REQUIRED_FONTS = {"fonts-deva", "fonts-lohit-deva"}

# A valid Debian package name token (loose check; the snapshot pin is the
# source of truth — this just rejects obvious junk like `;foo` or `//bar`).
_PKG_TOKEN_RE = re.compile(r"^[a-z0-9][a-z0-9+\-.]+$")


def _parse_file(path: pathlib.Path) -> tuple[list[str], list[str]]:
    """Return (packages, failures) for a single .list.chroot file."""
    packages: list[str] = []
    failures: list[str] = []
    seen_in_file: set[str] = set()
    for lineno, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        stripped = raw.strip()
        if not stripped:
            continue
        # Reject non-`#` comment markers anywhere a line starts.
        if stripped.startswith(";") or stripped.startswith("//"):
            failures.append(f"{path.name}:{lineno}: non-`#` comment marker (must use `#`)")
            continue
        if stripped.startswith("#"):
            continue
        # Strip inline `# ...` comments, then the leading token is the package.
        no_inline = stripped.split("#", 1)[0].strip()
        if not no_inline:
            continue
        token = no_inline.split()[0]
        if not _PKG_TOKEN_RE.match(token):
            failures.append(f"{path.name}:{lineno}: invalid package token {token!r}")
            continue
        if token in seen_in_file:
            failures.append(f"{path.name}:{lineno}: duplicate package within file: {token}")
            continue
        seen_in_file.add(token)
        packages.append(token)
    return packages, failures


def _collect() -> tuple[dict[str, list[str]], list[str]]:
    per_file: dict[str, list[str]] = {}
    failures: list[str] = []
    paths = sorted(REPO_ROOT.glob(LISTS_GLOB))
    if not paths:
        failures.append(f"no files matched glob {LISTS_GLOB!r}")
        return per_file, failures
    for path in paths:
        pkgs, file_failures = _parse_file(path)
        failures.extend(file_failures)
        if not pkgs:
            failures.append(f"{path.name}: list is empty (no packages)")
        per_file[path.name] = pkgs
    return per_file, failures


def _validate(per_file: dict[str, list[str]]) -> list[str]:
    failures: list[str] = []

    # Cross-file duplicates.
    origin: dict[str, list[str]] = defaultdict(list)
    for fname, pkgs in per_file.items():
        for pkg in pkgs:
            origin[pkg].append(fname)
    for pkg, fnames in sorted(origin.items()):
        if len(fnames) > 1:
            failures.append(f"duplicate package across lists: {pkg} -> {', '.join(fnames)}")

    union = set(origin.keys())

    # Deny set.
    denied = sorted(union & DENY_PACKAGES)
    if denied:
        failures.append(f"deny-set packages present: {', '.join(denied)}")

    # Required-one-of.
    for required in REQUIRED_ONE_OF:
        if not (union & required):
            failures.append(f"none of required-one-of present: {sorted(required)}")

    # Required fonts.
    if not (union & REQUIRED_FONTS):
        failures.append(f"no Devanagari font present; expected one of {sorted(REQUIRED_FONTS)}")

    return failures


def main() -> int:
    per_file, failures = _collect()
    failures.extend(_validate(per_file))

    if failures:
        for msg in failures:
            print(f"FAIL: {msg}")
        return 1

    total = sum(len(p) for p in per_file.values())
    print("PASS")
    print(f"  files:    {len(per_file)}")
    print(f"  packages: {total} (union: {len({p for ps in per_file.values() for p in ps})})")
    for fname, pkgs in sorted(per_file.items()):
        print(f"    {fname}: {len(pkgs)}")
    return 0


# pytest entrypoint -------------------------------------------------------


def test_package_lists_parse() -> None:
    per_file, failures = _collect()
    failures.extend(_validate(per_file))
    assert not failures, "package list validation failed:\n" + "\n".join(failures)


if __name__ == "__main__":
    sys.exit(main())
