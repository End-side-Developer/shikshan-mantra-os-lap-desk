#!/usr/bin/env bash
# .claude/hooks/pre-tool-use/protected-paths.sh
#
# Aborts any Edit/Write/MultiEdit tool call whose target path matches a glob
# in policies/protected-paths.yml `deny:`. Reads the tool input from stdin
# per the Claude Code hooks protocol and emits the abort decision on stdout.
#
# Exit codes per Claude Code hooks spec:
#   0  approve
#   2  deny (Claude is told to stop and re-plan)
#   other  non-blocking error (logged)

set -euo pipefail

REPO_ROOT="${SHIKSHAN_REPO_ROOT:-${CLAUDE_PROJECT_DIR:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}}"
POLICY="${REPO_ROOT}/policies/protected-paths.yml"

if [[ ! -f "$POLICY" ]]; then
  echo '{"continue": true, "comment": "no protected-paths policy found; passing through"}' >&2
  exit 0
fi

# Tool input arrives as JSON on stdin
INPUT="$(cat)"

# Extract the file path the tool intends to touch. Edit/Write/MultiEdit all
# use `file_path` (Write/Edit) or list of paths (MultiEdit).
PATHS="$(printf '%s' "$INPUT" | python3 -c '
import json, sys
try:
    d = json.load(sys.stdin)
    tool_input = d.get("tool_input", d)
    p = tool_input.get("file_path")
    if p:
        print(p)
    for edit in tool_input.get("edits", []) or []:
        if isinstance(edit, dict) and edit.get("file_path"):
            print(edit["file_path"])
except Exception:
    pass
')"

if [[ -z "$PATHS" ]]; then
  exit 0  # nothing to check
fi

# Convert YAML deny list into newline-separated globs
DENY_GLOBS="$(python3 -c '
import sys, yaml, pathlib
policy = yaml.safe_load(pathlib.Path(sys.argv[1]).read_text())
for g in policy.get("deny", []):
    print(g)
' "$POLICY")"

REPO_ROOT_ABS="$(cd "$REPO_ROOT" && pwd)"

while IFS= read -r ABS_PATH; do
  [[ -z "$ABS_PATH" ]] && continue
  # Normalize to repo-relative POSIX
  REL="${ABS_PATH#"$REPO_ROOT_ABS/"}"
  REL="${REL//\\//}"
  while IFS= read -r GLOB; do
    [[ -z "$GLOB" ]] && continue
    # shellcheck disable=SC2053
    case "$REL" in
      $GLOB)
        cat <<EOF
{
  "continue": false,
  "stopReason": "protected-path",
  "decision": "block",
  "reason": "Path '${REL}' matches policies/protected-paths.yml deny pattern '${GLOB}'. Require allowlist-override label + two-team approval. Per AGENTS.md §3, move task to tasks/blocked/ and ping CODEOWNERS."
}
EOF
        # Audit the attempt (best-effort; don't fail the hook if audit fails)
        python3 "${REPO_ROOT}/scripts/audit/append-entry.py" \
          --actor "${SHIKSHAN_AGENT_ID:-agent:claude-code}" \
          --action blocked-protected-path \
          --target "$REL" \
          --task-id "${SHIKSHAN_TASK_ID:-}" 2>/dev/null || true
        exit 2
        ;;
    esac
  done <<< "$DENY_GLOBS"
done <<< "$PATHS"

exit 0
