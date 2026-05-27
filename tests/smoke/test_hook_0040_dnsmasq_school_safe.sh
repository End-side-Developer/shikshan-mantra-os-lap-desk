#!/usr/bin/env bash
# tests/smoke/test_hook_0040_dnsmasq_school_safe.sh
#
# Static-analysis smoke test for config/hooks/live/0040-dnsmasq-school-safe.hook.chroot.
# Greps the hook source for required patterns; also runs shellcheck if available.
# Exit 0 silently on pass. Exit non-zero + "FAIL: <reason>" on stderr on miss.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
HOOK="$REPO_ROOT/config/hooks/live/0040-dnsmasq-school-safe.hook.chroot"

fail() { echo "FAIL: $1" >&2; exit 1; }

[[ -f "$HOOK" ]] || fail "hook not found: $HOOK"

# -- shebang (line 1 must be exactly #!/bin/sh) --
[[ "$(sed -n '1p' "$HOOK")" == "#!/bin/sh" ]] || fail "line 1 is not #!/bin/sh"

# -- set -eu --
grep -qF 'set -eu' "$HOOK" || fail "missing 'set -eu'"

# -- per-hook assertions --
grep -qF 'shikshan-school-safe.conf' "$HOOK" || fail "missing target config filename"
grep -qF 'server=1.1.1.3' "$HOOK" || fail "missing 'server=1.1.1.3' (Cloudflare Family DNS)"
grep -qF 'server=1.0.0.3' "$HOOK" || fail "missing 'server=1.0.0.3' (Cloudflare Family DNS)"
grep -qF 'no-resolv' "$HOOK" || fail "missing 'no-resolv' directive"
grep -qF 'systemctl enable dnsmasq' "$HOOK" || fail "missing 'systemctl enable dnsmasq'"

# -- shellcheck --
if command -v shellcheck >/dev/null 2>&1; then
    shellcheck -s sh "$HOOK" || fail "shellcheck reported warnings on $HOOK"
else
    echo "SKIP: shellcheck not installed -- skipping static analysis" >&2
fi
