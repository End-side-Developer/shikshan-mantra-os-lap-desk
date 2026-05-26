#!/usr/bin/env bash
# tests/integration/test_build_iso_resolves_releases_dir.sh
#
# Integration test: mocks the container runtime and asserts that
# scripts/build/build-iso.sh produces a canonical bundle in $RELEASES_DIR.
# Does NOT require docker/podman, syft, or a real live-build environment.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"

# ── hermetic temp dirs ─────────────────────────────────────────────────────────
RELEASES_DIR="$(mktemp -d)"
SHIM_DIR="$(mktemp -d)"
export RELEASES_DIR

cleanup() {
    rm -rf "$RELEASES_DIR" "$SHIM_DIR" "$REPO_ROOT/artifacts"
}
trap cleanup EXIT

# ── fake docker shim (simulates auto/build legacy output) ──────────────────────
cat > "$SHIM_DIR/docker" <<'SHIM'
#!/usr/bin/env bash
# Fake docker: locate the host-side repo mount (-v <host>:/build) and write
# a minimal fake ISO to simulate current auto/build output (artifacts/shikshan.iso).
host_mount=""
args=("$@")
i=0
while [[ $i -lt ${#args[@]} ]]; do
    if [[ "${args[$i]}" == "-v" ]]; then
        (( i++ )) || true
        # Match the repo mount (-v <host>:/build), not the apt cache mount.
        if [[ "${args[$i]}" == *":/build" ]]; then
            host_mount="${args[$i]%%:/build}"
            break
        fi
    fi
    (( i++ )) || true
done
if [[ -z "$host_mount" ]]; then
    echo "[fake-docker] could not find host mount" >&2
    exit 1
fi
mkdir -p "$host_mount/artifacts"
dd if=/dev/zero of="$host_mount/artifacts/shikshan.iso" bs=1M count=1 status=none
SHIM
chmod +x "$SHIM_DIR/docker"
export PATH="$SHIM_DIR:$PATH"

# ── fixed build identity ───────────────────────────────────────────────────────
export VERSION="0.0.0-test"
export ARCH="amd64"
export SMOKE_SBOM=1      # skip syft; write empty SBOM stubs

BASE="shikshan-mantra-os-0.0.0-test-amd64"

# ── run build-iso.sh (--quick skips lintian + verify-iso) ─────────────────────
bash "$REPO_ROOT/scripts/build/build-iso.sh" --quick

# ── assertions ─────────────────────────────────────────────────────────────────
fail() { echo "FAIL: $1" >&2; exit 1; }

[[ -s "$RELEASES_DIR/${BASE}.iso" ]]       || fail "ISO missing or empty at $RELEASES_DIR/${BASE}.iso"
[[ -s "$RELEASES_DIR/${BASE}.iso.sha256" ]] || fail "sha256 missing"
[[ -s "$RELEASES_DIR/${BASE}.iso.sha512" ]] || fail "sha512 missing"
[[ -s "$RELEASES_DIR/MANIFEST.txt" ]]       || fail "MANIFEST.txt missing or empty"
grep -q "${BASE}.iso" "$RELEASES_DIR/MANIFEST.txt" || fail "MANIFEST.txt does not list the ISO"
[[ ! -f "$REPO_ROOT/artifacts/shikshan.iso" ]] || fail "legacy artifacts/shikshan.iso was not moved"

# Verify sha256 is valid
( cd "$RELEASES_DIR" && sha256sum -c "${BASE}.iso.sha256" >/dev/null ) \
    || fail "sha256sum -c failed"

echo "test_build_iso_resolves_releases_dir: PASS"
