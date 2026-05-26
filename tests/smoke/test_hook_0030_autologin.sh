#!/usr/bin/env bash
# tests/smoke/test_hook_0030_autologin.sh
#
# Static-analysis smoke test for config/hooks/live/0030-autologin.hook.chroot.
# Greps the hook source for required patterns; also runs shellcheck if available.
# Exit 0 silently on pass. Exit non-zero + "FAIL: <reason>" on stderr on miss.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
HOOK="$REPO_ROOT/config/hooks/live/0030-autologin.hook.chroot"

fail() { echo "FAIL: $1" >&2; exit 1; }

[[ -f "$HOOK" ]] || fail "hook not found: $HOOK"

# -- shebang (line 1 must be exactly #!/bin/sh) --
[[ "$(sed -n '1p' "$HOOK")" == "#!/bin/sh" ]] || fail "line 1 is not #!/bin/sh"

# -- set -eu --
grep -qF 'set -eu' "$HOOK" || fail "missing 'set -eu'"

# -- per-hook assertions --
grep -qF '50-shikshan-autologin.conf' "$HOOK" || fail "missing target config filename"
grep -qF 'autologin-user=student' "$HOOK" || fail "missing 'autologin-user=student'"
grep -qF 'autologin-session=lxqt' "$HOOK" || fail "missing 'autologin-session=lxqt'"

# -- shellcheck --
if command -v shellcheck >/dev/null 2>&1; then
    shellcheck -s sh "$HOOK" || fail "shellcheck reported warnings on $HOOK"
else
    echo "SKIP: shellcheck not installed -- skipping static analysis" >&2
fi
