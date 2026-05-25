---
name: lint-manifest
description: Validate module manifests, catalog manifests, and admin policy files against their JSON Schemas. Use when adding or modifying any file under modules/, modules/catalogs/, or config/includes.chroot/etc/shikshan/.
---

# Skill: lint-manifest

## When to use
- New first-party module under `modules/core/`
- New community catalog entry under `modules/catalogs/`
- Edit to `config/includes.chroot/etc/shikshan/policy.yml`
- Before opening a PR touching any manifest

## Steps

1. **Run the full manifest validator** (one entrypoint, runs all three checks)
   ```bash
   bash scripts/verify/verify-manifests.sh
   ```

2. **Validate a single manifest manually**
   ```bash
   python -m jsonschema -i modules/core/ai-literacy/manifest.yml \
     modules/catalogs/schemas/module.schema.json
   ```

3. **Validate the official catalog**
   ```bash
   python -m jsonschema -i modules/catalogs/official.catalog.yml \
     modules/catalogs/schemas/catalog.schema.json
   ```

## Required fields recap (canonical: PLAN.md "Public Interfaces")

**Module manifest** (`modules/core/<id>/manifest.yml`):
`id, version, title, language, age_band, difficulty, prerequisites, outcomes, content_type, entrypoint, required_apps, unlock_rules, license, checksum, signature`

**Catalog manifest** (`modules/catalogs/<name>.catalog.yml`):
`catalog_id, publisher, trust_level, modules, signature, update_url`

**Admin policy** (`config/includes.chroot/etc/shikshan/policy.yml`):
`safety_mode, allowed_catalogs, blocked_categories, blocked_domains, sync_endpoint, ai_provider_mode, persistence_encryption_required`

## Hindi/English parity rule
Every `title`, `description`, or user-visible string must have both `en` and `hi` values. The schema enforces this via `oneOf` over `{ en, hi }` objects.

## Signature handling
- The `signature` field is `null` in development manifests.
- A pre-release CI job runs the cosign sign step and rewrites it. Do not attempt to set the signature manually.
