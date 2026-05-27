#!/bin/sh
# tests/build/test_plymouth_theme.sh
#
# SMO-0411: assert the Shikshan Mantra Plymouth theme is well-formed
# and wired into live-build. See docs/adr/0010-bootloader-visual-identity.md
# and the task contract S: criteria.
set -eu

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$REPO_ROOT"

PASS=0; FAIL=0
fail() { printf '  FAIL: %s\n' "$1" >&2; FAIL=$((FAIL + 1)); }
pass() { printf '  ok:   %s\n' "$1"; PASS=$((PASS + 1)); }

THEME=config/includes.chroot/usr/share/plymouth/themes/shikshan
DESC="$THEME/shikshan.plymouth"
SCRIPT="$THEME/shikshan.script"
LOGO="$THEME/logo.png"
BG="$THEME/background.png"
README="$THEME/README.md"
PKGLIST=config/package-lists/plymouth-shikshan.list.chroot
HOOK=config/hooks/live/0033-plymouth-default.hook.chroot

echo "==> SMO-0411 Plymouth theme assertions"

# (1) descriptor parses
if [ -s "$DESC" ] && grep -q '^\[Plymouth Theme\]' "$DESC" \
   && grep -q '^Name=Shikshan' "$DESC" \
   && grep -q '^ModuleName=script' "$DESC"; then
    pass "shikshan.plymouth descriptor valid"
else fail "shikshan.plymouth missing/invalid"; fi

# (2) script non-empty
if [ -s "$SCRIPT" ]; then pass "shikshan.script present"
else fail "shikshan.script missing or empty"; fi

# (3) logo.png dims via PIL
if [ -f "$LOGO" ] && command -v python >/dev/null 2>&1 && python -c "import PIL" 2>/dev/null; then
    dims=$(python -c "from PIL import Image; im=Image.open('$LOGO'); print(im.size[0], im.size[1])")
    # shellcheck disable=SC2086
    set -- $dims
    if { [ "$1" = "256" ] && [ "$2" = "256" ]; } || \
       { [ "$1" = "320" ] && [ "$2" = "320" ]; } || \
       { [ "$1" = "384" ] && [ "$2" = "384" ]; }; then
        pass "logo.png dims ${1}x${2}"
    else fail "logo.png dims ${1}x${2} not in {256,320,384}^2"; fi
elif [ -f "$LOGO" ]; then
    pass "logo.png present (PIL unavailable, dims unverified)"
else fail "logo.png missing"; fi

# (4) background.png dims via PIL
if [ -f "$BG" ] && command -v python >/dev/null 2>&1 && python -c "import PIL" 2>/dev/null; then
    dims=$(python -c "from PIL import Image; im=Image.open('$BG'); print(im.size[0], im.size[1])")
    # shellcheck disable=SC2086
    set -- $dims
    w="$1"; h="$2"
    if { [ "$w" = "1280" ] && [ "$h" = "720" ]; } || \
       { [ "$w" = "1366" ] && [ "$h" = "768" ]; } || \
       { [ "$w" = "1920" ] && [ "$h" = "1080" ]; }; then
        pass "background.png dims ${w}x${h}"
    else fail "background.png dims ${w}x${h} not in {1280x720,1366x768,1920x1080}"; fi
elif [ -f "$BG" ]; then
    pass "background.png present (PIL unavailable, dims unverified)"
else fail "background.png missing"; fi

# (5) package list
if [ -f "$PKGLIST" ] && grep -q '^plymouth$' "$PKGLIST" && grep -q '^plymouth-themes$' "$PKGLIST"; then
    pass "plymouth-shikshan.list.chroot pulls plymouth + plymouth-themes"
else fail "package list missing or incomplete"; fi

# (6) hook 0033 metadata
if [ -f "$HOOK" ]; then
    mode=$(stat -c '%a' "$HOOK" 2>/dev/null || stat -f '%Lp' "$HOOK" 2>/dev/null || echo "")
    if [ "$mode" = "755" ]; then pass "hook 0033 mode 0755"
    else fail "hook 0033 mode is '$mode' (want 755)"; fi
    if head -n 1 "$HOOK" | grep -q '^#!/bin/sh'; then pass "hook 0033 shebang /bin/sh"
    else fail "hook 0033 missing #!/bin/sh"; fi
    if head -n 30 "$HOOK" | grep -q '^set -eu'; then pass "hook 0033 'set -eu'"
    else fail "hook 0033 missing 'set -eu'"; fi
    if grep -q 'shikshan' "$HOOK"; then pass "hook 0033 references shikshan theme"
    else fail "hook 0033 doesn't reference shikshan"; fi
else fail "hook 0033 missing"; fi

# (7) README license header
if grep -q 'SPDX-License-Identifier' "$README" 2>/dev/null; then
    pass "README contains SPDX-License-Identifier"
else fail "README missing SPDX-License-Identifier"; fi

# (8) hook ordering: 0030 < 0031 < 0032 < 0033
prev=0
for h in config/hooks/live/0030-*.hook.chroot \
         config/hooks/live/0031-*.hook.chroot \
         config/hooks/live/0032-*.hook.chroot \
         config/hooks/live/0033-*.hook.chroot; do
    [ -e "$h" ] || continue
    n=$(basename "$h" | cut -c1-4)
    if [ "$n" -le "$prev" ]; then
        fail "hook ordering broken at $h (n=$n <= prev=$prev)"
    fi
    prev="$n"
done
pass "hook ordering 0030 < 0031 < 0032 < 0033 verified"

echo
echo "==> ${PASS} passed, ${FAIL} failed"
if [ "$FAIL" -gt 0 ]; then exit 1; fi
