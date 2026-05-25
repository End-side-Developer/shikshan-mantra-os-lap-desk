#!/usr/bin/env bash
# .claude/hooks/pre-tool-use/load-context.sh
#
# Emits a reminder that AGENTS.md, the active task contract, and
# protected-paths.yml must be in context before any Edit/Write. Non-blocking;
# logs to stderr and adds a system-style note to the agent transcript.

set -euo pipefail

REPO_ROOT="${SHIKSHAN_REPO_ROOT:-${CLAUDE_PROJECT_DIR:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}}"
STATE_DIR="${REPO_ROOT}/.claude/.session"
SEEN_FILE="${STATE_DIR}/context-loaded"

mkdir -p "$STATE_DIR"

if [[ -f "$SEEN_FILE" ]]; then
  exit 0
fi

cat <<'EOF' >&2
[load-context] Before editing in this repo, you must have read:
  - AGENTS.md
  - PLAN.md
  - policies/protected-paths.yml
  - policies/agent-allowlist.yml
  - your active task contract under tasks/in-progress/SMO-NNNN.yml
  - the ADR linked from that task (if any)
Set SHIKSHAN_AGENT_ID and SHIKSHAN_TASK_ID env vars so audit rows attribute
correctly. This reminder fires once per session.
EOF

touch "$SEEN_FILE"
exit 0
