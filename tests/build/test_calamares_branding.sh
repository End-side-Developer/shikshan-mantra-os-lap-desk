#!/bin/bash
# tests/build/test_calamares_branding.sh
#
# Asserts the Calamares Shikshan branding bundle is complete and correct.
# Run from the repository root:  bash tests/build/test_calamares_branding.sh
set -euo pipefail

BRANDING_DIR="branding/calamares/shikshan"
HOOK_FILE="config/hooks/live/0032-calamares-branding.hook.chroot"
PASS=0
FAIL=0

pass() { echo "PASS: $1"; PASS=$((PASS+1)); }
fail() { echo "FAIL: $1"; FAIL=$((FAIL+1)); }

echo "=== Calamares branding bundle tests ==="

# 1. branding.desc exists
[ -f "$BRANDING_DIR/branding.desc" ] \
  && pass "branding.desc exists" \
  || fail "branding.desc missing"

# 2. componentName = shikshan
grep -q 'componentName: shikshan' "$BRANDING_DIR/branding.desc" \
  && pass "componentName=shikshan" \
  || fail "componentName != shikshan"

# 3. productName contains 'Shikshan Mantra'
grep -q 'Shikshan Mantra' "$BRANDING_DIR/branding.desc" \
  && pass "productName contains Shikshan Mantra" \
  || fail "productName does not contain Shikshan Mantra"

# 4. All referenced images end in .svg
grep -qE 'productLogo:.*\.svg'   "$BRANDING_DIR/branding.desc" && \
grep -qE 'productIcon:.*\.svg'   "$BRANDING_DIR/branding.desc" && \
grep -qE 'productWelcome:.*\.svg' "$BRANDING_DIR/branding.desc" \
  && pass "all images reference .svg" \
  || fail "one or more images do not reference .svg"

# 5. Every .svg file has SVG xmlns
SVG_FAIL=0
while IFS= read -r -d '' svg; do
  if ! grep -q 'xmlns="http://www.w3.org/2000/svg"' "$svg"; then
    fail "$svg missing SVG xmlns"
    SVG_FAIL=1
  fi
done < <(find "$BRANDING_DIR" -name '*.svg' -print0)
[ "$SVG_FAIL" -eq 0 ] && pass "all .svg files have correct xmlns"

# 6. No raster images
RASTER=$(find "$BRANDING_DIR" -type f \( -iname "*.png" -o -iname "*.jpg" -o -iname "*.jpeg" -o -iname "*.bmp" \))
[ -z "$RASTER" ] \
  && pass "no raster images in bundle" \
  || fail "raster images found: $RASTER"

# 7. Hook is executable in git index (100755)
git ls-files --stage "$HOOK_FILE" | grep -q '^100755' \
  && pass "hook 0032 is executable in git index" \
  || fail "hook 0032 is not 100755 in git index"

# 8. shellcheck (skip gracefully when not installed — CI Linux will run it)
if command -v shellcheck >/dev/null 2>&1; then
  shellcheck "$HOOK_FILE" \
    && pass "hook 0032 shellcheck-clean" \
    || fail "hook 0032 shellcheck errors"
else
  echo "SKIP: shellcheck not found in PATH (will run in CI)"
fi

# 9. Hook numeric prefix in range 0032..0039
HOOKNUM=$(basename "$HOOK_FILE" | grep -oE '^[0-9]+')
[ "$HOOKNUM" -gt 31 ] && [ "$HOOKNUM" -lt 40 ] \
  && pass "hook prefix $HOOKNUM in range (32..39)" \
  || fail "hook prefix $HOOKNUM out of range"

echo ""
echo "Results: $PASS passed, $FAIL failed"
[ "$FAIL" -eq 0 ]
