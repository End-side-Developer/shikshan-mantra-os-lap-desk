# tests/

Test scaffold for Shikshan Mantra OS. Mirrors the CI workflow naming so a test's location predicts which workflow runs it.

```
tests/
├── smoke/            # Fast (<60s) shell tests — invoked by ci-lint + ci-build-iso post-build
├── integration/      # Python pytest — manifest validation, policy parsing, schema fixtures
├── qemu/             # QEMU boot + smoke scripts — invoked by ci-qemu-* workflows
├── lintian/          # Lintian baselines + override allowlist + runner
└── fixtures/         # Sample manifests, catalogs, policies (linguist-vendored)
```

## Conventions

- **Names:** `test_<topic>.py` (pytest), `<topic>.sh` (shell).
- **Determinism:** every test must be order-independent and pass on a clean checkout.
- **Network:** integration and smoke tests must not require network. QEMU tests may use a virtual NIC but only to a mock.
- **Coverage:** AGENTS.md §7 requires no coverage regression. The `agent-budget-check` workflow uses coverage delta declared in `task.O.coverage_delta` for tracking.

## Running

```bash
# Fast loop while editing
bash tests/smoke/test_protected_paths_policy.sh

# Integration suite
pytest tests/integration/

# Full QEMU smoke (requires the ISO at artifacts/shikshan.iso)
bash tests/qemu/boot-bios.sh artifacts/shikshan.iso
bash tests/qemu/boot-uefi.sh artifacts/shikshan.iso
```

## Adding a test

Follow the placement matrix from AGENTS.md §7:
- Manifest change → `tests/integration/test_<thing>_manifest.py`
- live-build hook change → `tests/smoke/test_<hook>.sh` + a QEMU script if behavior is post-boot
- Module add → `tests/fixtures/<module-id>/` + `tests/integration/test_module_<id>.py`
- Policy change → `tests/integration/test_policy_<name>.py`
