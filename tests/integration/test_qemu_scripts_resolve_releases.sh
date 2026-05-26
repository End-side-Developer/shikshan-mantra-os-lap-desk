#!/usr/bin/env bash
# tests/integration/test_qemu_scripts_resolve_releases.sh
#
# Validates that boot-bios.sh and boot-uefi.sh:
#   1. Accept a bare bundle basename and resolve it under RELEASES_DIR.
#   2. Accept a full ISO path directly.
#   3. Call verify-iso.sh first and exit 4 if it fails (before invoking qemu).
#
# Stubs qemu-system-x86_64 via PATH-prepend. UEFI cases are skipped when
# OVMF firmware is absent (same convention as boot-uefi.sh itself).

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
PASS=0
FAIL=0

fail() { echo "FAIL: $*" >&2; FAIL=$(( FAIL + 1 )); }
pass() { echo "PASS: $*"; PASS=$(( PASS + 1 )); }

# ── Setup ────────────────────────────────────────────────────────────────────

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

export RELEASES_DIR="$TMP/releases"
mkdir -p "$RELEASES_DIR"
export SHIKSHAN_QEMU_LOG_DIR="$TMP/qemu-logs"
mkdir -p "$SHIKSHAN_QEMU_LOG_DIR"

BASE="shikshan-mantra-os-0.0.0-test"
ISO="$RELEASES_DIR/$BASE.iso"

# ── Bundle fabrication helper ─────────────────────────────────────────────────

make_bundle() {
  # Minimal fake ISO (1 MB of zeros — enough for size check in verify-iso.sh).
  dd if=/dev/zero of="$ISO" bs=1M count=1 2>/dev/null

  pushd "$RELEASES_DIR" >/dev/null
  sha256sum "$BASE.iso" > "$BASE.iso.sha256"
  sha512sum "$BASE.iso" > "$BASE.iso.sha512"

  # Minimal valid JSON for SBOM companions.
  echo '{"bomFormat":"CycloneDX","specVersion":"1.4","components":[]}' > "$BASE.cdx.json"
  echo '{"spdxVersion":"SPDX-2.3","dataLicense":"CC0-1.0","packages":[]}' > "$BASE.spdx.json"
  echo '{}' > "$BASE.intoto.jsonl"
  echo '{}' > "$BASE.intoto.jsonl.sig"

  # MANIFEST.txt lists every companion.
  {
    sha256sum "$BASE.iso"
    sha256sum "$BASE.iso.sha256"
    sha256sum "$BASE.iso.sha512"
    sha256sum "$BASE.cdx.json"
    sha256sum "$BASE.spdx.json"
    sha256sum "$BASE.intoto.jsonl"
    sha256sum "$BASE.intoto.jsonl.sig"
  } > MANIFEST.txt

  popd >/dev/null
}

make_bundle

# ── Stub qemu-system-x86_64 ───────────────────────────────────────────────────

STUB_DIR="$TMP/bin"
mkdir -p "$STUB_DIR"

QEMU_STUB_LOG="$TMP/qemu-stub.log"
export QEMU_STUB_LOG

cat > "$STUB_DIR/qemu-system-x86_64" <<'SH'
#!/usr/bin/env bash
# Record invocation args for assertions.
echo "QEMU_STUB_ARGS: $*" >> "$QEMU_STUB_LOG"
# Emit the ADR-0008 success marker so the watch loop exits 0 quickly.
echo "lightdm autologin starting"
sleep 1
SH
chmod +x "$STUB_DIR/qemu-system-x86_64"

export PATH="$STUB_DIR:$PATH"

# ── Helper: assert stub was called with -cdrom <path> ────────────────────────

assert_cdrom() {
  local label="$1" expected_iso="$2"
  if grep -qF -- "-cdrom $expected_iso" "$QEMU_STUB_LOG" 2>/dev/null; then
    pass "$label: qemu invoked with -cdrom $expected_iso"
  else
    fail "$label: qemu not invoked with -cdrom $expected_iso (log: $(cat "$QEMU_STUB_LOG" 2>/dev/null || echo '<empty>'))"
  fi
}

assert_stub_silent() {
  local label="$1"
  if [[ ! -s "$QEMU_STUB_LOG" ]]; then
    pass "$label: qemu stub not invoked (correct)"
  else
    fail "$label: qemu stub was invoked despite verify-iso failure (log: $(cat "$QEMU_STUB_LOG"))"
  fi
}

# ── Invariant checks (belt-and-suspenders per S: section) ────────────────────

for script in boot-bios.sh boot-uefi.sh; do
  path="$REPO_ROOT/tests/qemu/$script"
  grep -qF 'lightdm.*autologin|shikshan.local login' "$path" \
    || fail "$script: ADR-0008 success regex missing"
  grep -qF '540' "$path" \
    || fail "$script: ADR-0008 540s deadline missing"
  grep -qF -- '-m 2048' "$path" \
    || fail "$script: ADR-0008 2 GB ceiling (-m 2048) missing"
done
pass "invariant checks: success regex, 540s deadline, -m 2048 present in both scripts"

# ── Case 1: bare basename → bios resolves under RELEASES_DIR ─────────────────

: > "$QEMU_STUB_LOG"
if bash "$REPO_ROOT/tests/qemu/boot-bios.sh" "$BASE.iso"; then
  assert_cdrom "bios bare basename" "$ISO"
else
  fail "bios bare basename: script exited non-zero"
fi

# ── Case 2: full path → bios passes through unchanged ────────────────────────

: > "$QEMU_STUB_LOG"
if bash "$REPO_ROOT/tests/qemu/boot-bios.sh" "$ISO"; then
  assert_cdrom "bios full path" "$ISO"
else
  fail "bios full path: script exited non-zero"
fi

# ── Cases 3a/3b: UEFI bare basename + full path (skip if no OVMF) ─────────────

OVMF_CODE="${OVMF_CODE:-/usr/share/OVMF/OVMF_CODE.fd}"
OVMF_VARS="${OVMF_VARS:-/usr/share/OVMF/OVMF_VARS.fd}"

if [[ -f "$OVMF_CODE" && -f "$OVMF_VARS" ]]; then
  : > "$QEMU_STUB_LOG"
  if bash "$REPO_ROOT/tests/qemu/boot-uefi.sh" "$BASE.iso"; then
    assert_cdrom "uefi bare basename" "$ISO"
  else
    fail "uefi bare basename: script exited non-zero"
  fi

  : > "$QEMU_STUB_LOG"
  if bash "$REPO_ROOT/tests/qemu/boot-uefi.sh" "$ISO"; then
    assert_cdrom "uefi full path" "$ISO"
  else
    fail "uefi full path: script exited non-zero"
  fi
else
  echo "SKIP: OVMF firmware not present — uefi cases skipped"
fi

# ── Case 4: missing MANIFEST.txt → exit 4 before qemu is invoked ─────────────

rm -f "$RELEASES_DIR/MANIFEST.txt"

: > "$QEMU_STUB_LOG"
set +e
bash "$REPO_ROOT/tests/qemu/boot-bios.sh" "$BASE.iso" 2>/dev/null
rc=$?
set -e
if [[ $rc -eq 4 ]]; then
  pass "bios missing MANIFEST.txt: exited 4"
else
  fail "bios missing MANIFEST.txt: expected exit 4, got $rc"
fi
assert_stub_silent "bios missing MANIFEST.txt"

if [[ -f "$OVMF_CODE" && -f "$OVMF_VARS" ]]; then
  : > "$QEMU_STUB_LOG"
  set +e
  bash "$REPO_ROOT/tests/qemu/boot-uefi.sh" "$BASE.iso" 2>/dev/null
  rc=$?
  set -e
  if [[ $rc -eq 4 ]]; then
    pass "uefi missing MANIFEST.txt: exited 4"
  else
    fail "uefi missing MANIFEST.txt: expected exit 4, got $rc"
  fi
  assert_stub_silent "uefi missing MANIFEST.txt"
fi

# ── Summary ───────────────────────────────────────────────────────────────────

echo ""
echo "Results: $PASS passed, $FAIL failed"
[[ $FAIL -eq 0 ]] || exit 1
