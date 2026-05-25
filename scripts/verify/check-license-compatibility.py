#!/usr/bin/env python3
"""Read a scancode-toolkit JSON output and reject licenses incompatible with
GPL-3.0-or-later for software, or restricted for content redistribution.

Used by ci-license-scan.yml. Exits 0 on pass, 2 on incompatible license found.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

# Conservative deny list. Add more as the project evolves; expansions require
# touches-policy approval (this script is in protected-paths deny:).
DENIED_LICENSES = {
    # Commercial-restrictive
    "commercial",
    "proprietary",
    "non-commercial",
    "academic-only",
    # GPL-3 incompatibles
    "gpl-2.0-only",                # without later-version clause
    "apsl-1.x",
    "cddl-1.0",
    "epl-1.0",                     # EPL-1.0 is GPL-incompatible; EPL-2.0 with secondary-license is OK
    "mpl-1.x",
    # Always denied
    "nokia-open-source-software-license",
    "sun-public-license",
}


def main(argv: list[str]) -> int:
    if len(argv) != 1:
        print("usage: check-license-compatibility.py <scancode.json>", file=sys.stderr)
        return 1

    path = Path(argv[0])
    if not path.exists():
        print(f"file not found: {path}", file=sys.stderr)
        return 1

    data = json.loads(path.read_text(encoding="utf-8"))

    violations: list[tuple[str, str]] = []
    for f in data.get("files", []):
        rel = f.get("path", "<unknown>")
        for lic in f.get("licenses", []) or []:
            key = (lic.get("key") or lic.get("spdx_license_key") or "").lower()
            if key in DENIED_LICENSES:
                violations.append((rel, key))

    if violations:
        print("[license] INCOMPATIBLE licenses found:", file=sys.stderr)
        for rel, key in violations:
            print(f"  {rel}: {key}", file=sys.stderr)
        print("", file=sys.stderr)
        print("Resolve by removing the file, or by an ADR carving out a per-file exception.", file=sys.stderr)
        return 2

    print(f"[license] OK — scanned {len(data.get('files', []))} files; no incompatible licenses")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
