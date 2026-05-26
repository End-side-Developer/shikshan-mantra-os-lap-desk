#!/usr/bin/env bash
# tests/integration/test_qemu_run_smoke_xml.sh
#
# Validates run-smoke.sh: JUnit XML shape + exit-code propagation.
# Stubs boot-bios.sh and boot-uefi.sh via BOOT_BIOS / BOOT_UEFI env vars
# (PATH-prepend cannot intercept scripts resolved by absolute path inside
# run-smoke.sh, so we use the injection seam it exposes instead).

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
RUN_SMOKE="$REPO_ROOT/tests/qemu/run-smoke.sh"

PASS=0
FAIL=0

fail() { echo "FAIL: $*" >&2; FAIL=$(( FAIL + 1 )); }
pass() { echo "PASS: $*";    PASS=$(( PASS + 1 )); }

# ── Setup ─────────────────────────────────────────────────────────────────────

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

STUB_DIR="$TMP/stubs"
mkdir -p "$STUB_DIR"

make_stub_pass() {
  local name="$1"
  cat >"$STUB_DIR/$name.sh" <<EOF
#!/usr/bin/env bash
echo "[stub] $name success (iso=\$1)"
exit 0
EOF
  chmod +x "$STUB_DIR/$name.sh"
}

make_stub_fail() {
  local name="$1" rc="${2:-2}"
  cat >"$STUB_DIR/$name.sh" <<EOF
#!/usr/bin/env bash
echo "[stub] $name failed (iso=\$1)"
exit $rc
EOF
  chmod +x "$STUB_DIR/$name.sh"
}

assert_contains() {
  local file="$1" pattern="$2" label="$3"
  if grep -qE "$pattern" "$file"; then
    pass "$label"
  else
    fail "$label — pattern /$pattern/ not found in $file"
    echo "--- $file ---" >&2; cat "$file" >&2
  fi
}

assert_not_contains() {
  local file="$1" pattern="$2" label="$3"
  if grep -qE "$pattern" "$file"; then
    fail "$label — unexpected pattern /$pattern/ found in $file"
    echo "--- $file ---" >&2; cat "$file" >&2
  else
    pass "$label"
  fi
}

find_run_dir() {
  find "$1" -maxdepth 1 -type d -name 'run-*' | head -n 1
}

# ── Case 1: both legs pass ────────────────────────────────────────────────────

make_stub_pass boot-bios
make_stub_pass boot-uefi

export BOOT_BIOS="$STUB_DIR/boot-bios.sh"
export BOOT_UEFI="$STUB_DIR/boot-uefi.sh"
export SHIKSHAN_QEMU_LOG_DIR="$TMP/logs-case1"
mkdir -p "$SHIKSHAN_QEMU_LOG_DIR"

set +e
bash "$RUN_SMOKE" dummy-iso.iso >"$TMP/out1.txt" 2>&1
RC1=$?
set -e

if [[ "$RC1" -eq 0 ]]; then
  pass "case1: run-smoke.sh exits 0 when both legs pass"
else
  fail "case1: expected exit 0, got $RC1"
  cat "$TMP/out1.txt" >&2
fi

RUN_DIR1="$(find_run_dir "$SHIKSHAN_QEMU_LOG_DIR")"
if [[ -z "$RUN_DIR1" ]]; then
  fail "case1: no run-* directory created under SHIKSHAN_QEMU_LOG_DIR"
else
  pass "case1: timestamped run dir created"
  JUNIT1="$RUN_DIR1/junit.xml"

  if [[ -f "$JUNIT1" ]]; then
    pass "case1: junit.xml present"
    assert_contains "$JUNIT1" \
      'tests="2" failures="0"' \
      "case1: junit.xml reports tests=2 failures=0"
    assert_contains "$JUNIT1" \
      '<testcase name="boot-bios"' \
      "case1: boot-bios testcase present"
    assert_contains "$JUNIT1" \
      '<testcase name="boot-uefi"' \
      "case1: boot-uefi testcase present"
    assert_not_contains "$JUNIT1" \
      '<failure' \
      "case1: no <failure> element"
    assert_contains "$JUNIT1" \
      '\[stub\] boot-bios success' \
      "case1: bios stub stdout in system-out"
    assert_contains "$JUNIT1" \
      '\[stub\] boot-uefi success' \
      "case1: uefi stub stdout in system-out"
    [[ -f "$RUN_DIR1/bios.log" ]] && pass "case1: bios.log present" \
      || fail "case1: bios.log missing"
    [[ -f "$RUN_DIR1/uefi.log" ]] && pass "case1: uefi.log present" \
      || fail "case1: uefi.log missing"
  else
    fail "case1: junit.xml missing"
  fi
fi

# ── Case 2: BIOS fails (rc=2), UEFI passes ───────────────────────────────────

make_stub_fail boot-bios 2
make_stub_pass boot-uefi

export SHIKSHAN_QEMU_LOG_DIR="$TMP/logs-case2"
mkdir -p "$SHIKSHAN_QEMU_LOG_DIR"

set +e
bash "$RUN_SMOKE" dummy-iso.iso >"$TMP/out2.txt" 2>&1
RC2=$?
set -e

if [[ "$RC2" -eq 2 ]]; then
  pass "case2: run-smoke.sh propagates BIOS exit code (2)"
else
  fail "case2: expected exit 2, got $RC2"
  cat "$TMP/out2.txt" >&2
fi

RUN_DIR2="$(find_run_dir "$SHIKSHAN_QEMU_LOG_DIR")"
if [[ -z "$RUN_DIR2" ]]; then
  fail "case2: no run-* directory created"
else
  pass "case2: timestamped run dir created"
  JUNIT2="$RUN_DIR2/junit.xml"

  if [[ -f "$JUNIT2" ]]; then
    pass "case2: junit.xml present"
    assert_contains "$JUNIT2" \
      'tests="2" failures="1"' \
      "case2: junit.xml reports tests=2 failures=1"
    assert_contains "$JUNIT2" \
      '<testcase name="boot-bios"' \
      "case2: boot-bios testcase present"
    assert_contains "$JUNIT2" \
      '<testcase name="boot-uefi"' \
      "case2: boot-uefi testcase present (UEFI always runs)"

    # Exactly one <failure> element.
    FAIL_COUNT="$(grep -c '<failure' "$JUNIT2" || true)"
    if [[ "$FAIL_COUNT" -eq 1 ]]; then
      pass "case2: exactly one <failure> element"
    else
      fail "case2: expected 1 <failure> element, found $FAIL_COUNT"
      cat "$JUNIT2" >&2
    fi

    # The <failure> must be inside the boot-bios testcase block, not boot-uefi.
    # Use awk (portable; avoids grep -Pzo which is GNU-only).
    IN_BIOS=0
    while IFS= read -r line; do
      if [[ "$line" == *'<testcase name="boot-bios"'* ]]; then IN_BIOS=1; fi
      if [[ "$line" == *'<testcase name="boot-uefi"'* ]]; then IN_BIOS=0; fi
      if [[ $IN_BIOS -eq 1 && "$line" == *'<failure'* ]]; then
        pass "case2: <failure> is inside boot-bios testcase"
        IN_BIOS=99  # sentinel — found, stop checking
        break
      fi
    done < "$JUNIT2"
    [[ $IN_BIOS -eq 99 ]] || fail "case2: <failure> not found inside boot-bios testcase"
  else
    fail "case2: junit.xml missing"
  fi
fi

# ── Summary ───────────────────────────────────────────────────────────────────

echo ""
echo "Results: $PASS passed, $FAIL failed"
[[ $FAIL -eq 0 ]] || exit 1
