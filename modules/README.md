# modules/

Learning modules — the user-facing content layer of Shikshan Mantra OS.

```
modules/
├── catalogs/
│   ├── official.catalog.yml        # First-party signed catalog
│   └── schemas/                    # JSON Schemas for module + catalog manifests
│       ├── module.schema.json
│       └── catalog.schema.json
└── core/                           # First-party module bundles
    ├── ai-literacy-basics/         # Each has manifest.yml + content/
    ├── blockly-intro/
    ├── cyber-safety-basics/
    └── ...
```

## What is a module?

A self-contained learning unit with:
- A signed `manifest.yml` declaring metadata (id, version, language, age_band, license, checksum, signature)
- Content files (HTML / PDF / Blockly XML / Python notebook / WebXR scene)
- Optional locales (`en/`, `hi/`)
- Hindi + English parity for any user-visible string

## What is a catalog?

A signed registry of modules, with a `trust_level`:
- `official` — produced by this repo, signed by our release workflow
- `verified-community` — third-party publishers we've vetted
- `community` — open submissions
- `experimental` — research/early-stage

The OS's [admin policy file](../config/includes.chroot/etc/shikshan/policy.yml) decides which trust levels are allowed.

## How a module ships

1. Open a [module-proposal issue](../.github/ISSUE_TEMPLATE/module-proposal.yml)
2. Triage assigns an SMO-NNNN task
3. Agent or human implements under `modules/core/<id>/`
4. PR is reviewed by `@shikshan/content` (and `@shikshan/safety` for any content that touches young learners)
5. At release time, `release-cosign-sign.yml` populates the `signature` fields and stamps the catalog

## Validation

- `bash scripts/verify/verify-manifests.sh` validates every module and catalog manifest against its JSON Schema.
- Pre-commit hook `manifest-validate` runs the same check locally.
- `ci-schema-validate.yml` enforces in CI.

See [docs/architecture/module-system.md](../docs/architecture/module-system.md) for the trust chain and launcher resolution flow.
