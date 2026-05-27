#!/usr/bin/env bash
# tests/qemu/run-smoke.sh — orchestrate BIOS + UEFI qemu smoke and emit JUnit XML.
# Used by .github/workflows/ci-qemu-smoke.yml.
#
# Exit codes:
#   0  both legs passed
#   N  first non-zero leg's exit code (BIOS leg checked first)
#   1  usage error
#
# intentional: no -e — leg exit codes are captured manually; do not add -e.
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

ISO_ARG="${1:?usage: run-smoke.sh <iso-path-or-bundle-basename>}"

# Test-injection seams: integration tests set these to stub scripts.
# Defaults resolve legs relative to this script so the orchestrator is
# self-contained regardless of working directory.
BOOT_BIOS="${BOOT_BIOS:-$SCRIPT_DIR/boot-bios.sh}"
BOOT_UEFI="${BOOT_UEFI:-$SCRIPT_DIR/boot-uefi.sh}"

# Timestamped run directory — compact UTC ISO-8601, safe as a dir name.
RUN_TS="$(date -u +%Y%m%dT%H%M%SZ)"
BASE_LOG_DIR="${SHIKSHAN_QEMU_LOG_DIR:-tests/qemu/logs}"
RUN_DIR="$BASE_LOG_DIR/run-$RUN_TS"
mkdir -p "$RUN_DIR"

BIOS_LOG="$RUN_DIR/bios.log"
UEFI_LOG="$RUN_DIR/uefi.log"
JUNIT="$RUN_DIR/junit.xml"

# Point the child scripts' internal LOGDIR at the run dir so their own
# tee'd logs also land under the same timestamped directory.
export SHIKSHAN_QEMU_LOG_DIR="$RUN_DIR"

# ── run_leg ───────────────────────────────────────────────────────────────────
# Run one leg script; capture combined stdout+stderr to $log.
# Prints "RC ELAPSED_SECONDS" on stdout for the caller to read.
run_leg() {
  local script="$1" log="$2"
  local start end rc
  start="$(date +%s)"
  set +e
  bash "$script" "$ISO_ARG" >"$log" 2>&1
  rc=$?
  set -e 2>/dev/null || true
  end="$(date +%s)"
  printf '%d %d\n' "$rc" "$((end - start))"
}

# ── Run both legs (UEFI runs regardless of BIOS outcome) ─────────────────────
BIOS_RC=0; BIOS_TIME=0
UEFI_RC=0; UEFI_TIME=0

read -r BIOS_RC BIOS_TIME < <(run_leg "$BOOT_BIOS" "$BIOS_LOG")
read -r UEFI_RC UEFI_TIME < <(run_leg "$BOOT_UEFI" "$UEFI_LOG")

# ── JUnit XML emission ────────────────────────────────────────────────────────
FAILURES=0
[[ "$BIOS_RC" -ne 0 ]] && FAILURES=$((FAILURES + 1))
[[ "$UEFI_RC" -ne 0 ]] && FAILURES=$((FAILURES + 1))
TOTAL_TIME=$((BIOS_TIME + UEFI_TIME))

# Escape ]]> so user-supplied log content cannot terminate a CDATA section.
cdata_escape() {
  sed 's/]]>/]]]]><![CDATA[>/g' "$1"
}

emit_testcase() {
  local name="$1" rc="$2" elapsed="$3" log="$4"
  printf '    <testcase name="%s" classname="qemu" time="%s">\n' \
    "$name" "$elapsed"
  if [[ "$rc" -ne 0 ]]; then
    printf '      <failure message="exit %s" type="qemu-smoke-failure">' "$rc"
    printf 'exit %s</failure>\n' "$rc"
  fi
  printf '      <system-out><![CDATA[\n'
  if [[ -f "$log" ]]; then cdata_escape "$log"; fi
  printf '\n]]></system-out>\n'
  printf '    </testcase>\n'
}

{
  printf '<?xml version="1.0" encoding="UTF-8"?>\n'
  printf '<testsuites name="qemu-smoke" tests="2" failures="%d" time="%d">\n' \
    "$FAILURES" "$TOTAL_TIME"
  printf '  <testsuite name="qemu-smoke" tests="2" failures="%d" time="%d">\n' \
    "$FAILURES" "$TOTAL_TIME"
  emit_testcase boot-bios "$BIOS_RC" "$BIOS_TIME" "$BIOS_LOG"
  emit_testcase boot-uefi "$UEFI_RC" "$UEFI_TIME" "$UEFI_LOG"
  printf '  </testsuite>\n'
  printf '</testsuites>\n'
} >"$JUNIT"

echo "[run-smoke] run dir : $RUN_DIR"
echo "[run-smoke] BIOS    : rc=$BIOS_RC time=${BIOS_TIME}s log=$BIOS_LOG"
echo "[run-smoke] UEFI    : rc=$UEFI_RC time=${UEFI_TIME}s log=$UEFI_LOG"
echo "[run-smoke] junit   : $JUNIT"

# Propagate the first non-zero leg's exit code; BIOS is checked first.
if [[ "$BIOS_RC" -ne 0 ]]; then exit "$BIOS_RC"; fi
if [[ "$UEFI_RC" -ne 0 ]]; then exit "$UEFI_RC"; fi
exit 0
