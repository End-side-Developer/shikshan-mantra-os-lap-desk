# Releases

This directory is the output destination for ISO builds. Its contents are gitignored, except for this README and `.gitkeep`.

The naming convention for files produced during the build is: `shikshan-mantra-os-<version>-<arch>.<ext>`

## Documented Artifacts

- `*.iso` (live-build hybrid ISO)
- `*.iso.sha256`, `*.iso.sha512`
- `*.cdx.json` (CycloneDX SBOM)
- `*.spdx.json` (SPDX SBOM)
- `*.intoto.jsonl` (in-toto attestation)
- `*.intoto.jsonl.sig` (cosign signature)
- `MANIFEST.txt` (per-file SHA-256 list)

For the authoritative architectural decision regarding this release bundle layout, please refer to [ADR-0006](../docs/adr/0006-release-artifact-layout.md).

## Verification

To verify a bundle locally, use the verification script:
```bash
bash scripts/verify/verify-iso.sh releases/<file>.iso
```

To regenerate the SBOM:
```bash
bash scripts/build/sbom-generate.sh releases/<file>.iso
```
