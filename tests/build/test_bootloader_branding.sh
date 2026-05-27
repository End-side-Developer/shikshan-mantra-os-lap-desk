#!/bin/sh
# tests/build/test_bootloader_branding.sh
#
# SMO-0410: assert bootloader menu surfaces (syslinux BIOS + GRUB-EFI) carry
# Shikshan Mantra OS branding and never expose "Debian" as a menu-visible
# string. See docs/adr/0010-bootloader-visual-identity.md and the task contract
# tasks/in-progress/SMO-0410-bootloader-branding.yml S: criteria 11-13.
#
# Run from repo root.
set -eu

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$REPO_ROOT"

PASS=0
FAIL=0
fail() { printf '  FAIL: %s\n' "$1" >&2; FAIL=$((FAIL + 1)); }
pass() { printf '  ok:   %s\n' "$1"; PASS=$((PASS + 1)); }

ISO_LIVE="config/bootloaders/isolinux/live.cfg"
ISO_MENU="config/bootloaders/isolinux/menu.cfg"
ISO_CFG="config/bootloaders/isolinux/isolinux.cfg"
ISO_PNG="config/bootloaders/isolinux/splash.png"
GRUB_CFG="config/bootloaders/grub-pc/config.cfg"
GRUB_THEME="config/bootloaders/grub-pc/theme/theme.txt"
GRUB_BG="config/bootloaders/grub-pc/theme/background.png"
README="config/bootloaders/README.md"

echo "==> SMO-0410 bootloader branding assertions"

# (1) live.cfg exists, non-empty
if [ -s "$ISO_LIVE" ]; then pass "live.cfg present and non-empty"
else fail "live.cfg missing or empty"; fi

# (2) menu.cfg MENU TITLE contains Shikshan Mantra
if grep -q '^menu title Shikshan Mantra' "$ISO_MENU" 2>/dev/null; then
    pass "menu.cfg MENU TITLE = Shikshan Mantra"
else fail "menu.cfg missing 'menu title Shikshan Mantra'"; fi

# (3) live.cfg has both required entry labels
if grep -q 'menu label.*Shikshan Mantra OS (Live)' "$ISO_LIVE" 2>/dev/null; then
    pass "live.cfg has 'Shikshan Mantra OS (Live)' entry"
else fail "live.cfg missing Live entry label"; fi
if grep -q 'menu label.*fail-safe' "$ISO_LIVE" 2>/dev/null; then
    pass "live.cfg has fail-safe entry"
else fail "live.cfg missing fail-safe entry"; fi

# (4) No bare 'Debian' string in menu-visible content of any cfg
# (strip lines starting with # so neutral comments don't false-positive)
for f in "$ISO_LIVE" "$ISO_MENU" "$ISO_CFG" "$GRUB_CFG" "$GRUB_THEME"; do
    if [ -f "$f" ] && sed 's/^[[:space:]]*#.*$//' "$f" | grep -F 'Debian' >/dev/null; then
        fail "$f contains 'Debian' outside comments"
    else
        pass "$f free of 'Debian' (excluding comments)"
    fi
done

# (5) GRUB config.cfg menuentries
if grep -q 'menuentry "Shikshan Mantra OS"' "$GRUB_CFG" 2>/dev/null; then
    pass "GRUB config.cfg has 'Shikshan Mantra OS' menuentry"
else fail "GRUB config.cfg missing default menuentry"; fi
if grep -q 'menuentry "Shikshan Mantra OS (fail-safe)"' "$GRUB_CFG" 2>/dev/null; then
    pass "GRUB config.cfg has fail-safe menuentry"
else fail "GRUB config.cfg missing fail-safe menuentry"; fi

# (6) GRUB theme.txt
if grep -q '^title-text:.*"Shikshan Mantra OS"' "$GRUB_THEME" 2>/dev/null; then
    pass "GRUB theme.txt title-text = Shikshan Mantra OS"
else fail "GRUB theme.txt missing title-text"; fi
if grep -q 'desktop-image:.*"background.png"' "$GRUB_THEME" 2>/dev/null; then
    pass "GRUB theme.txt references background.png"
else fail "GRUB theme.txt missing desktop-image background.png"; fi

# (7) splash.png exists and (if python+PIL available) is 640x480 with <=16 colors
if [ -f "$ISO_PNG" ]; then
    pass "splash.png present ($(wc -c <"$ISO_PNG") bytes)"
    if command -v python >/dev/null 2>&1 && python -c "import PIL" 2>/dev/null; then
        dims=$(python -c "from PIL import Image; im=Image.open('$ISO_PNG'); print(im.size[0], im.size[1], im.mode, len(im.getcolors() or []))")
        # shellcheck disable=SC2086
        set -- $dims
        w="$1"; h="$2"; mode="$3"; ncol="$4"
        if [ "$w" = "640" ] && [ "$h" = "480" ]; then
            pass "splash.png dimensions 640x480"
        else fail "splash.png dimensions $w""x""$h (want 640x480)"; fi
        if [ "$mode" = "P" ] && [ "$ncol" -le 16 ]; then
            pass "splash.png is palette mode with $ncol colors (<=16)"
        else fail "splash.png mode=$mode colors=$ncol (want P + <=16)"; fi
    else
        echo "  skip: PIL not available; cannot verify splash.png dimensions/palette"
    fi
else fail "splash.png missing"; fi

# (8) background.png exists and is one of the accepted dimensions
if [ -f "$GRUB_BG" ]; then
    pass "background.png present ($(wc -c <"$GRUB_BG") bytes)"
    if command -v python >/dev/null 2>&1 && python -c "import PIL" 2>/dev/null; then
        dims=$(python -c "from PIL import Image; im=Image.open('$GRUB_BG'); print(im.size[0], im.size[1])")
        # shellcheck disable=SC2086
        set -- $dims
        w="$1"; h="$2"
        if { [ "$w" = "1024" ] && [ "$h" = "768" ]; } || { [ "$w" = "800" ] && [ "$h" = "600" ]; }; then
            pass "background.png dimensions ${w}x${h} (accepted)"
        else fail "background.png dimensions ${w}x${h} (want 800x600 or 1024x768)"; fi
    else
        echo "  skip: PIL not available; cannot verify background.png dimensions"
    fi
else fail "background.png missing"; fi

# (9) README documents the protected path and license
for needle in 'SPDX-License-Identifier' '640x480' 'touches-bootloader'; do
    if grep -q "$needle" "$README" 2>/dev/null; then
        pass "README mentions '$needle'"
    else fail "README missing '$needle'"; fi
done

# (10) isolinux.cfg includes live.cfg and references the splash
if grep -q 'include live.cfg' "$ISO_CFG" 2>/dev/null && grep -q 'splash.png' "$ISO_MENU" 2>/dev/null; then
    pass "isolinux.cfg chain (include live.cfg + splash background) wired"
else fail "isolinux.cfg or menu.cfg missing include live.cfg / splash background"; fi

echo
echo "==> ${PASS} passed, ${FAIL} failed"
if [ "$FAIL" -gt 0 ]; then exit 1; fi
