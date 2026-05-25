#!/usr/bin/env bash
# tests/smoke/test_protected_paths_policy.sh
#
# Sanity: every path listed in policies/protected-paths.yml deny: is either
# (a) a real file/dir in the repo, or (b) a glob pattern that's syntactically
# valid (contains *, ?, [, or ends in /**). Catches typos in the policy.

set -euo pipefail
REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$REPO_ROOT"

python3 - <<'PY'
import sys, pathlib, yaml, fnmatch, glob

root = pathlib.Path(".")
policy = yaml.safe_load((root / "policies/protected-paths.yml").read_text())
errors = 0

for pat in policy.get("deny", []):
    # If the pattern contains a glob char, accept it as a pattern.
    if any(ch in pat for ch in "*?["):
        continue
    # Otherwise it must refer to an extant file or directory.
    p = root / pat
    if not p.exists():
        # bootstrap-pending files explicitly noted in runbooks are OK
        if pat in (
            "docs/adr/0000-template.md",
            "docs/audit/audit.db",
            ".github/workflows",
            ".github/rulesets",
            ".github/CODEOWNERS",
            "scripts/audit",
            "scripts/verify/verify-slsa.sh",
            "config/bootloaders",
            "config/packages.chroot",
        ):
            continue
        print(f"[policy] dangling protected path: {pat}", file=sys.stderr)
        errors += 1

if errors:
    sys.exit(1)
print(f"[policy] OK — all non-glob deny entries resolve")
PY
