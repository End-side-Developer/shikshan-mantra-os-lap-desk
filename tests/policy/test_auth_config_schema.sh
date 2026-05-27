#!/usr/bin/env bash
# tests/policy/test_auth_config_schema.sh
# SMO-0407: validate /etc/shikshan/auth.yml against its JSON Schema and
# parse-check the OpenAPI document.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$REPO_ROOT"

CONF=config/includes.chroot/etc/shikshan/auth.yml
SCHEMA=modules/catalogs/schemas/auth-config.schema.json
SPEC=docs/architecture/api/auth-v1.yaml

errors=0
require() {
    if eval "$1"; then echo "OK:   $2"; else echo "FAIL: $2" >&2; errors=$((errors + 1)); fi
}

require "[[ -f '$CONF' ]]"   "$CONF exists"
require "[[ -f '$SCHEMA' ]]" "$SCHEMA exists"
require "[[ -f '$SPEC' ]]"   "$SPEC exists"

# 1 — auth.yml parses as YAML
require "python3 -c \"import yaml; yaml.safe_load(open('$CONF', encoding='utf-8'))\"" \
    "$CONF parses as YAML"

# 2 — auth.yml validates against schema (via Python jsonschema, not the broken CLI)
require "python3 -c \"
import json, sys, yaml
import jsonschema
data = yaml.safe_load(open('$CONF', encoding='utf-8'))
schema = json.load(open('$SCHEMA', encoding='utf-8'))
jsonschema.validate(instance=data, schema=schema)
\"" "$CONF validates against $SCHEMA"

# 3 — auth-v1.yaml parses as YAML and openapi field equals 3.1.0
require "python3 -c \"
import yaml, sys
d = yaml.safe_load(open('$SPEC', encoding='utf-8'))
assert d.get('openapi') == '3.1.0', 'openapi field is not 3.1.0'
assert d['info']['title'] == 'Shikshan Mantra Auth API'
assert d['info']['version'] == '1.0.0'
\"" "$SPEC parses with openapi=3.1.0 and expected info"

if [[ $errors -ne 0 ]]; then
    echo "[test_auth_config_schema] $errors failure(s)" >&2
    exit 1
fi
echo "[test_auth_config_schema] all checks passed"
