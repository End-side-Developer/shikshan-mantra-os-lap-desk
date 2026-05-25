#!/usr/bin/env bash
# .claude/hooks/stop/finalize-task.sh
#
# Runs at the end of a Claude Code session. If an active task ID is set,
# appends a final audit row marking the session boundary. Best-effort.

set -euo pipefail

REPO_ROOT="${SHIKSHAN_REPO_ROOT:-${CLAUDE_PROJECT_DIR:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}}"
TASK_ID="${SHIKSHAN_TASK_ID:-}"
ACTOR="${SHIKSHAN_AGENT_ID:-agent:claude-code}"

if [[ -z "$TASK_ID" ]]; then
  exit 0
fi

python3 "${REPO_ROOT}/scripts/audit/append-entry.py" \
  --actor "$ACTOR" \
  --action edit \
  --target "tasks/in-progress/${TASK_ID}.yml" \
  --task-id "$TASK_ID" \
  >&2 || echo "[finalize-task] audit append failed for ${TASK_ID}" >&2

# Verify chain so the agent knows whether to push or stop.
python3 "${REPO_ROOT}/scripts/audit/verify-chain.py" --quiet || {
  echo "[finalize-task] CHAIN BREAK detected — do not push. See docs/security/incident-response.md." >&2
}

exit 0
