#!/usr/bin/env bash
# tests/build/test_welcome_autostart.sh
# SMO-0406: autostart .desktop is freedesktop-valid, the Institution-login
# button carries `disabled`, hook 0050 is exec + shellcheck-clean.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$REPO_ROOT"

DESK=config/includes.chroot/etc/xdg/autostart/shikshan-welcome.desktop
HTML=ui/login/welcome/index.html
HOOK=config/hooks/live/0050-welcome-firstrun.hook.chroot

errors=0
require() {
    if eval "$1"; then echo "OK:   $2"; else echo "FAIL: $2" >&2; errors=$((errors + 1)); fi
}

require "[[ -f '$DESK' ]] && grep -q '^\\[Desktop Entry\\]' '$DESK' && grep -q '^Type=Application' '$DESK' && grep -Eq '^Exec=.+' '$DESK'" \
    "$DESK is freedesktop-valid"

require "python3 -c \"import re,sys; h=open('$HTML',encoding='utf-8').read(); m=re.search(r'<button[^>]*data-role=\\\"institution\\\"[^>]*>', h, re.DOTALL); sys.exit(0 if (m and 'disabled' in m.group(0)) else 1)\"" \
    "$HTML institution button has disabled attribute"

mode=$(git ls-files --stage "$HOOK" 2>/dev/null | awk '{print $1}')
require "[[ '$mode' == '100755' ]] || [[ -x '$HOOK' ]]" \
    "$HOOK is executable (git=$mode)"

if command -v shellcheck >/dev/null 2>&1; then
    require "shellcheck '$HOOK'" "shellcheck clean on $HOOK"
else
    echo "[test_welcome_autostart] SKIP shellcheck (not installed)"
fi

if [[ $errors -ne 0 ]]; then
    echo "[test_welcome_autostart] $errors failure(s)" >&2
    exit 1
fi
echo "[test_welcome_autostart] all checks passed"
