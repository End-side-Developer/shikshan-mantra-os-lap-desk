#!/usr/bin/env bash
# tests/build/test_greeter_config.sh
#
# Assert the SMO-0405 greeter wiring is correct:
#   1. lightdm-slick-greeter appears in desktop-lxqt.list.chroot (exactly once)
#   2. hook 0031 is executable
#   3. hook 0031 is shellcheck-clean (best-effort; skips when shellcheck missing)
#   4. slick-greeter.conf parses as INI

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$REPO_ROOT"

errors=0
_fail() { echo "FAIL: $1" >&2; errors=$((errors + 1)); }
_ok()   { echo "OK:   $1"; }

# 1 — package list addition
LIST=config/package-lists/desktop-lxqt.list.chroot
if [[ ! -f "$LIST" ]]; then
    _fail "missing $LIST"
else
    count=$(grep -c '^lightdm-slick-greeter$' "$LIST" || true)
    if [[ "$count" -ne 1 ]]; then
        _fail "expected exactly 1 line 'lightdm-slick-greeter' in $LIST, got $count"
    else
        _ok  "$LIST contains lightdm-slick-greeter (1 occurrence)"
    fi
fi

# 2 — hook executable bit (check git index, since Windows working tree may lie)
HOOK=config/hooks/live/0031-greeter-theme.hook.chroot
if [[ ! -f "$HOOK" ]]; then
    _fail "missing $HOOK"
else
    mode=$(git ls-files --stage "$HOOK" 2>/dev/null | awk '{print $1}')
    if [[ "$mode" != "100755" ]]; then
        # Fall back to filesystem check if not in git index yet
        if [[ -x "$HOOK" ]]; then
            _ok "$HOOK is executable (filesystem)"
        else
            _fail "$HOOK is not executable (git mode='$mode', fs not +x)"
        fi
    else
        _ok "$HOOK is executable (git mode 100755)"
    fi
fi

# 3 — shellcheck (best-effort)
if command -v shellcheck >/dev/null 2>&1; then
    if shellcheck "$HOOK"; then
        _ok "shellcheck clean on $HOOK"
    else
        _fail "shellcheck reported issues in $HOOK"
    fi
else
    echo "[test_greeter_config] SKIP shellcheck (not installed)"
fi

# 4 — slick-greeter.conf is INI-parseable. We use python's configparser.
CONF=branding/greeter/slick-greeter.conf
if [[ ! -f "$CONF" ]]; then
    _fail "missing $CONF"
else
    if python3 -c "
import configparser, sys
p = configparser.ConfigParser(strict=False)
p.read('$CONF')
if 'Greeter' not in p:
    sys.exit('missing [Greeter] section')
required = ['background','background-color','logo','theme-name','icon-theme-name','draw-user-backgrounds','show-power','show-keyboard']
missing = [k for k in required if k not in p['Greeter']]
if missing:
    sys.exit(f'missing keys: {missing}')
print('ok')
" 2>&1; then
        _ok "$CONF is INI-parseable with all required keys"
    else
        _fail "$CONF failed INI parse or missing required keys"
    fi
fi

if [[ $errors -ne 0 ]]; then
    echo "[test_greeter_config] $errors failure(s)" >&2
    exit 1
fi
echo "[test_greeter_config] all checks passed"
