#!/usr/bin/env bash
# tests/qemu/boot-bios.sh — smoke test BIOS boot of the built ISO.
# Used by .github/workflows/ci-qemu-bios.yml.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
RELEASES_DIR="${RELEASES_DIR:-$REPO_ROOT/releases}"

ISO_ARG="${1:?usage: boot-bios.sh <iso-path-or-bundle-basename>}"
if [[ "$ISO_ARG" == */* ]]; then
  ISO="$ISO_ARG"
else
  ISO="$RELEASES_DIR/$ISO_ARG"
fi

[[ -f "$ISO" ]] || { echo "[qemu-bios] missing ISO: $ISO" >&2; exit 1; }

if ! "$REPO_ROOT/scripts/verify/verify-iso.sh" "$ISO"; then
  echo "[qemu-bios] verify-iso failed" >&2
  exit 4
fi

LOGDIR="${SHIKSHAN_QEMU_LOG_DIR:-tests/qemu/logs}"
mkdir -p "$LOGDIR"
LOG="$LOGDIR/boot-bios.log"

echo "[qemu-bios] booting $ISO in BIOS mode, 2GB RAM"

# nographic so CI captures serial; -no-reboot to exit if init panics.
timeout 600 qemu-system-x86_64 \
  -m 2048 \
  -cdrom "$ISO" \
  -boot d \
  -nographic \
  -no-reboot \
  -serial mon:stdio \
  -display none \
  -device virtio-net-pci,netdev=n0 \
  -netdev user,id=n0 \
  2>&1 | tee "$LOG" &

PID=$!

# Wait for either the login prompt or the launcher to appear in the log.
# The exact string is set by live-build's getty + LightDM autologin.
# ADR-0008: success regex, 540s deadline, 2 GB ceiling
SUCCESS_RE='lightdm.*autologin|shikshan.local login'
deadline=$(( $(date +%s) + 540 ))

while kill -0 $PID 2>/dev/null; do
  if grep -qE "$SUCCESS_RE" "$LOG" 2>/dev/null; then
    echo "[qemu-bios] success marker found"
    kill $PID 2>/dev/null || true
    wait $PID 2>/dev/null || true
    exit 0
  fi
  if [[ $(date +%s) -gt $deadline ]]; then
    echo "[qemu-bios] timeout waiting for success marker" >&2
    kill $PID 2>/dev/null || true
    exit 2
  fi
  sleep 5
done

echo "[qemu-bios] qemu exited before success marker" >&2
exit 3
