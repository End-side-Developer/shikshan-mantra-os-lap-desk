#!/usr/bin/env bash
# tests/build/test_sync_ui_to_iso.sh
#
# Verify scripts/build/sync-ui-to-iso.sh creates all six expected destinations
# with content sourced from the input tree. Runs against a synthetic tmp tree
# so the real config/includes.chroot/ is not touched.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
SCRIPT="$REPO_ROOT/scripts/build/sync-ui-to-iso.sh"

if [[ ! -x "$SCRIPT" && ! -f "$SCRIPT" ]]; then
    echo "FAIL: sync script missing at $SCRIPT" >&2
    exit 1
fi

if ! command -v rsync >/dev/null 2>&1; then
    echo "[test_sync_ui_to_iso] SKIP: rsync not installed (install with: apt install rsync)"
    exit 0
fi

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
SRC="$TMP/src"
DST="$TMP/dst"

mkdir -p \
    "$SRC/ui/launcher" \
    "$SRC/ui/login" \
    "$SRC/ui/themes" \
    "$SRC/branding/wallpapers" \
    "$SRC/branding/logo"

# Distinctive marker files so we can assert origin
echo "launcher-marker" > "$SRC/ui/launcher/index.html"
echo "login-marker"    > "$SRC/ui/login/welcome.html"
echo "themes-marker"   > "$SRC/ui/themes/light.qss"
echo "wall-marker"     > "$SRC/branding/wallpapers/default.png"
echo "logo-marker"     > "$SRC/branding/logo/shikshan-mantra.svg"
printf '{"v":"test"}\n' > "$SRC/branding/tokens.json"

# Run the sync against the synthetic tree
SHIKSHAN_SRC_ROOT="$SRC" SHIKSHAN_DST_ROOT="$DST" bash "$SCRIPT"

errors=0
_check_file() {
    local path="$1"
    local expected="$2"
    if [[ ! -f "$path" ]]; then
        echo "FAIL: missing $path" >&2
        errors=$((errors + 1))
        return
    fi
    local got
    got="$(cat "$path")"
    if [[ "$got" != "$expected" ]]; then
        echo "FAIL: $path content mismatch (got '$got', expected '$expected')" >&2
        errors=$((errors + 1))
        return
    fi
    echo "OK:   $path"
}

_check_file "$DST/usr/share/shikshan/launcher/index.html"        "launcher-marker"
_check_file "$DST/usr/share/shikshan/login/welcome.html"         "login-marker"
_check_file "$DST/usr/share/shikshan/themes/light.qss"           "themes-marker"
_check_file "$DST/usr/share/backgrounds/shikshan/default.png"    "wall-marker"
_check_file "$DST/usr/share/shikshan/branding/logo/shikshan-mantra.svg" "logo-marker"
_check_file "$DST/usr/share/shikshan/branding/tokens.json"       '{"v":"test"}'

if [[ $errors -ne 0 ]]; then
    echo "[test_sync_ui_to_iso] $errors failure(s)" >&2
    exit 1
fi
echo "[test_sync_ui_to_iso] all 6 destinations present and correct"
