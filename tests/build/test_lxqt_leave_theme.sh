#!/usr/bin/env bash
# tests/build/test_lxqt_leave_theme.sh
# SMO-0408: QSS basic syntax (balanced braces, no unknown @-rules) and
# lxqt-leave.conf parses as INI with the QSS path referenced.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$REPO_ROOT"

QSS=ui/themes/shikshan-light/lxqt-leave.qss
CONF=config/includes.chroot/etc/xdg/lxqt/lxqt-leave.conf
QSS_RUNTIME_PATH=/usr/share/shikshan/themes/shikshan-light/lxqt-leave.qss

errors=0
require() {
    if eval "$1"; then echo "OK:   $2"; else echo "FAIL: $2" >&2; errors=$((errors + 1)); fi
}

require "[[ -f '$QSS' ]]"  "$QSS exists"
require "[[ -f '$CONF' ]]" "$CONF exists"

# QSS brace balance
opens=$(grep -o '{' "$QSS" | wc -l | tr -d ' ')
closes=$(grep -o '}' "$QSS" | wc -l | tr -d ' ')
require "[[ '$opens' == '$closes' ]] && [[ '$opens' -gt 0 ]]" \
    "$QSS brace count balanced ($opens open, $closes close)"

# Reject CSS @-rules that Qt QSS does not support
require "! grep -E '^[[:space:]]*@(import|media|keyframes|font-face|charset)' '$QSS'" \
    "$QSS has no unsupported @-rules"

# lxqt-leave.conf INI parse + references the QSS path
require "python3 -c \"
import configparser, sys
p = configparser.ConfigParser(strict=False)
p.read('$CONF', encoding='utf-8')
if 'General' not in p: sys.exit('missing [General]')
if 'Style' not in p:   sys.exit('missing [Style]')
ss = p['Style'].get('stylesheet', '')
if ss != '$QSS_RUNTIME_PATH': sys.exit('stylesheet path mismatch: ' + ss)
\"" "$CONF parses as INI with stylesheet=$QSS_RUNTIME_PATH"

if [[ $errors -ne 0 ]]; then
    echo "[test_lxqt_leave_theme] $errors failure(s)" >&2
    exit 1
fi
echo "[test_lxqt_leave_theme] all checks passed"
