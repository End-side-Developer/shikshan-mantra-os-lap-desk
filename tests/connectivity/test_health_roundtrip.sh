#!/usr/bin/env bash
#
# tests/connectivity/test_health_roundtrip.sh
#
# Plan-level HARD GATE for plans/active/content-backend-bootstrap.md (ADR-0017).
#
# Run INSIDE smo-os-vm with the NAT adapter DISABLED so the only path to the
# backend is the host-only network. Proves the OS VM reaches the backend VM's
# /health endpoint over HTTPS with a PINNED CA, gets 200 + {"status":"ok"},
# in under 1 second.
#
# Usage:
#   bash tests/connectivity/test_health_roundtrip.sh
#
# Config is read from /etc/shikshan/backend.yml (SMO-0704) when present, with
# the ADR-0017 canonical values as fallback. Override with env vars:
#   BACKEND_URL  (e.g. https://192.168.56.20:8443)
#   BACKEND_CA   (e.g. /etc/shikshan/backend-ca.crt)
#   BACKEND_CONFIG (path to backend.yml; default /etc/shikshan/backend.yml)
#
# Exits non-zero on any assertion failure.

set -euo pipefail

CONFIG="${BACKEND_CONFIG:-/etc/shikshan/backend.yml}"
DEFAULT_URL="https://192.168.56.20:8443"
DEFAULT_CA="/etc/shikshan/backend-ca.crt"
MAX_SECONDS="1"

fail() {
    echo "FAIL: $*" >&2
    exit 1
}

# Minimal grep/sed parser for a `key: value` line under the backend: block.
# Keeps the test dependency-free (no yq/jq in the live image). Strips an
# optional inline comment and surrounding double quotes.
read_yaml_value() {
    sed -n "s/^[[:space:]]*$1[[:space:]]*:[[:space:]]*//p" "$CONFIG" 2>/dev/null \
        | head -n1 \
        | sed -e 's/[[:space:]]*#.*$//' -e 's/^"//' -e 's/"$//' -e 's/[[:space:]]*$//'
}

BACKEND_URL="${BACKEND_URL:-}"
BACKEND_CA="${BACKEND_CA:-}"
if [[ -r "$CONFIG" ]]; then
    if [[ -z "$BACKEND_URL" ]]; then BACKEND_URL="$(read_yaml_value url)"; fi
    if [[ -z "$BACKEND_CA" ]]; then BACKEND_CA="$(read_yaml_value ca_cert_path)"; fi
fi
BACKEND_URL="${BACKEND_URL:-$DEFAULT_URL}"
BACKEND_CA="${BACKEND_CA:-$DEFAULT_CA}"

HEALTH_URL="${BACKEND_URL%/}/health"

echo "Probing ${HEALTH_URL} with CA ${BACKEND_CA} (max ${MAX_SECONDS}s)..."

if [[ ! -r "$BACKEND_CA" ]]; then
    fail "pinned CA cert not readable at ${BACKEND_CA} (distribute it per docs/runbooks/backend-vm-bootstrap.md)"
fi

# Informational: a default route usually means the NAT adapter is still
# attached. The gate must run over the host-only path only.
if command -v ip >/dev/null 2>&1 && ip route show default 2>/dev/null | grep -q .; then
    echo "WARN: a default route is present — disable the NAT adapter so this" >&2
    echo "      test proves the host-only path, not an internet route." >&2
fi

body_file="$(mktemp)"
trap 'rm -f "$body_file"' EXIT

# --max-time hard-caps the round-trip at 1s; -w captures status + total time.
# curl exits non-zero on TLS failure, timeout, or connection refused.
metrics="$(curl --cacert "$BACKEND_CA" --max-time "$MAX_SECONDS" \
    -sS -o "$body_file" -w '%{http_code} %{time_total}' \
    "$HEALTH_URL")" || fail "curl failed (TLS / timeout / connection) against ${HEALTH_URL}"

http_code="${metrics%% *}"
time_total="${metrics##* }"
body="$(cat "$body_file")"

echo "  http_code=${http_code} time_total=${time_total}s body=${body}"

if [[ "$http_code" != "200" ]]; then
    fail "expected HTTP 200, got ${http_code}"
fi

if ! printf '%s' "$body" | grep -Eq '"status"[[:space:]]*:[[:space:]]*"ok"'; then
    fail "expected body to contain \"status\":\"ok\", got: ${body}"
fi

# Sub-second assertion (awk handles the float compare; --max-time also caps).
if ! awk -v t="$time_total" 'BEGIN { exit !(t < 1.0) }'; then
    fail "round-trip took ${time_total}s, expected < 1.0s"
fi

echo "PASS: ${HEALTH_URL} -> 200 {\"status\":\"ok\"} in ${time_total}s"
