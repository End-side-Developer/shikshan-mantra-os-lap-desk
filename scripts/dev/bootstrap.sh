#!/usr/bin/env bash
# scripts/dev/bootstrap.sh
#
# One-time setup for a new developer machine. Installs:
#   - pre-commit + hook tools (gitleaks, shellcheck, yamllint, markdownlint, ruff)
#   - cosign + gitsign (Sigstore)
#   - syft + grype (Anchore)
#   - lintian, scancode-toolkit
#
# Run with: bash scripts/dev/bootstrap.sh

set -euo pipefail

OS="$(uname -s)"
echo "[bootstrap] detected OS: $OS"

_install_apt() {
  echo "[bootstrap] using apt-get"
  sudo apt-get update -qq
  sudo apt-get install -y --no-install-recommends \
    python3 python3-pip python3-venv \
    git curl jq sqlite3 \
    shellcheck yamllint \
    lintian \
    qemu-system-x86 ovmf
}

_install_brew() {
  echo "[bootstrap] using brew"
  brew install python git curl jq sqlite shellcheck yamllint cosign syft grype scancode-toolkit
}

case "$OS" in
  Linux)
    if command -v apt-get >/dev/null 2>&1; then _install_apt; fi
    ;;
  Darwin)
    _install_brew
    ;;
  *) echo "[bootstrap] unknown OS $OS; install dependencies manually" ;;
esac

# Python deps
python3 -m pip install --user --upgrade pre-commit pyyaml jsonschema ruff

# Sigstore: cosign + gitsign — install if not present
if ! command -v cosign >/dev/null 2>&1; then
  echo "[bootstrap] installing cosign"
  go install github.com/sigstore/cosign/v2/cmd/cosign@latest 2>/dev/null || {
    echo "[bootstrap] go not available; install cosign manually from https://docs.sigstore.dev/cosign/installation/"
  }
fi

if ! command -v gitsign >/dev/null 2>&1; then
  echo "[bootstrap] installing gitsign"
  go install github.com/sigstore/gitsign@latest 2>/dev/null || {
    echo "[bootstrap] go not available; install gitsign manually from https://docs.sigstore.dev/cosign/git-signing/"
  }
fi

# Configure git for keyless signing
git config --local commit.gpgsign true
git config --local tag.gpgsign true
git config --local gpg.x509.program gitsign
git config --local gpg.format x509

# Pre-commit
pre-commit install --install-hooks --hook-type pre-commit --hook-type commit-msg --hook-type pre-push

# Markdownlint (Node-based, optional)
if ! command -v markdownlint >/dev/null 2>&1 && command -v npm >/dev/null 2>&1; then
  npm install -g markdownlint-cli
fi

echo "[bootstrap] done"
echo "Verify with: pre-commit run --all-files"
