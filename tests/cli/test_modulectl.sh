#!/usr/bin/env bash
# tests/cli/test_modulectl.sh
# Integration tests for vidyarthi-modulectl (SMO-0580).
# Run from repo root: bash tests/cli/test_modulectl.sh
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
MODULECTL="${REPO}/config/includes.chroot/usr/local/bin/vidyarthi-modulectl"
SQL_BASICS="${REPO}/modules/core/sql-basics"
PASS=0
FAIL=0

ok()   { echo "  PASS: $*"; PASS=$((PASS+1)); }
fail() { echo "  FAIL: $*" >&2; FAIL=$((FAIL+1)); }

echo "=== vidyarthi-modulectl CLI tests ==="

# 1. Script is executable and shebang is present
if [ -x "${MODULECTL}" ] && head -1 "${MODULECTL}" | grep -q "python3"; then
    ok "modulectl is executable with python3 shebang"
else
    fail "modulectl not executable or wrong shebang"
fi

# 2. --help exits 0
if python3 "${MODULECTL}" --help >/dev/null 2>&1; then
    ok "modulectl --help exits 0"
else
    fail "modulectl --help failed"
fi

# 3. validate subcommand on sql-basics passes
if python3 "${MODULECTL}" validate "${SQL_BASICS}" 2>&1 | grep -q "OK:"; then
    ok "validate sql-basics passes"
else
    fail "validate sql-basics failed"
fi

# 4. validate on a non-existent path exits non-zero
if ! python3 "${MODULECTL}" validate /nonexistent/path >/dev/null 2>&1; then
    ok "validate non-existent path exits non-zero"
else
    fail "validate non-existent path unexpectedly succeeded"
fi

# 5. verify subcommand runs (warns about unsigned, does not crash)
if python3 "${MODULECTL}" verify "${SQL_BASICS}" 2>&1; then
    ok "verify sql-basics runs without crash (may warn about unsigned)"
else
    fail "verify sql-basics crashed"
fi

# 6. list subcommand runs
if python3 "${MODULECTL}" list >/dev/null 2>&1; then
    ok "list subcommand exits 0"
else
    fail "list subcommand failed"
fi

# 7. install + remove round-trip (uses a tmp dir to avoid polluting ~)
TMP_BUNDLE="$(mktemp -d)"
# Create a minimal valid bundle
cp -r "${SQL_BASICS}/." "${TMP_BUNDLE}/test-sql-install-$$/"
ORIG_HOME="${HOME}"
export HOME="$(mktemp -d)"
if python3 "${MODULECTL}" install "${TMP_BUNDLE}/test-sql-install-$$" 2>&1 | grep -q "Installed"; then
    ok "install round-trip: module installed"
    if python3 "${MODULECTL}" list 2>&1 | grep -q "test-sql-install"; then
        ok "list shows installed module"
    else
        fail "list does not show installed module"
    fi
    if python3 "${MODULECTL}" remove "test-sql-install-$$" 2>&1 | grep -q "Removed"; then
        ok "remove: module removed"
    else
        fail "remove failed"
    fi
else
    fail "install round-trip failed"
fi
export HOME="${ORIG_HOME}"
rm -rf "${TMP_BUNDLE}" 2>/dev/null || true

echo ""
echo "Results: ${PASS} passed, ${FAIL} failed"
[ "${FAIL}" -eq 0 ]
