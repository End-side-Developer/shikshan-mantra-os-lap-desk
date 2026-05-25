# Module System

Learning modules are signed, verifiable bundles delivered through signed catalogs. This doc covers the trust chain, the manifest contract, and how the launcher resolves and runs a module.

## Trust chain

```
       Root verification key (shipped in /usr/share/shikshan/keys/)
                            │
                            ▼ verifies
              Catalog manifest signature (catalog.signature)
                            │
                            ▼ catalog lists
                Module entries with checksum + signature
                            │
                            ▼ verifies
              Module manifest (module/<id>/manifest.yml)
                            │
                            ▼ refs
              Module content under module/<id>/
```

Key custody:
- **Root key** ships with the OS image; rotated only via a signed OS update.
- **Official catalog key** is a Sigstore keyless certificate bound to the GitHub OIDC subject of this repo's release workflow. Catalog updates are validated against the Rekor transparency log.
- **Community catalog keys** are owned by their publishers; trust level is recorded in `catalog.trust_level` (one of `official`, `verified-community`, `community`, `experimental`). The admin policy file decides which trust levels are allowed.

## Manifest contract (canonical: [PLAN.md](../../PLAN.md))

### Module manifest fields

```yaml
id:               "ai-literacy-basics"        # kebab-case, unique within catalog
version:          "1.0.0"                     # SemVer
title:
  en:             "AI Literacy Basics"
  hi:             "एआई साक्षरता मूल बातें"
language:         ["en", "hi"]                # languages the content is provided in
age_band:         "9-12"
difficulty:       "beginner"
prerequisites:    []                          # list of module IDs
outcomes:
  - "Identify what is and isn't AI"
  - "Use a chatbot safely with consent"
content_type:     "html"                      # html | pdf | video | webxr | blockly | python | jupyter
entrypoint:       "index.html"
required_apps:    []                          # debian package names this module needs at runtime
unlock_rules:
  - kind: "completion"
    of: "intro-to-computing"
license:          "CC-BY-SA-4.0"              # SPDX
checksum:         "sha256:..."                # content tree checksum
signature:        "..."                       # cosign signature; null in dev
```

**Validation:** [modules/catalogs/schemas/module.schema.json](../../modules/catalogs/schemas/module.schema.json). Enforced by `ci-schema-validate.yml` and the `lint-manifest` skill.

### Catalog manifest fields

```yaml
catalog_id:       "shikshan/official"
publisher:        "Shikshan Mantra OS"
trust_level:      "official"
update_url:       "https://catalog.shikshan-mantra.example/official/index.yml"
modules:
  - id: "ai-literacy-basics"
    version: "1.0.0"
    checksum: "sha256:..."
signature:        "..."
```

## Launcher resolution flow

1. Read admin policy → permitted catalogs and trust levels.
2. For each permitted catalog: verify `catalog.signature` against the trust-level's permitted key.
3. For each module in the catalog: verify `module.checksum` matches the on-disk content and `module.signature` verifies under the catalog publisher's key.
4. Apply `unlock_rules` against the local SQLite progress store.
5. Filter by `age_band` and `language` per the active user profile.
6. Render to the launcher UI in the user's selected language; require Hi+En parity for `title` and `description`.

## Adding a first-party module

1. Open a `module-proposal` issue.
2. Maintainer creates a task `SMO-NNNN` of type `module-add`.
3. Agent or human implements under `modules/core/<id>/`:
   - `manifest.yml` (validated by JSON Schema)
   - content files
   - `tests/integration/<id>_test.py` (manifest validates, content checksum matches)
4. CI signs the manifest at release time (`release-cosign-sign.yml`); dev builds leave `signature: null`.
5. Agent appends `id` to `modules/catalogs/official.catalog.yml` (sensitive change — `touches-signing`-adjacent; requires `content` + `security` two-team approval).

## Adding a community catalog

Community catalogs are not in this repo. The OS knows about them through the admin policy's `allowed_catalogs` list. Publishers run their own catalog servers; the OS only verifies signatures and trust levels.
