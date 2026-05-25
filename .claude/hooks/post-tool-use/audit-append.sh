#!/usr/bin/env bash
# .claude/hooks/post-tool-use/audit-append.sh
#
# After a successful Edit/Write/MultiEdit, write one row per touched path
# to docs/audit/audit.db via scripts/audit/append-entry.py. Computes the
# diff against HEAD using `git diff -- <path>` and pipes it into the
# appender as the diff source.
#
# Non-blocking: a failure here logs to stderr but does not abort the agent
# (the chain-integrity check in pre-push enforces eventual consistency).

set -euo pipefail

REPO_ROOT="${SHIKSHAN_REPO_ROOT:-${CLAUDE_PROJECT_DIR:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}}"
INPUT="$(cat)"

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

[[ -z "$PATHS" ]] && exit 0

TOOL_NAME="$(printf '%s' "$INPUT" | python3 -c '
import json, sys
try:
    d = json.load(sys.stdin)
    print(d.get("tool_name", "Edit"))
except Exception:
    print("Edit")
')"

case "$TOOL_NAME" in
  Write)     ACTION=write ;;
  Edit|MultiEdit) ACTION=edit ;;
  *)         ACTION=edit ;;
esac

ACTOR="${SHIKSHAN_AGENT_ID:-agent:claude-code}"
TASK_ID="${SHIKSHAN_TASK_ID:-}"
REPO_ROOT_ABS="$(cd "$REPO_ROOT" && pwd)"

while IFS= read -r ABS_PATH; do
  [[ -z "$ABS_PATH" ]] && continue
  REL="${ABS_PATH#"$REPO_ROOT_ABS/"}"
  REL="${REL//\\//}"

  # Capture diff for hashing (empty diff if file is new and not yet committed)
  TMPDIFF="$(mktemp)"
  ( cd "$REPO_ROOT" && git diff -- "$REL" > "$TMPDIFF" ) 2>/dev/null || true

  python3 "${REPO_ROOT}/scripts/audit/append-entry.py" \
    --actor "$ACTOR" \
    --action "$ACTION" \
    --target "$REL" \
    --diff-file "$TMPDIFF" \
    ${TASK_ID:+--task-id "$TASK_ID"} \
    >&2 || echo "[audit-append] failed for $REL" >&2

  rm -f "$TMPDIFF"
done <<< "$PATHS"

exit 0
