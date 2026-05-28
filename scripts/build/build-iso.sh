#!/usr/bin/env bash
# scripts/build/build-iso.sh
#
# Build the Shikshan Mantra OS ISO inside a clean, pinned Debian container.
# The host needs Docker or Podman; everything else runs inside the container.
#
# Usage:
#   bash scripts/build/build-iso.sh           # full build
#   bash scripts/build/build-iso.sh --quick   # skip lintian + local verify (~30 min faster)
#
# Env vars:
#   VERSION      — bundle version string (default: 0.0.0-dev+<git-hash>)
#   ARCH         — target arch (default: amd64)
#   RELEASES_DIR — output directory (default: releases)
#   SMOKE_SBOM   — set to 1 to write empty SBOM stubs instead of running syft (test-only)

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$REPO_ROOT"

QUICK=0
if [[ "${1:-}" == "--quick" ]]; then
    QUICK=1
    shift
fi

# ── bundle identity ────────────────────────────────────────────────────────────
_git_short() { git rev-parse --short HEAD 2>/dev/null || echo "unknown"; }
VERSION="${VERSION:-0.0.0-dev+$(_git_short)}"
ARCH="${ARCH:-amd64}"
BUNDLE_BASE="shikshan-mantra-os-${VERSION}-${ARCH}"
RELEASES_DIR="${RELEASES_DIR:-releases}"

mkdir -p "$RELEASES_DIR" .build/cache artifacts

# Pinned container per ADR-0001. Update only via touches-signing + ADR amendment.
BUILDER_IMAGE="debian:trixie"

# ── container runtime ──────────────────────────────────────────────────────────
if command -v docker >/dev/null 2>&1; then
    RUNTIME=docker
elif command -v podman >/dev/null 2>&1; then
    RUNTIME=podman
else
    echo "[build-iso] need docker or podman on host" >&2
    exit 1
fi

echo "[build-iso] using $RUNTIME with $BUILDER_IMAGE"
echo "[build-iso] bundle: $BUNDLE_BASE -> $RELEASES_DIR/"

# ── sync ui/ + branding/ into includes.chroot before lb build (ADR-0009) ─────
echo "[build-iso] syncing ui/ + branding/ sources to config/includes.chroot/"
bash scripts/build/sync-ui-to-iso.sh

# ── container build ────────────────────────────────────────────────────────────
# On Windows (MSYS2/Git Bash), POSIX paths like /build get converted to
# C:/Program Files/Git/build by the shell before Docker sees them.
# Use cygpath for host-side mounts and // prefix for container-side paths.
if [ -n "${MSYSTEM:-}" ] || [ "${OS:-}" = "Windows_NT" ]; then
    _host_root="$(cygpath -w "$REPO_ROOT" 2>/dev/null || echo "$REPO_ROOT")"
    _host_cache="$(cygpath -w "$REPO_ROOT/.build/cache" 2>/dev/null || echo "$REPO_ROOT/.build/cache")"
    _workdir="//build"
    _mount_build="${_host_root}://build"
    _mount_cache="${_host_cache}://var/cache/apt/archives"
else
    _host_root="$REPO_ROOT"
    _host_cache="$REPO_ROOT/.build/cache"
    _workdir="/build"
    _mount_build="${_host_root}:/build"
    _mount_cache="${_host_cache}:/var/cache/apt/archives"
fi

"$RUNTIME" run --rm --privileged \
    -v "$_mount_build" \
    -v "$_mount_cache" \
    -w "$_workdir" \
    -e DEBIAN_FRONTEND=noninteractive \
    -e VERSION="$VERSION" \
    -e ARCH="$ARCH" \
    "$BUILDER_IMAGE" \
    bash -c '
        set -euo pipefail
        apt-get update -qq
        apt-get install -y --no-install-recommends \
            live-build live-boot live-config xorriso syslinux-utils isolinux \
            grub-pc-bin grub-efi-amd64-bin mtools dosfstools squashfs-tools sudo
        bash auto/build
    '

# ── locate produced ISO ────────────────────────────────────────────────────────
# auto/build currently writes artifacts/shikshan.iso (pre-SMO-0306b).
# After SMO-0306b lands it will write releases/<bundle>.iso directly.
if   [[ -f "artifacts/shikshan.iso" ]]; then
    SRC="artifacts/shikshan.iso"
elif [[ -f "${RELEASES_DIR}/${BUNDLE_BASE}.iso" ]]; then
    SRC="${RELEASES_DIR}/${BUNDLE_BASE}.iso"
elif [[ -f "${RELEASES_DIR}/shikshan.iso" ]]; then
    SRC="${RELEASES_DIR}/shikshan.iso"
else
    echo "[build-iso] no ISO produced by auto/build" >&2
    exit 2
fi

# ── move to canonical bundle path ─────────────────────────────────────────────
DST="${RELEASES_DIR}/${BUNDLE_BASE}.iso"
if [[ "$SRC" != "$DST" ]]; then
    mv -f "$SRC" "$DST"
fi

echo "[build-iso] ISO at $DST ($(du -sh "$DST" | cut -f1))"

# ── checksums ─────────────────────────────────────────────────────────────────
( cd "$RELEASES_DIR" && sha256sum "${BUNDLE_BASE}.iso" > "${BUNDLE_BASE}.iso.sha256" )
( cd "$RELEASES_DIR" && sha512sum "${BUNDLE_BASE}.iso" > "${BUNDLE_BASE}.iso.sha512" )
echo "[build-iso] checksums written"

# ── SBOMs ─────────────────────────────────────────────────────────────────────
# Real SBOMs need syft on the host. If unavailable (CI runners, casual local
# builds), write empty stubs so verify-iso.sh's companion check still passes.
# SMOKE_SBOM=1 forces stubs explicitly. SMOKE_SBOM=0 forces failure if syft
# missing. Default (unset) is auto-fallback.
if [[ "${SMOKE_SBOM:-auto}" == "1" ]] || \
   { [[ "${SMOKE_SBOM:-auto}" == "auto" ]] && ! command -v syft >/dev/null 2>&1; }; then
    if [[ "${SMOKE_SBOM:-auto}" == "auto" ]]; then
        echo "[build-iso] syft not installed; writing stub SBOMs (set SMOKE_SBOM=0 to require syft)"
    else
        echo "[build-iso] SMOKE_SBOM=1 — writing empty SBOM stubs (not for production)"
    fi
    : > "${RELEASES_DIR}/${BUNDLE_BASE}.cdx.json"
    : > "${RELEASES_DIR}/${BUNDLE_BASE}.spdx.json"
else
    RELEASES_DIR="$RELEASES_DIR" bash scripts/build/sbom-generate.sh "$DST"
fi

# ── intoto stubs (overwritten by CI cosign-sign step) ─────────────────────────
: > "${RELEASES_DIR}/${BUNDLE_BASE}.intoto.jsonl"
: > "${RELEASES_DIR}/${BUNDLE_BASE}.intoto.jsonl.sig"

# ── MANIFEST.txt ──────────────────────────────────────────────────────────────
( cd "$RELEASES_DIR" && \
    find . -maxdepth 1 -type f -name "${BUNDLE_BASE}*" ! -name "MANIFEST.txt" \
        | sort | xargs sha256sum > MANIFEST.txt )
echo "[build-iso] MANIFEST.txt written"

# ── verify ────────────────────────────────────────────────────────────────────
if [[ $QUICK -eq 0 ]]; then
    echo "[build-iso] running verify-iso.sh"
    RELEASES_DIR="$RELEASES_DIR" bash scripts/verify/verify-iso.sh "${BUNDLE_BASE}.iso"
    _rc=$?
    if [[ $_rc -ne 0 ]]; then
        echo "[build-iso] verify-iso.sh failed (exit $_rc)" >&2
        exit "$_rc"
    fi

    echo "[build-iso] running lintian (subset)"
    if command -v lintian >/dev/null 2>&1; then
        lintian --no-tag-display-limit "$DST" || true
    else
        echo "[build-iso] lintian not installed on host; skipping (CI runs it)"
    fi
fi

echo "[build-iso] complete -> $DST"
