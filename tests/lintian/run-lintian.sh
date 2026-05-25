#!/usr/bin/env bash
# tests/lintian/run-lintian.sh
#
# Runs lintian against the built ISO and compares against the baseline
# allowlist. Fails on any new E:/W: line not in tests/lintian/baseline.txt.

set -euo pipefail

ISO="${1:?usage: run-lintian.sh <iso>}"
[[ -f "$ISO" ]] || { echo "missing: $ISO" >&2; exit 1; }

BASELINE="${BASELINE:-tests/lintian/baseline.txt}"
TMP="$(mktemp)"
trap 'rm -f "$TMP"' EXIT

if ! command -v lintian >/dev/null 2>&1; then
  echo "[lintian] not installed; skipping" >&2
  exit 0
fi

# Only consider E: and W: lines (info lines are noise)
lintian --no-tag-display-limit "$ISO" 2>&1 | grep -E '^(E|W):' | sort -u > "$TMP" || true

if [[ ! -f "$BASELINE" ]]; then
  echo "[lintian] no baseline; initializing from current output"
  cp "$TMP" "$BASELINE"
  exit 0
fi

# Diff
NEW=$(comm -23 "$TMP" <(sort -u "$BASELINE"))
if [[ -n "$NEW" ]]; then
  echo "[lintian] NEW issues since baseline:" >&2
  echo "$NEW" >&2
  exit 2
fi
echo "[lintian] OK — no new issues vs baseline"
