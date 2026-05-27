#!/usr/bin/env bash
# tests/smoke/test_hook_0010_locale.sh
#
# Static-analysis smoke test for config/hooks/live/0010-locale-default.hook.chroot.
# Greps the hook source for required patterns; also runs shellcheck if available.
# Exit 0 silently on pass. Exit non-zero + "FAIL: <reason>" on stderr on miss.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
HOOK="$REPO_ROOT/config/hooks/live/0010-locale-default.hook.chroot"

fail() { echo "FAIL: $1" >&2; exit 1; }

[[ -f "$HOOK" ]] || fail "hook not found: $HOOK"

# -- shebang (line 1 must be exactly #!/bin/sh) --
[[ "$(sed -n '1p' "$HOOK")" == "#!/bin/sh" ]] || fail "line 1 is not #!/bin/sh"

# -- set -eu --
grep -qF 'set -eu' "$HOOK" || fail "missing 'set -eu'"

# -- per-hook assertions --
grep -qF 'locale-gen' "$HOOK" || fail "missing 'locale-gen' invocation"
grep -qF 'en_IN UTF-8' "$HOOK" || fail "missing 'en_IN UTF-8' in locale.gen heredoc"
grep -qF 'hi_IN UTF-8' "$HOOK" || fail "missing 'hi_IN UTF-8' in locale.gen heredoc"
grep -qF 'update-locale' "$HOOK" || fail "missing 'update-locale' call"
grep -qF 'en_IN.UTF-8' "$HOOK" || fail "missing 'en_IN.UTF-8' in update-locale call"

# -- shellcheck --
if command -v shellcheck >/dev/null 2>&1; then
    shellcheck -s sh "$HOOK" || fail "shellcheck reported warnings on $HOOK"
else
    echo "SKIP: shellcheck not installed -- skipping static analysis" >&2
fi
