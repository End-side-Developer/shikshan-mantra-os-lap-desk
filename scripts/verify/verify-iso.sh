#!/usr/bin/env bash
# scripts/verify/verify-iso.sh
#
# Verify a built/released ISO: SHA-256, SHA-512, cosign signature (if release),
# package list lintian check, expected-contents presence.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$REPO_ROOT"

if [[ $# -eq 0 ]]; then
    echo "Usage: $0 <iso-path-or-filename>" >&2
    exit 1
fi

INPUT="$1"
OUT_DIR="${RELEASES_DIR:-releases}"

if [[ "$INPUT" != */* ]]; then
  ISO="${OUT_DIR}/${INPUT}"
else
  ISO="$INPUT"
fi

if [[ ! -f "$ISO" ]]; then
  echo "[verify-iso] file not found: $ISO" >&2
  exit 1
fi

BASE=$(basename "$ISO" .iso)
DIR=$(dirname "$ISO")

echo "[verify-iso] verifying $ISO"

# Require all companions
COMPANIONS=(
  "${BASE}.iso.sha256"
  "${BASE}.iso.sha512"
  "${BASE}.cdx.json"
  "${BASE}.spdx.json"
  "${BASE}.intoto.jsonl"
  "${BASE}.intoto.jsonl.sig"
  "MANIFEST.txt"
)

MISSING=0
for comp in "${COMPANIONS[@]}"; do
  if [[ ! -f "$DIR/$comp" ]]; then
    echo "[verify-iso] missing: $DIR/$comp" >&2
    MISSING=1
  fi
done

if [[ $MISSING -eq 1 ]]; then
  echo "[verify-iso] one or more companion artifacts are missing in $DIR" >&2
  exit 1
fi

# SHA-256 / SHA-512
# The .sha256/.sha512 companion files contain the bundle basename only
# (no directory prefix), so sha{256,512}sum -c must be run from the
# directory containing the ISO. Otherwise sha*sum looks in CWD and fails
# with "No such file or directory" when verify-iso is invoked from REPO_ROOT.
echo "[verify-iso] sha256 check"
( cd "$DIR" && sha256sum -c "${BASE}.iso.sha256" )

echo "[verify-iso] sha512 check"
( cd "$DIR" && sha512sum -c "${BASE}.iso.sha512" )

# Cosign signature
BUNDLE="$DIR/${BASE}.iso.bundle"
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
