#!/usr/bin/env bash
# scripts/verify/verify-manifests.sh
#
# Validate every JSON-Schema-governed YAML/JSON in the repo:
#   - tasks/{open,in-progress,blocked,examples}/*.yml against tasks/schema/task.schema.yml
#   - modules/core/*/manifest.yml against modules/catalogs/schemas/module.schema.json
#   - modules/catalogs/*.catalog.yml against modules/catalogs/schemas/catalog.schema.json
#   - config/includes.chroot/etc/shikshan/policy.yml against (TBD schema)

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$REPO_ROOT"

if ! python3 -c "import jsonschema, yaml" 2>/dev/null; then
  echo "[verify-manifests] need python3 with jsonschema + pyyaml" >&2
  echo "                   bash scripts/dev/bootstrap.sh" >&2
  exit 1
fi

failed=0

_validate() {
  local instance="$1"
  local schema="$2"
  if ! python3 -m jsonschema -i "$instance" "$schema" >/dev/null 2>&1; then
    echo "[verify-manifests] FAIL  $instance  (schema: $schema)" >&2
    python3 -m jsonschema -i "$instance" "$schema" >&2 || true
    failed=1
    return 1
  fi
  echo "[verify-manifests] ok    $instance"
}

# Tasks
TASK_SCHEMA="tasks/schema/task.schema.yml"
if [[ -f "$TASK_SCHEMA" ]]; then
  for dir in tasks/open tasks/in-progress tasks/blocked tasks/examples; do
    [[ -d "$dir" ]] || continue
    while IFS= read -r -d '' f; do
      _validate "$f" "$TASK_SCHEMA" || true
    done < <(find "$dir" -maxdepth 1 -name '*.yml' -print0)
  done
fi

# Module manifests
MODULE_SCHEMA="modules/catalogs/schemas/module.schema.json"
if [[ -f "$MODULE_SCHEMA" ]]; then
  while IFS= read -r -d '' f; do
    _validate "$f" "$MODULE_SCHEMA" || true
  done < <(find modules/core -name 'manifest.yml' -print0 2>/dev/null)
fi

# Catalog manifests
CATALOG_SCHEMA="modules/catalogs/schemas/catalog.schema.json"
if [[ -f "$CATALOG_SCHEMA" ]]; then
  while IFS= read -r -d '' f; do
    _validate "$f" "$CATALOG_SCHEMA" || true
  done < <(find modules/catalogs -maxdepth 1 -name '*.catalog.yml' -print0 2>/dev/null)
fi

if [[ $failed -eq 0 ]]; then
  echo "[verify-manifests] OK"
  exit 0
fi
echo "[verify-manifests] FAILED" >&2
exit 2
