# tests/fixtures/

Sample data files used by integration tests. Marked `linguist-vendored` in `.gitattributes` so they don't pollute language stats.

| Subdir | Purpose |
|---|---|
| `manifests/` | Sample module manifests for `test_lint_manifest.py` |
| `catalogs/` | Sample catalog manifests |
| `policies/` | Sample admin policy files (valid + invalid) |
| `tasks/` | Sample task contracts (valid + invalid) |

## Conventions

- Each test fixture is named after the test that uses it.
- Invalid fixtures end in `-invalid.<ext>` and are used in negative tests.
- Fixtures never contain real PII; they are synthetic.
- A fixture should be the smallest valid/invalid example that exercises the case under test.

## Updating fixtures

When the corresponding schema changes (e.g., a new required field in `module.schema.json`), update the fixture in the same PR. The `ci-schema-validate` workflow will fail if fixtures drift.
