# modules/catalogs/

| File | Purpose |
|---|---|
| [`official.catalog.yml`](official.catalog.yml) | First-party signed catalog (entries added when modules ship) |
| [`schemas/module.schema.json`](schemas/module.schema.json) | JSON Schema for module manifests |
| [`schemas/catalog.schema.json`](schemas/catalog.schema.json) | JSON Schema for catalog manifests |

## Adding a module to the official catalog

When a new module under `modules/core/<id>/` lands, append an entry to `official.catalog.yml`:

```yaml
modules:
  - id: ai-literacy-basics
    version: 1.0.0
    checksum: sha256:0123abcd...        # SHA-256 of the canonical content tree
    path: modules/core/ai-literacy-basics/manifest.yml
```

The `release-cosign-sign.yml` workflow re-signs the catalog and the module's manifest at tag time; for dev builds, `signature: null` is acceptable.

## Community catalogs

Are not in this repo. They live on publishers' own catalog servers. The OS's [admin policy](../../config/includes.chroot/etc/shikshan/policy.yml) decides which publishers and trust levels are allowed.

## Signing trust chain

```
Root verification key (shipped in /usr/share/shikshan/keys/)
    │ verifies
    ▼
Catalog signature (catalog.signature)
    │ catalog entries reference
    ▼
Module entries (id, version, checksum)
    │ checksum validates
    ▼
On-disk content tree
```

Full trust-chain doc: [docs/architecture/module-system.md](../../docs/architecture/module-system.md).
