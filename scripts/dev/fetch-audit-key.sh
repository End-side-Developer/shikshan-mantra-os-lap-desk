#!/usr/bin/env bash
# scripts/dev/fetch-audit-key.sh
#
# Placeholder: in production, this exchanges the GitHub Actions OIDC token
# for a short-lived cloud-KMS-derived HMAC key and prints it on stdout.
#
# The actual exchange is provider-specific:
#   - AWS:   aws sts assume-role-with-web-identity → aws kms generate-mac
#   - GCP:   IDToken → CloudKMS hmacSign
#   - Vault: oidc/login → kv read shikshan/audit-hmac
#
# Until the deploying org wires this, the function falls back to the local
# SHIKSHAN_AUDIT_DEV_KEY env var (insecure; CI verify-chain --strict rejects).

set -euo pipefail

if [[ -n "${SHIKSHAN_AUDIT_HMAC_KEY:-}" ]]; then
  printf '%s' "$SHIKSHAN_AUDIT_HMAC_KEY"
  exit 0
fi

if [[ -n "${ACTIONS_ID_TOKEN_REQUEST_URL:-}" && -n "${ACTIONS_ID_TOKEN_REQUEST_TOKEN:-}" ]]; then
  echo "[fetch-audit-key] OIDC available but no KMS exchange wired yet" >&2
  echo "                   See docs/runbooks/rotate-signing-key.md" >&2
fi

if [[ -n "${SHIKSHAN_AUDIT_DEV_KEY:-}" ]]; then
  printf '%s' "$SHIKSHAN_AUDIT_DEV_KEY"
  exit 0
fi

echo "[fetch-audit-key] no key source available" >&2
exit 1
