# Signing Policy

What gets signed, with what, by whom, and how to verify.

## Summary table

| Artifact | Signed with | Issued by | Verified at | Stored in |
|---|---|---|---|---|
| Git commits | Sigstore gitsign (keyless, OIDC) | GitHub OIDC issuer | `ci-sign-verify` workflow + local pre-push | Rekor transparency log |
| Release tags | gitsign signed-tags | GitHub OIDC issuer | `.github/rulesets/release-tags.json` (`required_signatures`) | Rekor |
| ISO artifact | cosign keyless (`sign-blob`) | GitHub OIDC issuer | `scripts/verify/verify-iso.sh` | `.bundle` + Rekor |
| SBOM (CycloneDX) | cosign keyless | GitHub OIDC issuer | downstream consumers | `.bundle` + Rekor |
| SLSA provenance (in-toto DSSE) | slsa-github-generator | GitHub OIDC issuer | `scripts/verify/verify-slsa.sh` | `.intoto.jsonl` |
| Module manifest | cosign keyless (per release) | GitHub OIDC issuer for `modules/catalogs/official.catalog.yml` | Launcher on-device | `signature` field of manifest |
| Official catalog manifest | cosign keyless | GitHub OIDC issuer | Launcher on-device | `signature` field |
| Community catalog manifest | publisher's own keyless or PGP | Publisher | Launcher per `trust_level` | `signature` field |
| Audit row HMAC | HMAC-SHA256 with OIDC-bound KMS key | OIDC → KMS (e.g., AWS KMS) | `scripts/audit/verify-chain.py` | `audit_entries.hmac` column |
| Audit tail (per release) | cosign keyless | GitHub OIDC issuer | downstream consumers | `docs/audit/exports/<tag>.audit-tail.bundle` |
| Debian archive keys | GPG (Debian project) | Debian | apt at build time | `config/archives/debian.key.chroot` |

## Key custody principles

1. **No long-lived private keys** in this repository, in CI secrets, or on developer laptops for project-signing purposes.
2. **OIDC ↔ KMS** for HMAC: GitHub Actions OIDC token is exchanged for a short-lived KMS key access; the raw key never leaves KMS.
3. **OIDC ↔ Sigstore** for commit, tag, ISO, SBOM, provenance, catalog: short-lived X.509 certs from Fulcio; entries logged in Rekor.
4. **Debian archive keys** remain Debian's responsibility; we mirror them as binary blobs in `config/archives/` with `touches-signing` two-team approval required to update.

## OIDC subject identity model

| Identity | Asserted by | Used for |
|---|---|---|
| `repo:shikshan-mantra/shikshan-mantra-os:ref:refs/heads/main` | GitHub Actions OIDC | Release-time signing (ISO, SBOM, catalog, tail HMAC) |
| `repo:shikshan-mantra/shikshan-mantra-os:ref:refs/heads/agent/SMO-*` | GitHub Actions OIDC | Agent-attributable PR signing |
| `repo:shikshan-mantra/shikshan-mantra-os:ref:refs/heads/human/<handle>/*` | GitHub Actions OIDC | Human-attributable PR signing |
| `https://github.com/login/oauth/<user>` | GitHub OAuth | Local developer gitsign (Rekor entry attributable to GH user) |

## Rotation

| Key class | Frequency | Runbook |
|---|---|---|
| Audit HMAC (OIDC-bound KMS key version) | Quarterly + on-suspicion | [rotate-signing-key.md](../runbooks/rotate-signing-key.md) |
| Module catalog publisher (we are the official publisher) | n/a — keyless, no key to rotate | — |
| Debian archive key | Per Debian's schedule | Pull via `touches-signing` PR |
| Sync bearer token (per-school) | Quarterly | School ops own this; we provide rotation steps in the admin guide (out of repo scope) |

## Public verification recipe (any user can run)

```bash
# Verify an ISO release
cosign verify-blob \
  --bundle shikshan.iso.bundle \
  --certificate-identity-regexp '^https://github.com/shikshan-mantra/shikshan-mantra-os/.+' \
  --certificate-oidc-issuer 'https://token.actions.githubusercontent.com' \
  shikshan.iso

# Verify SLSA provenance
cosign verify-attestation \
  --type slsaprovenance \
  --certificate-identity-regexp '^https://github.com/slsa-framework/slsa-github-generator/.+' \
  --certificate-oidc-issuer 'https://token.actions.githubusercontent.com' \
  shikshan.iso.intoto.jsonl

# Verify the audit tail
cosign verify-blob \
  --bundle audit-tail.bundle \
  --certificate-identity-regexp '^https://github.com/shikshan-mantra/.+' \
  --certificate-oidc-issuer 'https://token.actions.githubusercontent.com' \
  audit-tail.txt
```
