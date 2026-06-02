---
name: lint-manifest
description: Validate module manifests, catalog manifests, and admin policy files against their JSON Schemas. Use when adding or modifying any file under modules/, modules/catalogs/, or config/includes.chroot/etc/shikshan/.
---

# Skill: lint-manifest

## When to use

- New first-party module under `modules/core/`
- New community catalog entry under `modules/catalogs/`
- Edit to `config/includes.chroot/etc/shikshan/policy.yml`
- Edit to `config/includes.chroot/etc/shikshan/auth.yml` (ADR-0009 / SMO-0407)
- Edit to `config/includes.chroot/etc/shikshan/backend.yml` (ADR-0017 / SMO-0704)
- Before opening a PR touching any manifest

## Steps

1. **Run the full manifest validator** (one entrypoint, runs all checks)

   ```bash
   bash scripts/verify/verify-manifests.sh
   ```

2. **Validate a single module manifest manually**

   ```bash
   python -m jsonschema -i modules/core/ai-literacy/manifest.yml \
     modules/catalogs/schemas/module.schema.json
   ```

3. **Validate the official catalog**

   ```bash
   python -m jsonschema -i modules/catalogs/official.catalog.yml \
     modules/catalogs/schemas/catalog.schema.json
   ```

4. **Validate the auth client config** (ADR-0009 / SMO-0407)

   ```bash
   python -m jsonschema -i config/includes.chroot/etc/shikshan/auth.yml \
     modules/catalogs/schemas/auth-config.schema.json
   ```

5. **Validate the backend client config** (ADR-0017 / SMO-0704)

   ```bash
   python -m jsonschema -i config/includes.chroot/etc/shikshan/backend.yml \
     modules/catalogs/schemas/backend-config.schema.json
   ```

   The shipped `backend.yml.example` is the reference document; a deployed
   `backend.yml` must validate the same way.

## Required fields recap

Canonical source: `PLAN.md` "Public Interfaces".

**Module manifest** (`modules/core/<id>/manifest.yml`): `id, version,
title, language, age_band, difficulty, prerequisites, outcomes,
content_type, entrypoint, required_apps, unlock_rules, license,
checksum, signature`.

**Catalog manifest** (`modules/catalogs/<name>.catalog.yml`): `catalog_id,
publisher, trust_level, modules, signature, update_url`.

**Admin policy** (`config/includes.chroot/etc/shikshan/policy.yml`):
`safety_mode, allowed_catalogs, blocked_categories, blocked_domains,
sync_endpoint, ai_provider_mode, persistence_encryption_required`.

**Auth config** (`config/includes.chroot/etc/shikshan/auth.yml`): `modes,
backend.url, backend.ca_cert_path, institution.client_id,
institution.endpoint, cache_ttl_seconds`.

**Backend config** (`config/includes.chroot/etc/shikshan/backend.yml`):
`backend.url` (https URI), `backend.ca_cert_path` (absolute path),
`backend.timeout_ms` (integer 100–30000). Schema:
`modules/catalogs/schemas/backend-config.schema.json` (ADR-0017).

## Hindi/English parity rule

Every `title`, `description`, or user-visible string must have both `en`
and `hi` values. The schema enforces this via `oneOf` over `{ en, hi }`
objects.

## Signature handling

- The `signature` field is `null` in development manifests.
- A pre-release CI job runs the cosign sign step and rewrites it. Do not
  attempt to set the signature manually.
