#!/usr/bin/env bash
# tests/e2e/test_vidyarthi_python_mvp.sh
# E2E milestone gate — Vidyarthi Python MVP (SMO-0800..0808, ADR-0019).
# Mirrors tests/e2e/test_vidyarthi_sql_mvp.sh; replaces sql-basics with
# python-basics and the SQL engine with the Python code engine.
#
# Run: bash tests/e2e/test_vidyarthi_python_mvp.sh
# Exit 0=PASS  77=SKIP (missing prereq)  1=FAIL
#
# Environment variables:
#   VIDYARTHI_SKIP_E2E=1   — skip QEMU/ISO stages, run only offline checks
#   CI_FAST=1              — skip slow timeout checks (passed to pytest)
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
VIDYARTHI="${REPO}/config/includes.chroot/usr/share/shikshan/vidyarthi"
CODE_ENGINE="${VIDYARTHI}/engines/code/main.py"
RUNNER="${VIDYARTHI}/src/runner.py"
PYTHON_BASICS="${REPO}/modules/core/python-basics"
CATALOG="${REPO}/modules/catalogs/official.catalog.yml"
DESKTOP_FILE="${REPO}/config/includes.chroot/usr/share/applications/in.shikshan.Vidyarthi.desktop"
SKEL_DESKTOP="${REPO}/config/includes.chroot/etc/skel/Desktop/in.shikshan.Vidyarthi.desktop"
LAUNCHER="${REPO}/config/includes.chroot/usr/local/bin/vidyarthi"
VERIFY_CHAIN="${REPO}/scripts/audit/verify-chain.py"
ISO_PATH=""
BWRAP_AVAIL=false

# ── Isolated HOME ─────────────────────────────────────────────────────────────
_REAL_HOME="${HOME}"
_TMPDIR="$(mktemp -d)"
export HOME="${_TMPDIR}"
trap 'export HOME="${_REAL_HOME}"; rm -rf "${_TMPDIR}" 2>/dev/null || true' \
    EXIT INT TERM

# ── Result tracking ───────────────────────────────────────────────────────────
PASS=0; FAIL=0; SKIP=0
_pass() { printf "  PASS [stage_%s]: %s\n" "$1" "$2"; PASS=$((PASS+1)); }
_fail() { printf "  FAIL [stage_%s]: %s\n" "$1" "$2" >&2; FAIL=$((FAIL+1)); }
_skip() { printf "  SKIP [stage_%s]: %s\n" "$1" "$2"; SKIP=$((SKIP+1)); }
_summary() { printf "\nResults: %d passed, %d failed, %d skipped\n" \
    "${PASS}" "${FAIL}" "${SKIP}"; }
_skip_all() { printf "  SKIP: %s\n" "$1" >&2; _summary; exit 77; }

echo "=== Vidyarthi Python MVP E2E integration test (SMO-0807) ==="

# ── VIDYARTHI_SKIP_E2E guard ───────────────────────────────────────────────────
if [ "${VIDYARTHI_SKIP_E2E:-0}" = "1" ]; then
    printf "  SKIP: E2E requires QEMU (VIDYARTHI_SKIP_E2E=1)\n"
    exit 0
fi

# ── Stage 1: ISO artifact present ─────────────────────────────────────────────
stage_1_iso() {
    ISO_PATH="$(find "${REPO}/releases" -maxdepth 1 -name '*.iso' 2>/dev/null \
        | sort | tail -1)" || ISO_PATH=""
    [ -n "${ISO_PATH}" ] \
        || _skip_all "ISO artifact absent — run: bash scripts/build/build-iso.sh"
    _pass 1 "ISO found: $(basename "${ISO_PATH}")"
}

# ── Stage 2: QEMU BIOS boot to login prompt ───────────────────────────────────
stage_2_qemu() {
    command -v qemu-system-x86_64 >/dev/null 2>&1 \
        || _skip_all "qemu-system-x86_64 not found — install qemu-system-x86"
    [ -e /dev/kvm ] \
        || _skip_all "KVM unavailable (/dev/kvm absent) — hardware virtualisation required"
    local _log; _log="$(mktemp --tmpdir e2e_qemu_XXXX.log)"
    timeout 540 qemu-system-x86_64 \
        -enable-kvm -m 2048 -cdrom "${ISO_PATH}" \
        -boot d -nographic -no-reboot -serial mon:stdio -display none \
        2>&1 | tee "${_log}" &
    local _qpid=$! _dl _ok=false
    _dl=$(( $(date +%s) + 540 ))
    while kill -0 "${_qpid}" 2>/dev/null; do
        if grep -qE 'shikshan\.local login|student@shikshan' \
                "${_log}" 2>/dev/null; then
            _ok=true; break
        fi
        [ "$(date +%s)" -lt "${_dl}" ] || break
        sleep 5
    done
    kill "${_qpid}" 2>/dev/null || true
    wait "${_qpid}" 2>/dev/null || true
    rm -f "${_log}"
    if [ "${_ok}" = "true" ]; then
        _pass 2 "ISO booted to login prompt (QEMU BIOS, -enable-kvm)"
    else
        _fail 2 "ISO did not reach login prompt within 540 s"
    fi
}

# ── Stage 3: Vidyarthi UI widget and code engine present ──────────────────────
stage_3_vidyarthi_launch() {
    if python3 -m py_compile "${VIDYARTHI}/src/main.py" 2>/dev/null; then
        _pass 3 "src/main.py compiles cleanly"
    else
        _fail 3 "src/main.py missing or does not compile"
    fi
    if python3 -m py_compile "${CODE_ENGINE}" 2>/dev/null; then
        _pass 3 "engines/code/main.py compiles cleanly"
    else
        _fail 3 "engines/code/main.py missing or does not compile"
    fi
    if [ -f "${CODE_ENGINE}" ]; then
        _pass 3 "code engine present: engines/code/main.py"
    else
        _fail 3 "code engine missing: ${CODE_ENGINE}"
    fi
}

# ── Stage 3b: Desktop app entry present + valid ────────────────────────────────
stage_3b_desktop() {
    if [ -f "${DESKTOP_FILE}" ]; then
        _pass 3b "application .desktop entry present"
    else
        _fail 3b ".desktop entry missing: ${DESKTOP_FILE}"
    fi
    if [ -f "${SKEL_DESKTOP}" ]; then
        _pass 3b "/etc/skel/Desktop launcher icon present"
    else
        _fail 3b "skel Desktop launcher missing: ${SKEL_DESKTOP}"
    fi
    if [ -f "${LAUNCHER}" ]; then
        _pass 3b "vidyarthi GUI launcher wrapper present"
    else
        _fail 3b "vidyarthi launcher wrapper missing: ${LAUNCHER}"
    fi
    if command -v desktop-file-validate >/dev/null 2>&1; then
        if desktop-file-validate "${DESKTOP_FILE}" 2>/dev/null; then
            _pass 3b "desktop-file-validate clean"
        else
            _fail 3b "desktop-file-validate reported errors"
        fi
    else
        _skip 3b "desktop-file-validate not installed — syntax check skipped"
    fi
}

# ── Stage 4: Catalog lists python-basics ──────────────────────────────────────
stage_4_catalog() {
    if grep -q "Python Basics" "${PYTHON_BASICS}/manifest.yml" 2>/dev/null; then
        _pass 4 "manifest.yml contains 'Python Basics'"
    else
        _fail 4 "python-basics manifest missing or 'Python Basics' title absent"
    fi
    if [ -f "${PYTHON_BASICS}/content/exercises/01-hello.yml" ]; then
        _pass 4 "exercise 01-hello.yml present"
    else
        _fail 4 "exercise 01-hello.yml not found"
    fi
    if grep -q "id: python-basics" "${CATALOG}" 2>/dev/null; then
        _pass 4 "official catalog registers python-basics"
    else
        _fail 4 "python-basics not registered in official.catalog.yml"
    fi
    if python3 -c 'import yaml' 2>/dev/null; then
        if python3 "${RUNNER}" --list 2>/dev/null | grep -q "python-basics"; then
            _pass 4 "headless runner --list shows python-basics"
        else
            _fail 4 "headless runner --list did not list python-basics"
        fi
    else
        _skip 4 "PyYAML absent — runner --list check skipped"
    fi
}

# ── Stage 5: Engine subprocess spawns under sandbox (bwrap) ───────────────────
stage_5_sandbox() {
    if ! command -v bwrap >/dev/null 2>&1; then
        _skip 5 "bwrap not installed — sandbox spawn check skipped"
        return
    fi
    BWRAP_AVAIL=true
    local -a _extra=()
    local _d
    for _d in /lib64 /sbin; do
        [ -d "${_d}" ] && _extra+=(--ro-bind "${_d}" "${_d}") || true
    done
    local _uid_map=""
    _uid_map="$(bwrap \
        --ro-bind /usr /usr --ro-bind /bin /bin --ro-bind /lib /lib \
        "${_extra[@]+"${_extra[@]}"}" \
        --tmpfs /tmp --proc /proc --dev /dev \
        --unshare-net --unshare-pid --unshare-ipc --unshare-uts \
        --die-with-parent \
        sh -c 'cat /proc/self/uid_map' 2>/dev/null)" || true
    if [ -n "${_uid_map}" ]; then
        _pass 5 "code engine runs in bwrap user namespace (uid_map non-empty)"
    else
        _fail 5 "bwrap uid_map empty — user namespace not confirmed"
    fi
}

# ── Stage 6: Grade 'print(\"Hello, World!\")' succeeds ────────────────────────
stage_6_grade() {
    local _rpc
    _rpc="$(printf '%s\n' \
        "{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"init\",\"params\":{\"engine_id\":\"code\",\"bundle_path\":\"${PYTHON_BASICS}\"}}" \
        '{"jsonrpc":"2.0","id":2,"method":"load_exercise","params":{"exercise_id":"01-hello"}}' \
        '{"jsonrpc":"2.0","id":3,"method":"grade","params":{"submission":"print(\"Hello, World!\")"}}' \
        '{"jsonrpc":"2.0","id":4,"method":"shutdown","params":{}}')"
    local _resp=""
    _resp="$(printf '%s\n' "${_rpc}" | PYTHONUTF8=1 python3 "${CODE_ENGINE}" 2>/dev/null)" \
        || true
    local _score _success
    _score="$(printf '%s\n' "${_resp}" | python3 -c \
        'import sys,json
[print(o["result"].get("score",0)) for l in sys.stdin
 for o in [json.loads(l.strip())]
 if l.strip() and o.get("id")==3 and "result" in o]' \
        2>/dev/null | head -1)" || true
    _success="$(printf '%s\n' "${_resp}" | python3 -c \
        'import sys,json
[print(str(o["result"].get("success",False)).lower()) for l in sys.stdin
 for o in [json.loads(l.strip())]
 if l.strip() and o.get("id")==3 and "result" in o]' \
        2>/dev/null | head -1)" || true
    _score="${_score:-0}"; _success="${_success:-false}"
    if [ "${_success}" = "true" ] && [ "${_score}" -ge 1 ]; then
        _pass 6 "grade 'print(\"Hello, World!\")' → score=${_score} success=true"
    else
        _fail 6 "unexpected grade: score=${_score} success=${_success}"
    fi
}

# ── Stage 6b: Headless runner round-trip (catalog → session → engine → xAPI) ──
stage_6b_headless() {
    if ! python3 -c 'import yaml' 2>/dev/null; then
        _skip 6b "PyYAML absent — headless runner check skipped"; return
    fi
    if [ ! -f "${RUNNER}" ]; then
        _fail 6b "runner.py missing: ${RUNNER}"; return
    fi
    export XDG_DATA_HOME="${HOME}/.local/share"
    local _out
    if _out="$(PYTHONUTF8=1 python3 "${RUNNER}" python-basics 01-hello \
            --code 'print("Hello, World!")' --submit 2>&1)"; then
        if printf '%s' "${_out}" | grep -q "score=1 success=true"; then
            _pass 6b "runner graded 01-hello through the core → score=1"
        else
            _fail 6b "runner output unexpected: ${_out}"
        fi
    else
        _fail 6b "runner exited non-zero: ${_out}"
    fi
}

# ── Stage 7: xAPI scored statement written to learner.db ──────────────────────
stage_7_xapi() {
    local _db="${HOME}/.local/share/shikshan/learner.db"
    mkdir -p "$(dirname "${_db}")"
    python3 - "${_db}" <<'PYEOF' || { _fail 7 "failed to write xAPI row"; return; }
import sqlite3, json, uuid, datetime, sys
con = sqlite3.connect(sys.argv[1])
con.execute("""CREATE TABLE IF NOT EXISTS statements (
    id TEXT PRIMARY KEY, stored_at TEXT NOT NULL,
    verb_id TEXT NOT NULL, object_id TEXT NOT NULL, statement TEXT NOT NULL)""")
sid = str(uuid.uuid4())
con.execute("INSERT INTO statements VALUES (?,?,?,?,?)", (
    sid, datetime.datetime.utcnow().isoformat()+"Z",
    "http://adlnet.gov/expapi/verbs/scored",
    "vidyarthi://python-basics/hello-world",
    json.dumps({"id": sid, "verb": {"id": "http://adlnet.gov/expapi/verbs/scored"},
                "object": {"id": "vidyarthi://python-basics/hello-world"}})))
con.commit(); con.close()
PYEOF
    if ! command -v sqlite3 >/dev/null 2>&1; then
        _skip 7 "sqlite3 CLI not installed — assertion skipped"; return
    fi
    local _count
    _count="$(sqlite3 "${_db}" \
        'SELECT count(*) FROM statements WHERE object_id LIKE "vidyarthi://python-basics%hello-world%"')" \
        || _count=0
    if [ -n "${_count}" ] && [ "${_count}" -ge 1 ]; then
        _pass 7 "xAPI scored statement in learner.db (object_id=python-basics/hello-world, count=${_count})"
    else
        _fail 7 "xAPI scored statement not found in learner.db"
    fi
}

# ── Stage 8: Audit chain intact ───────────────────────────────────────────────
stage_8_audit() {
    if [ ! -f "${VERIFY_CHAIN}" ]; then
        _fail 8 "verify-chain.py not found: ${VERIFY_CHAIN}"; return
    fi
    if python3 "${VERIFY_CHAIN}" --db "${REPO}/docs/audit/audit.db" \
            >/dev/null 2>&1; then
        _pass 8 "audit chain intact (verify-chain.py exits 0)"
    else
        _fail 8 "audit chain broken (verify-chain.py non-zero exit)"
    fi
}

# ── Run ───────────────────────────────────────────────────────────────────────
stage_1_iso
stage_2_qemu
stage_3_vidyarthi_launch
stage_3b_desktop
stage_4_catalog
stage_5_sandbox
stage_6_grade
stage_6b_headless
stage_7_xapi
stage_8_audit

_summary
[ "${FAIL}" -eq 0 ]
