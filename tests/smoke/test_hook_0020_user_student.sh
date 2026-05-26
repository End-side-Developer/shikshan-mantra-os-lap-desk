#!/usr/bin/env bash
# tests/smoke/test_hook_0020_user_student.sh
#
# Static-analysis smoke test for config/hooks/live/0020-user-student.hook.chroot.
# Greps the hook source for required patterns; also runs shellcheck if available.
# Exit 0 silently on pass. Exit non-zero + "FAIL: <reason>" on stderr on miss.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
HOOK="$REPO_ROOT/config/hooks/live/0020-user-student.hook.chroot"

fail() { echo "FAIL: $1" >&2; exit 1; }

[[ -f "$HOOK" ]] || fail "hook not found: $HOOK"

# -- shebang (line 1 must be exactly #!/bin/sh) --
[[ "$(sed -n '1p' "$HOOK")" == "#!/bin/sh" ]] || fail "line 1 is not #!/bin/sh"

# -- set -eu --
grep -qF 'set -eu' "$HOOK" || fail "missing 'set -eu'"

# -- per-hook assertions --
grep -qE 'adduser[[:space:]].*--disabled-password' "$HOOK" || fail "missing 'adduser --disabled-password'"
grep -qF -- '--uid 1000' "$HOOK" || fail "missing '--uid 1000'"
for grp in audio video plugdev netdev; do
    grep -qF "$grp" "$HOOK" || fail "missing group '$grp' in hook"
done
grep -qF 'passwd -l root' "$HOOK" || fail "missing 'passwd -l root'"

# -- shellcheck --
if command -v shellcheck >/dev/null 2>&1; then
    shellcheck -s sh "$HOOK" || fail "shellcheck reported warnings on $HOOK"
else
    echo "SKIP: shellcheck not installed -- skipping static analysis" >&2
fi
