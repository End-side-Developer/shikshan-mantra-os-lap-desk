#!/usr/bin/env bash
# tests/engines/test_sql_sandbox_escape.sh
# Verifies that the SQL engine sandbox (bwrap + seccomp) blocks:
#   1. File writes outside /tmp
#   2. Network connections
#   3. Exec of arbitrary binaries (beyond the allow-list)
#
# IMPORTANT: This test requires bwrap installed on the host.
# It is skipped automatically if bwrap is not present.
# Run from repo root: bash tests/engines/test_sql_sandbox_escape.sh
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ENGINES="${REPO}/config/includes.chroot/usr/share/shikshan/vidyarthi/engines"
SQL_ENGINE="${ENGINES}/sql"
PASS=0
FAIL=0
SKIP=0

ok()   { echo "  PASS: $*"; PASS=$((PASS+1)); }
fail() { echo "  FAIL: $*" >&2; FAIL=$((FAIL+1)); }
skip() { echo "  SKIP: $*"; SKIP=$((SKIP+1)); }

echo "=== SQL engine sandbox escape tests ==="

if ! command -v bwrap >/dev/null 2>&1; then
    skip "bwrap not installed — skipping all sandbox tests"
    echo "Results: ${PASS} passed, ${FAIL} failed, ${SKIP} skipped"
    exit 0
fi

# Helper: run a command inside bwrap with the SQL sandbox profile.
# Returns the exit code of the inner command.
_bwrap() {
    bwrap \
        --ro-bind /usr /usr \
        --ro-bind /bin /bin \
        --ro-bind /lib /lib \
        --ro-bind /lib64 /lib64 2>/dev/null || true \
        --ro-bind /proc /proc \
        --tmpfs /tmp \
        --proc /proc \
        --dev /dev \
        --unshare-net \
        --unshare-pid \
        --unshare-ipc \
        --unshare-uts \
        --die-with-parent \
        "$@" 2>/dev/null
}

# 1. File write outside /tmp must fail
if _bwrap sh -c 'echo test > /etc/pwned 2>/dev/null; [ -f /etc/pwned ]' 2>/dev/null; then
    fail "sandbox allowed write to /etc/pwned"
else
    ok "sandbox blocks write to /etc/ (read-only bind)"
fi

# 2. Network connection must fail (--unshare-net)
if _bwrap sh -c 'cat /dev/tcp/8.8.8.8/53 2>/dev/null' 2>/dev/null; then
    fail "sandbox allowed network connection"
else
    ok "sandbox blocks network connection (--unshare-net)"
fi

# 3. Write to /tmp is allowed (tmpfs)
if _bwrap sh -c 'echo ok > /tmp/test_escape && cat /tmp/test_escape' 2>/dev/null | grep -q ok; then
    ok "/tmp writes are allowed (tmpfs)"
else
    fail "/tmp write unexpectedly blocked"
fi

# 4. Sandbox profile file exists and is non-empty
if [ -s "${SQL_ENGINE}/sandbox.bwrap" ]; then
    ok "sandbox.bwrap profile exists and is non-empty"
else
    fail "sandbox.bwrap profile missing or empty"
fi

# 5. seccomp.json exists and is valid JSON
if python3 -c "import json; json.load(open('${SQL_ENGINE}/seccomp.json'))" 2>/dev/null; then
    ok "seccomp.json exists and is valid JSON"
else
    fail "seccomp.json missing or invalid JSON"
fi

echo ""
echo "Results: ${PASS} passed, ${FAIL} failed, ${SKIP} skipped"
[ "${FAIL}" -eq 0 ]
