# SBOM Policy

We produce a [CycloneDX](https://cyclonedx.org/) SBOM for every release ISO, attach it to the GitHub Release, and gate releases on a CVE scan of that SBOM.

## Format and tool

- **Tool:** [Syft](https://github.com/anchore/syft) v1.x
- **Format:** CycloneDX JSON (`shikshan.cdx.json`)
- **Trigger:** `ci-sbom.yml` runs after `ci-build-iso.yml` succeeds
- **Storage:** uploaded as a workflow artifact; signed by cosign at release time; attached to `vX.Y.Z` GitHub Release

## CVE gate

- **Tool:** [Grype](https://github.com/anchore/grype) latest
- **Policy:** fail the release if any package has a `High` or `Critical` CVE with a known fix
- **Workflow:** `ci-cve-scan.yml` (required-status-check `security / cve-grype`)

Exception process: a `High` or `Critical` with no upstream fix may be allowlisted via `docs/security/cve-allowlist.yml` (created on first need); each entry needs a justification, an expiration date, and a tracking issue.

## What's in the SBOM

- Every Debian package installed in the chroot (name, version, license, supplier)
- Hashes for each package
- The Linux kernel package
- Firmware packages
- Bootloader components
- Any custom .deb under `config/packages.chroot/`
- Module content is **not** in the SBOM (modules have their own per-manifest `checksum` + `signature`; they are content, not software dependencies)

## License compliance

- `ci-license-scan.yml` runs scancode-toolkit against the SBOM and against `modules/`, `config/packages.chroot/`.
- Allowed license SPDX expressions and the deny list live in `policies/license-allowlist.yml` (created when first needed).
- Default deny: any license incompatible with GPL-3.0-or-later for software, or restricted for educational redistribution (case-by-case for content).

## Retention

- Per release: SBOM + signature retained indefinitely on the GitHub Release.
- Per workflow run: artifact retention 90 days (default).
- The audit log records SBOM-related actions (`action: "release"`, target = `shikshan.cdx.json`).

## SBOM diff (between releases)

The release notes auto-include a `cyclonedx-diff` between the previous release's SBOM and the current one (planned). Reviewers should look for:

- New packages — was their addition documented in an ADR?
- License changes — did a transitive dep's license change?
- Removed packages — does anything still depend on them?
