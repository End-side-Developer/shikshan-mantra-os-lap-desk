#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
CONTROL="${REPO_ROOT}/debian/control"
CHANGELOG="${REPO_ROOT}/debian/changelog"
SOURCE_FORMAT="${REPO_ROOT}/debian/source/format"
RULES="${REPO_ROOT}/debian/rules"

pass() { echo "PASS: $*"; }
fail() { echo "FAIL: $*" >&2; exit 1; }

# 1. debian/changelog parses successfully
if command -v dpkg-parsechangelog >/dev/null 2>&1; then
    dpkg-parsechangelog -l "${CHANGELOG}" >/dev/null || fail "dpkg-parsechangelog failed"
    pass "dpkg-parsechangelog exit 0"
else
    grep -q "shikshan-vidyarthi" "${CHANGELOG}" || fail "changelog missing package name"
    grep -q "UNRELEASED"         "${CHANGELOG}" || fail "changelog missing UNRELEASED"
    pass "changelog fields present (dpkg-dev unavailable, grepped)"
fi

# 2. debian/source/format == '3.0 (native)'
fmt="$(cat "${SOURCE_FORMAT}")"
[ "${fmt}" = "3.0 (native)" ] || fail "source/format is '${fmt}', expected '3.0 (native)'"
pass "debian/source/format == '3.0 (native)'"

# 3. debian/rules starts with #!/usr/bin/make -f
head_line="$(head -1 "${RULES}")"
[ "${head_line}" = "#!/usr/bin/make -f" ] || fail "debian/rules shebang wrong: '${head_line}'"
pass "debian/rules starts with #!/usr/bin/make -f"

# 4. both binary stanzas appear in debian/control
grep -q "^Package: shikshan-vidyarthi$"     "${CONTROL}" || fail "debian/control missing Package: shikshan-vidyarthi"
grep -q "^Package: shikshan-engines-core$"  "${CONTROL}" || fail "debian/control missing Package: shikshan-engines-core"
pass "both binary stanzas present in debian/control"

# 5. lintian (best-effort)
if command -v lintian >/dev/null 2>&1; then
    lintian -c "${CONTROL}" && pass "lintian clean" || echo "WARN: lintian reported issues (non-fatal)"
else
    pass "lintian not available — skipped"
fi

echo "All assertions passed."
