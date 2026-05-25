# Runbook — Policy Scripts Bootstrap (human-only)

The sandbox correctly enforced our own `policies/protected-paths.yml` deny list while the scaffolding agent ran. Five protected scripts need to be created by a human, then committed with two-team approval (governance + security per `policies/sensitive-change-labels.yml#touches-audit` and `touches-policy`).

**Files to create:**
- `scripts/policy/check-protected-paths.py`
- `scripts/policy/check-allowlist.py`
- `scripts/policy/check-budget.py`
- `scripts/policy/README.md`
- `scripts/verify/verify-slsa.sh`

After committing, mark each `chmod +x` (Python and shell scripts).

---

## `scripts/policy/check-protected-paths.py`

```python
#!/usr/bin/env python3
"""Reject diffs that touch any path matching policies/protected-paths.yml `deny:`.

Runs in two modes:
    --staged                  use `git diff --cached --name-only` (pre-commit)
    --base REF --head REF     use `git diff --name-only BASE..HEAD` (CI)

Exit codes:
    0  no protected paths touched
    1  CLI / I/O error
    2  diff touches a protected path
"""
from __future__ import annotations

import argparse
import fnmatch
import subprocess
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
POLICY_FILE = REPO_ROOT / "policies" / "protected-paths.yml"


def _changed_files(args):
    if args.staged:
        cmd = ["git", "diff", "--cached", "--name-only", "--diff-filter=ACMRTD"]
    else:
        cmd = ["git", "diff", "--name-only", "--diff-filter=ACMRTD", f"{args.base}..{args.head}"]
    out = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True, check=True)
    return [l.strip().replace("\\", "/") for l in out.stdout.splitlines() if l.strip()]


def main(argv):
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--staged", action="store_true")
    g.add_argument("--base", type=str)
    ap.add_argument("--head", type=str, default="HEAD")
    ap.add_argument("--allow-override-label", action="store_true")
    args = ap.parse_args(argv)

    if args.allow_override_label:
        print("[protected-paths] override label active; skipping")
        return 0

    policy = yaml.safe_load(POLICY_FILE.read_text(encoding="utf-8"))
    deny = policy.get("deny", [])
    if not deny:
        return 0

    changed = _changed_files(args)
    violations = []
    for path in changed:
        for glob in deny:
            if fnmatch.fnmatchcase(path, glob):
                violations.append((path, glob))
                break

    if violations:
        print("[protected-paths] DENIED:", file=sys.stderr)
        for p, g in violations:
            print(f"  {p}  (matches `{g}`)", file=sys.stderr)
        print("\nTo proceed: open a PR with label `allowlist-override` and two-team approval.", file=sys.stderr)
        return 2

    print(f"[protected-paths] OK — checked {len(changed)} file(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
```

## `scripts/policy/check-allowlist.py`

```python
#!/usr/bin/env python3
"""Assert all changed files are within task.I.files_in_scope AND policies/agent-allowlist.yml allow:."""
from __future__ import annotations
import argparse, fnmatch, subprocess, sys
from pathlib import Path
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
ALLOWLIST_FILE = REPO_ROOT / "policies" / "agent-allowlist.yml"


def _changed(staged, base, head):
    cmd = (["git", "diff", "--cached", "--name-only", "--diff-filter=ACMRTD"]
           if staged else
           ["git", "diff", "--name-only", "--diff-filter=ACMRTD", f"{base}..{head}"])
    out = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True, check=True)
    return [l.strip().replace("\\", "/") for l in out.stdout.splitlines() if l.strip()]


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--task", type=Path, required=True)
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--staged", action="store_true")
    src.add_argument("--base", type=str)
    ap.add_argument("--head", type=str, default="HEAD")
    ap.add_argument("--warn-only", action="store_true")
    args = ap.parse_args(argv)

    task = yaml.safe_load(args.task.read_text(encoding="utf-8"))
    files_in_scope = task.get("I", {}).get("files_in_scope", [])
    if not files_in_scope:
        print(f"[allowlist] task has empty files_in_scope", file=sys.stderr)
        return 2

    allowlist = yaml.safe_load(ALLOWLIST_FILE.read_text(encoding="utf-8"))
    allow = allowlist.get("allow", [])

    changed = _changed(args.staged, args.base, args.head)
    oos, ooa = [], []
    task_path = str(args.task).replace("\\", "/")
    for p in changed:
        if p == task_path:
            continue
        if not any(fnmatch.fnmatchcase(p, g) for g in files_in_scope):
            oos.append(p); continue
        if not any(fnmatch.fnmatchcase(p, g) for g in allow):
            ooa.append(p)

    if oos or ooa:
        for p in oos: print(f"[allowlist] OUT-OF-SCOPE  {p}", file=sys.stderr)
        for p in ooa: print(f"[allowlist] NOT-ALLOWED   {p}", file=sys.stderr)
        return 0 if args.warn_only else 2

    print(f"[allowlist] OK — {len(changed)} file(s) checked")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
```

## `scripts/policy/check-budget.py`

```python
#!/usr/bin/env python3
"""Compare PR actual usage against declared R: + policies/token-budgets.yml absolute_ceiling."""
from __future__ import annotations
import argparse, re, subprocess, sys
from pathlib import Path
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
BUDGETS_FILE = REPO_ROOT / "policies" / "token-budgets.yml"


def _parse_actuals(body):
    m = re.search(r"```yaml\s*(tokens:.*?diff_lines:.*?)```", body, re.DOTALL)
    if not m: return {}
    out = {}
    for line in m.group(1).splitlines():
        m2 = re.match(r"\s*(tokens|wall_minutes|files_changed|diff_lines):\s*([0-9]+)\s*/", line)
        if m2: out[m2.group(1)] = int(m2.group(2))
    return out


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--task", type=Path, required=True)
    ap.add_argument("--pr", type=int, required=True)
    ap.add_argument("--diff-base", type=str, required=True)
    args = ap.parse_args(argv)

    task = yaml.safe_load(args.task.read_text(encoding="utf-8"))
    declared = task["R"]
    task_type = task.get("type", "fix")
    budgets = yaml.safe_load(BUDGETS_FILE.read_text(encoding="utf-8"))
    type_cap = budgets.get("types", {}).get(task_type, budgets["defaults"])
    abs_cap = budgets["absolute_ceiling"]

    for k in ("max_tokens", "max_wall_minutes", "max_files_changed", "max_diff_lines"):
        if declared[k] > type_cap[k] or declared[k] > abs_cap[k]:
            print(f"[budget] declared {k}={declared[k]} exceeds cap", file=sys.stderr)
            return 2

    body = subprocess.check_output(
        ["gh", "pr", "view", str(args.pr), "--json", "body", "--jq", ".body"],
        cwd=str(REPO_ROOT), text=True)
    actuals = _parse_actuals(body)
    if not actuals:
        print("[budget] PR body missing 'Budget actual vs declared' block", file=sys.stderr)
        return 2

    for key, dk in (("tokens", "max_tokens"), ("wall_minutes", "max_wall_minutes"),
                     ("files_changed", "max_files_changed"), ("diff_lines", "max_diff_lines")):
        if actuals.get(key, 0) > declared[dk]:
            print(f"[budget] EXCEEDED: {key}={actuals[key]} > {dk}={declared[dk]}", file=sys.stderr)
            return 2

    print(f"[budget] OK — within declared budget")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
```

## `scripts/policy/README.md`

```markdown
# scripts/policy/

Policy enforcement scripts. Every script here is in `policies/protected-paths.yml` `deny:` — they cannot be modified without governance + security two-team approval.

| Script | Used by | Exits non-zero when |
|---|---|---|
| `check-protected-paths.py` | pre-commit, `ci-protected-paths.yml` | Changed file matches a `deny:` pattern |
| `check-allowlist.py` | pre-commit, `agent-task-validate.yml` | Changed file outside `task.I.files_in_scope` or `allow:` |
| `check-budget.py` | `agent-budget-check.yml` | Actuals exceed declared `R:` or absolute_ceiling |

These scripts ARE the policy gate. If an agent could rewrite them, the gate is theatre.
```

## `scripts/verify/verify-slsa.sh`

```bash
#!/usr/bin/env bash
# scripts/verify/verify-slsa.sh
#
# Verify SLSA L2+ in-toto provenance for a release ISO.
# Usage: bash scripts/verify/verify-slsa.sh <iso> <intoto.jsonl> [<source-tag>]
# PROTECTED: in policies/protected-paths.yml deny:.

set -euo pipefail

ISO="${1:?usage: verify-slsa.sh <iso> <intoto.jsonl> [<source-tag>]}"
ATTESTATION="${2:?usage}"
SOURCE_TAG="${3:-}"
SOURCE_URI="github.com/shikshan-mantra/shikshan-mantra-os"

if ! command -v slsa-verifier >/dev/null 2>&1; then
  echo "need slsa-verifier on PATH" >&2; exit 1
fi
[[ -f "$ISO" ]] || { echo "missing: $ISO" >&2; exit 1; }
[[ -f "$ATTESTATION" ]] || { echo "missing: $ATTESTATION" >&2; exit 1; }

EXTRA=()
[[ -n "$SOURCE_TAG" ]] && EXTRA+=(--source-tag "$SOURCE_TAG")

slsa-verifier verify-artifact "$ISO" \
  --provenance-path "$ATTESTATION" \
  --source-uri "$SOURCE_URI" \
  "${EXTRA[@]}"

echo "[verify-slsa] OK — provenance authentic for $ISO"
```

## Commit

```bash
mkdir -p scripts/policy
# Create all five files above.
chmod +x scripts/policy/*.py scripts/verify/verify-slsa.sh
git add scripts/policy/ scripts/verify/verify-slsa.sh
git commit -S -m "policy: bootstrap protected enforcement scripts (touches-policy + touches-audit)"
```

After commit, these scripts will be enforced by pre-commit hooks and by CI workflows.
