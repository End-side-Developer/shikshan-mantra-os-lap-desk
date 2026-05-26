#!/usr/bin/env bash

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
export RELEASES_DIR=$(mktemp -d)

BASE="shikshan-mantra-os-0.0.0-test"

# Make a small fake ISO so size doesn't crash or stat works
dd if=/dev/zero of="$RELEASES_DIR/${BASE}.iso" bs=1M count=1 2>/dev/null || true

cd "$RELEASES_DIR"
sha256sum "${BASE}.iso" > "${BASE}.iso.sha256"
sha512sum "${BASE}.iso" > "${BASE}.iso.sha512"

touch "${BASE}.cdx.json"
touch "${BASE}.spdx.json"
touch "${BASE}.intoto.jsonl"
touch "${BASE}.intoto.jsonl.sig"
touch "MANIFEST.txt"

# Go back
cd "$REPO_ROOT"

echo "Testing exact bundle verification..."
if ! bash "$REPO_ROOT/scripts/verify/verify-iso.sh" "${BASE}.iso"; then
  echo "FAIL: Expected script to pass when all companions are present." >&2
  exit 1
fi

echo "Testing missing companion..."
rm "$RELEASES_DIR/MANIFEST.txt"
if bash "$REPO_ROOT/scripts/verify/verify-iso.sh" "${BASE}.iso" >/dev/null 2>&1; then
  echo "FAIL: Expected script to fail when MANIFEST.txt is missing." >&2
  exit 1
fi

echo "All tests passed."
rm -rf "$RELEASES_DIR"
