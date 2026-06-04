#!/usr/bin/env bash
# tests/integration/test_headless_runner.sh
# Headless end-to-end gate (SMO-0612): drives the GUI-equivalent path
# (catalog -> session -> engine subprocess -> xAPI) with no GTK and no ISO.
# Run: bash tests/integration/test_headless_runner.sh
# Exit 0=PASS  77=SKIP (missing prereq)  1=FAIL
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
RUNNER="${REPO}/config/includes.chroot/usr/share/shikshan/vidyarthi/src/runner.py"

command -v python3 >/dev/null 2>&1 || { echo "SKIP: python3 not found" >&2; exit 77; }
python3 -c 'import yaml' 2>/dev/null || { echo "SKIP: PyYAML not installed" >&2; exit 77; }
[ -f "${RUNNER}" ] || { echo "FAIL: runner.py missing at ${RUNNER}" >&2; exit 1; }

# Isolated data dir so we never touch the real learner.db.
TMP="$(mktemp -d)"
export XDG_DATA_HOME="${TMP}/data"
trap 'rm -rf "${TMP}" 2>/dev/null || true' EXIT INT TERM

PASS=0; FAIL=0
_pass() { printf "  PASS: %s\n" "$1"; PASS=$((PASS+1)); }
_fail() { printf "  FAIL: %s\n" "$1" >&2; FAIL=$((FAIL+1)); }

echo "=== Vidyarthi headless runner E2E ==="

# Stage 1: correct answer grades to 100 and exits 0.
if out="$(python3 "${RUNNER}" sql-basics 01-select \
        --sql "SELECT * FROM employees;" --submit 2>&1)"; then
    if printf '%s' "${out}" | grep -q "score=100 success=true"; then
        _pass "correct answer -> score=100 success=true (exit 0)"
    else
        _fail "expected score=100 success=true; got: ${out}"
    fi
else
    _fail "runner exited non-zero on correct answer: ${out}"
fi

# Stage 2: --submit wrote a scored xAPI row to the isolated learner.db.
DB="${XDG_DATA_HOME}/shikshan/learner.db"
count="$(python3 - "${DB}" <<'PY'
import sqlite3, sys
con = sqlite3.connect(sys.argv[1])
print(con.execute(
    "SELECT count(*) FROM statements "
    "WHERE verb_id='http://adlnet.gov/expapi/verbs/scored' "
    "AND object_id='vidyarthi://sql-basics/01-select'").fetchone()[0])
PY
)" || count=0
if [ "${count}" -ge 1 ]; then
    _pass "xAPI scored statement recorded in learner.db (count=${count})"
else
    _fail "xAPI scored statement not found in learner.db"
fi

# Stage 3: wrong answer reports failure and exits non-zero.
if python3 "${RUNNER}" sql-basics 01-select --sql "SELECT id FROM employees;" \
        >/dev/null 2>&1; then
    _fail "wrong answer unexpectedly exited 0"
else
    _pass "wrong answer reports failure (non-zero exit)"
fi

printf "\nResults: %d passed, %d failed\n" "${PASS}" "${FAIL}"
[ "${FAIL}" -eq 0 ]
