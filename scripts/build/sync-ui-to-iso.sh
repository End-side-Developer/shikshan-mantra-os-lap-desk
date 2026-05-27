#!/bin/sh
# scripts/build/sync-ui-to-iso.sh
#
# Copy ui/ and branding/ source trees into config/includes.chroot/ at the
# paths the running OS expects. Run by scripts/build/build-iso.sh before
# the live-build container starts. See ADR-0009.
#
# Six rsync destinations (one per source subtree + tokens.json):
#   ui/launcher/         -> config/includes.chroot/usr/share/shikshan/launcher/
#   ui/login/            -> config/includes.chroot/usr/share/shikshan/login/
#   ui/themes/           -> config/includes.chroot/usr/share/shikshan/themes/
#   branding/wallpapers/ -> config/includes.chroot/usr/share/backgrounds/shikshan/
#   branding/logo/       -> config/includes.chroot/usr/share/shikshan/branding/logo/
#   branding/tokens.json -> config/includes.chroot/usr/share/shikshan/branding/tokens.json
#
# Env overrides (test hook):
#   SHIKSHAN_SRC_ROOT    repo root for sources    (default: script_dir/../..)
#   SHIKSHAN_DST_ROOT    config/includes.chroot   (default: $SHIKSHAN_SRC_ROOT/config/includes.chroot)

set -eu

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SRC_ROOT="${SHIKSHAN_SRC_ROOT:-$(cd "$SCRIPT_DIR/../.." && pwd)}"
DST_ROOT="${SHIKSHAN_DST_ROOT:-$SRC_ROOT/config/includes.chroot}"

UI_DST="$DST_ROOT/usr/share/shikshan"
WALL_DST="$DST_ROOT/usr/share/backgrounds/shikshan"

echo "[sync-ui-to-iso] SRC_ROOT=$SRC_ROOT"
echo "[sync-ui-to-iso] DST_ROOT=$DST_ROOT"

if ! command -v rsync >/dev/null 2>&1; then
    echo "[sync-ui-to-iso] need rsync on host (apt install rsync)" >&2
    exit 1
fi

mkdir -p \
    "$UI_DST/launcher" \
    "$UI_DST/login" \
    "$UI_DST/themes" \
    "$UI_DST/branding/logo" \
    "$WALL_DST"

rsync -a --delete "$SRC_ROOT/ui/launcher/"          "$UI_DST/launcher/"
rsync -a --delete "$SRC_ROOT/ui/login/"             "$UI_DST/login/"
rsync -a --delete "$SRC_ROOT/ui/themes/"            "$UI_DST/themes/"
rsync -a --delete "$SRC_ROOT/branding/wallpapers/"  "$WALL_DST/"
rsync -a --delete "$SRC_ROOT/branding/logo/"        "$UI_DST/branding/logo/"
rsync -a          "$SRC_ROOT/branding/tokens.json"  "$UI_DST/branding/tokens.json"

# Strip .gitkeep markers from synced destinations so they don't ship on the ISO.
find "$UI_DST" "$WALL_DST" -name '.gitkeep' -type f -delete 2>/dev/null || true

echo "[sync-ui-to-iso] done"
