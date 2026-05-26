#!/usr/bin/env bash
# tests/qemu/boot-uefi.sh — UEFI variant of boot-bios.sh
# Used by .github/workflows/ci-qemu-uefi.yml.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
RELEASES_DIR="${RELEASES_DIR:-$REPO_ROOT/releases}"

# OVMF firmware location (Debian/Ubuntu default) — checked before ISO resolution
# so we fail fast on misconfigured hosts without touching the release bundle.
OVMF_CODE="${OVMF_CODE:-/usr/share/OVMF/OVMF_CODE.fd}"
OVMF_VARS_SRC="${OVMF_VARS:-/usr/share/OVMF/OVMF_VARS.fd}"
if [[ ! -f "$OVMF_CODE" || ! -f "$OVMF_VARS_SRC" ]]; then
  echo "[qemu-uefi] OVMF firmware not found; install ovmf package" >&2
  exit 1
fi

ISO_ARG="${1:?usage: boot-uefi.sh <iso-path-or-bundle-basename>}"
if [[ "$ISO_ARG" == */* ]]; then
  ISO="$ISO_ARG"
else
  ISO="$RELEASES_DIR/$ISO_ARG"
fi

[[ -f "$ISO" ]] || { echo "[qemu-uefi] missing ISO: $ISO" >&2; exit 1; }

if ! "$REPO_ROOT/scripts/verify/verify-iso.sh" "$ISO"; then
  echo "[qemu-uefi] verify-iso failed" >&2
  exit 4
fi

LOGDIR="${SHIKSHAN_QEMU_LOG_DIR:-tests/qemu/logs}"
mkdir -p "$LOGDIR"
LOG="$LOGDIR/boot-uefi.log"
VARS_TMP="$(mktemp -t shikshan-ovmf-vars.XXXXXX.fd)"
cp "$OVMF_VARS_SRC" "$VARS_TMP"
trap 'rm -f "$VARS_TMP"' EXIT

echo "[qemu-uefi] booting $ISO in UEFI mode, 2GB RAM"

timeout 600 qemu-system-x86_64 \
  -m 2048 \
  -drive if=pflash,format=raw,readonly=on,file="$OVMF_CODE" \
  -drive if=pflash,format=raw,file="$VARS_TMP" \
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
# ADR-0008: success regex, 540s deadline, 2 GB ceiling
SUCCESS_RE='lightdm.*autologin|shikshan.local login'
deadline=$(( $(date +%s) + 540 ))

while kill -0 $PID 2>/dev/null; do
  if grep -qE "$SUCCESS_RE" "$LOG" 2>/dev/null; then
    echo "[qemu-uefi] success marker found"
    kill $PID 2>/dev/null || true; wait $PID 2>/dev/null || true; exit 0
  fi
  if [[ $(date +%s) -gt $deadline ]]; then
    echo "[qemu-uefi] timeout" >&2; kill $PID 2>/dev/null || true; exit 2
  fi
  sleep 5
done
exit 3
