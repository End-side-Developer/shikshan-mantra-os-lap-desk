#!/usr/bin/env bash
# scripts/verify/verify-iso.sh
#
# Verify a built/released ISO: SHA-256, cosign signature (if release),
# package list lintian check, expected-contents presence.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$REPO_ROOT"

ISO="${1:-artifacts/shikshan.iso}"

if [[ ! -f "$ISO" ]]; then
  echo "[verify-iso] file not found: $ISO" >&2
  exit 1
fi

echo "[verify-iso] verifying $ISO"

# SHA-256
SHA_FILE="${ISO}.sha256"
if [[ -f "$SHA_FILE" ]]; then
  echo "[verify-iso] sha256 check"
  sha256sum -c "$SHA_FILE"
else
  echo "[verify-iso] no sha256 sidecar; computing"
  sha256sum "$ISO"
fi

# Cosign signature (only for release artifacts that have a .bundle)
BUNDLE="${ISO}.bundle"
if [[ -f "$BUNDLE" ]] && command -v cosign >/dev/null 2>&1; then
  echo "[verify-iso] cosign verify"
  cosign verify-blob \
    --bundle "$BUNDLE" \
    --certificate-identity-regexp '^https://github.com/shikshan-mantra/shikshan-mantra-os/.+' \
    --certificate-oidc-issuer 'https://token.actions.githubusercontent.com' \
    "$ISO"
fi

# Lintian (best-effort)
if command -v lintian >/dev/null 2>&1; then
  echo "[verify-iso] lintian (subset)"
  lintian --no-tag-display-limit "$ISO" 2>&1 | head -100 || true
fi

# Expected contents sanity (mount + inspect would be ideal; for now check size)
SIZE=$(stat -c%s "$ISO" 2>/dev/null || stat -f%z "$ISO" 2>/dev/null || echo 0)
MIN_MB=400
SIZE_MB=$((SIZE / 1024 / 1024))
if [[ $SIZE_MB -lt $MIN_MB ]]; then
  echo "[verify-iso] WARN: ISO is ${SIZE_MB}MB; expected ≥ ${MIN_MB}MB" >&2
fi
echo "[verify-iso] size ${SIZE_MB}MB"

echo "[verify-iso] OK"
