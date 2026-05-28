#!/usr/bin/env bash
# tests/build/test_vidyarthi_skeleton.sh
# Smoke-tests the SMO-0550 Vidyarthi Meson + PyGObject skeleton.
# Run from the repo root: bash tests/build/test_vidyarthi_skeleton.sh
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
VIDYARTHI="${REPO_ROOT}/config/includes.chroot/usr/share/shikshan/vidyarthi"
PASS=0
FAIL=0

ok()  { echo "  PASS: $*"; PASS=$((PASS + 1)); }
fail(){ echo "  FAIL: $*" >&2; FAIL=$((FAIL + 1)); }

echo "=== Vidyarthi skeleton smoke tests ==="

# 1. meson.build exists and declares the project
if [ -f "${VIDYARTHI}/meson.build" ] && grep -q "project('vidyarthi'" "${VIDYARTHI}/meson.build"; then
    ok "meson.build exists and declares project('vidyarthi')"
else
    fail "meson.build missing or project() not found"
fi

# 2. main.py compiles (use py_compile to handle top-level scripts)
if python3 -m py_compile "${VIDYARTHI}/src/main.py" 2>/dev/null; then
    ok "main.py compiles cleanly"
else
    fail "main.py does not compile"
fi

# 3. window.py compiles
if python3 -m py_compile "${VIDYARTHI}/src/window.py" 2>/dev/null; then
    ok "window.py compiles cleanly"
else
    fail "window.py does not compile"
fi

# 4. window.blp exists and has required identifiers
if [ -f "${VIDYARTHI}/data/ui/window.blp" ] \
    && grep -q "Adw.ApplicationWindow" "${VIDYARTHI}/data/ui/window.blp" \
    && grep -q "HeaderBar" "${VIDYARTHI}/data/ui/window.blp"; then
    ok "window.blp exists with Adw.ApplicationWindow + HeaderBar"
else
    fail "window.blp missing or incomplete"
fi

# 5. package list contains all required packages
PKG_LIST="${REPO_ROOT}/config/package-lists/vidyarthi.list.chroot"
for pkg in python3-gi gir1.2-gtk-4.0 gir1.2-adw-1 gir1.2-gtksourceview-5 libadwaita-1-0 blueprint-compiler meson; do
    if grep -q "^${pkg}$" "${PKG_LIST}"; then
        ok "package list contains ${pkg}"
    else
        fail "package list missing ${pkg}"
    fi
done

# 6. No subprocess wiring in src/ (skeleton only)
if ! grep -r "subprocess" "${VIDYARTHI}/src/" 2>/dev/null | grep -q .; then
    ok "no subprocess wiring in src/ (skeleton-only check)"
else
    fail "unexpected subprocess usage found in src/"
fi

# 7. SPDX headers present
for f in "${VIDYARTHI}/src/main.py" "${VIDYARTHI}/src/window.py"; do
    if grep -q "SPDX-License-Identifier" "$f"; then
        ok "SPDX header present in $(basename "$f")"
    else
        fail "SPDX header missing in $(basename "$f")"
    fi
done

echo ""
echo "Results: ${PASS} passed, ${FAIL} failed"
[ "${FAIL}" -eq 0 ]
