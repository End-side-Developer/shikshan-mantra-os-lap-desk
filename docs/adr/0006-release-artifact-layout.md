---
status: "proposed"
date: 2026-05-25
decision-makers: ["@shikshan/release-managers"]
consulted: []
informed: ["@shikshan/devex"]
---

# 0006 - Release artifact bundle layout

## Context and Problem Statement

When releasing Shikshan Mantra OS, we produce a live-build hybrid ISO along with several companion artifacts like checksums, SBOMs, and in-toto attestations. How should these artifacts be structured locally during the build and in CI to ensure reproducibility, SLSA provenance, and standard supply-chain checks?

## Decision Drivers

* Must ensure reproducibility.
* Must support SLSA L2+ provenance.
* Must facilitate supply-chain checks via in-toto attestations.
* Must support safe rollbacks.

## Considered Options

* Option 1: Flat outputs in repo root.
* Option 2: Gitignored `releases/` directory with a tracked `README.md`.
* Option 3: External artifact registry only.

## Decision Outcome

Chosen option: **"Option 2 — Gitignored `releases/` directory with a tracked `README.md`"**, because this provides a clean local workspace while establishing a clear, documented layout for final build outputs without pushing binary blobs into the repository history.

### Consequences

* **Good**, because it prevents accidental commits of large ISOs to git, preserving the repository size.
* **Good**, because a well-defined structure aids in verifying reproducibility.
* **Good**, because the bundle structure supports SLSA L2+ provenance.
* **Good**, because it explicitly accommodates supply-chain checks via `in-toto` attestations.
* **Good**, because rollbacks are simpler by removing/deprecating bad artifact directories or registry tags without undoing git structures incorrectly.

### Confirmation

Compliance with this ADR will be confirmed by `scripts/verify/verify-iso.sh`, matching the directory schema and asserting the presence of the 8 expected files.

## Pros and Cons of the Options

### Option 1 (Flat outputs in repo root)

* **Good**, because it requires no structural changes.
* **Bad**, because it clutters the root directory, risking accidental commits and confusing developers.

### Option 2 (Gitignored releases/ with tracked README)

* **Good**, because it keeps outputs contained and strictly separated from source code.
* **Good**, because a tracked README serves as the canonical bundle schema documentation.
* **Bad**, because it requires updating build scripts to point to the new directory (handled by SMO-0204).

### Option 3 (External artifact registry only)

* **Good**, because it avoids local disk management entirely.
* **Bad**, because local development builds have no standard output directory to verify results locally before pushing.

## Supply-chain and audit implications

Introduces the convention of outputting `shikshan-mantra-os-<version>-<arch>.cdx.json` (CycloneDX SBOM), `*.spdx.json`, `*.intoto.jsonl`, and signature files inside the `releases/` folder. This standardizes our SLSA provenance output format. No upstream pins or signing material change just by outputting here.

## Rollback plan

If this directory layout proves cumbersome, we revert the build scripts (SBOM generation and verify-iso.sh) to their prior output paths, remove `releases/README.md`, and write a superseding ADR. Bad releases can be recalled by deleting the bundle from the artifact registry, retracting the git tag, and drafting a remediation ADR.

## More Information

* Implementation Task: SMO-0204
* Artifacts included:
  1. `shikshan-mantra-os-<version>-<arch>.iso`
  2. `shikshan-mantra-os-<version>-<arch>.iso.sha256`
  3. `shikshan-mantra-os-<version>-<arch>.iso.sha512`
  4. `shikshan-mantra-os-<version>-<arch>.cdx.json` (CycloneDX SBOM)
  5. `shikshan-mantra-os-<version>-<arch>.spdx.json` (SPDX SBOM)
  6. `shikshan-mantra-os-<version>-<arch>.intoto.jsonl` (in-toto attestation)
  7. `shikshan-mantra-os-<version>-<arch>.intoto.jsonl.sig` (cosign signature)
  8. `MANIFEST.txt` (per-file SHA-256 list, human-readable)
