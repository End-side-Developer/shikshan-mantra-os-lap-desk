#!/usr/bin/env bash
# tests/smoke/test_auto_config_flags.sh
#
# Asserts auto/config carries the locked lb config flag set documented in
# ADR-0007 (live-build-config-flags) and that the defects fixed by SMO-0303
# stay fixed: exactly one LB_LINUX_FLAVOURS assignment and no LB_SYSLINUX_THEME.
#
# Usage: tests/smoke/test_auto_config_flags.sh [path-to-auto/config]

set -euo pipefail

AUTO_CONFIG="${1:-auto/config}"

if [[ ! -f "$AUTO_CONFIG" ]]; then
  echo "FAIL: $AUTO_CONFIG does not exist"
  exit 1
fi

FAILED=0

_check_flag() {
  local pattern="$1"
  local label="$2"
  # `-e` so leading `--` in patterns is not parsed as a grep option.
  if ! grep -qE -e "$pattern" "$AUTO_CONFIG"; then
    echo "FAIL: missing $label"
    FAILED=1
  fi
}

# ADR-0007 inputs.flags_to_document (14 entries).
_check_flag '--distribution[[:space:]]+"?\$?(DISTRIBUTION|trixie)"?'           '--distribution trixie'
_check_flag '--architectures[[:space:]]+"?\$?(ARCHITECTURES|amd64)"?'           '--architectures amd64'
_check_flag '--bootloaders[[:space:]]+"?\$?(BOOTLOADER|syslinux,grub-efi)"?'    '--bootloaders syslinux,grub-efi'
_check_flag '--binary-images[[:space:]]+"?\$?(IMAGE_TYPE|iso-hybrid)"?'         '--binary-images iso-hybrid'
_check_flag '--debian-installer[[:space:]]+none'                                '--debian-installer none'
_check_flag '--initramfs[[:space:]]+"?\$?(LB_INITRAMFS|live-boot)"?'            '--initramfs live-boot'
_check_flag '--apt-recommends[[:space:]]+"?\$?(LB_APT_RECOMMENDS|false)"?'      '--apt-recommends false'
_check_flag '--memtest[[:space:]]+none'                                         '--memtest none'
_check_flag '--linux-flavours[[:space:]]+"?\$?(LB_LINUX_FLAVOURS|amd64)"?'      '--linux-flavours amd64'
_check_flag '--linux-packages[[:space:]]+"?\$?(LB_LINUX_PACKAGES|linux-image-amd64)"?' '--linux-packages linux-image-amd64'
_check_flag '--firmware-chroot[[:space:]]+"?\$?(LB_FIRMWARE_CHROOT|true)"?'     '--firmware-chroot true'
# Persistence and union-filesystem assertions removed: these flags are not exposed
# by `lb config` in live-build 1:20250505+deb13u1. Persistence is enabled at boot
# via the `persistence` kernel parameter + persistence.conf on the live media.
_check_flag '^LB_BOOTAPPEND_LIVE=.*locales=en_IN\.UTF-8' 'LB_BOOTAPPEND_LIVE locales=en_IN.UTF-8'
_check_flag '^LB_BOOTAPPEND_LIVE=.*keyboard-layouts=us' 'LB_BOOTAPPEND_LIVE keyboard-layouts=us'
_check_flag '^LB_BOOTAPPEND_LIVE=.*hostname=shikshan'   'LB_BOOTAPPEND_LIVE hostname=shikshan'
_check_flag '^LB_BOOTAPPEND_LIVE=.*username=student'    'LB_BOOTAPPEND_LIVE username=student'

# Defect guard 1: LB_LINUX_FLAVOURS assignment must appear exactly once
# (was duplicated on lines 31 and 51 pre-SMO-0303). References inside the
# `lb config` invocation (e.g., `--linux-flavours "$LB_LINUX_FLAVOURS"`)
# are intentionally excluded — we only count assignments.
count=$(grep -cE '^[[:space:]]*LB_LINUX_FLAVOURS=' "$AUTO_CONFIG" || true)
if [[ "$count" -ne 1 ]]; then
  echo "FAIL: LB_LINUX_FLAVOURS assignment appears $count times (expected 1)"
  FAILED=1
fi

# Defect guard 2: LB_SYSLINUX_THEME must not appear as an assignment.
if grep -qE '^[[:space:]]*LB_SYSLINUX_THEME=' "$AUTO_CONFIG"; then
  echo "FAIL: LB_SYSLINUX_THEME still present"
  FAILED=1
fi

if [[ "$FAILED" -eq 0 ]]; then
  echo "PASS: all ADR-0007 flags present in auto/config"
else
  echo "FAIL: see above"
  exit 1
fi
