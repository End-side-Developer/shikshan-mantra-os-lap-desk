# Runbook — Reproduce a Release

How to independently rebuild a released ISO and confirm it byte-matches the published artifact. Anyone with internet access and a Debian host can do this.

## What "reproducible" means here

Two independent builds from the exact same tag, run on different machines, produce the same SHA-256 for `shikshan.iso`. We enforce this in CI via `ci-reproducible.yml` (which runs two matrix builds and `cmp`s them) and document it here so downstream consumers can re-verify.

## Prerequisites

- Debian 12+ or Ubuntu 22.04+
- `git`, `live-build`, `cosign`, `slsa-verifier`
- ≥ 8 GB disk, ≥ 4 GB RAM

## Steps

```bash
# 1. Pick a tag
TAG=v0.1.0   # the release you want to reproduce
git clone https://github.com/shikshan-mantra/shikshan-mantra-os
cd shikshan-mantra-os
git checkout $TAG

# 2. Rebuild
bash scripts/build/reproduce.sh

# 3. Hash and compare
EXPECTED=$(curl -sL https://github.com/shikshan-mantra/shikshan-mantra-os/releases/download/$TAG/shikshan.iso.sha256 | awk '{print $1}')
ACTUAL=$(sha256sum artifacts/shikshan.iso | awk '{print $1}')
test "$EXPECTED" = "$ACTUAL" && echo "REPRODUCIBLE ✅" || echo "MISMATCH ❌"
```

## Verify SLSA provenance (recommended)

```bash
curl -sLO https://github.com/shikshan-mantra/shikshan-mantra-os/releases/download/$TAG/shikshan.iso.intoto.jsonl
slsa-verifier verify-artifact artifacts/shikshan.iso \
  --provenance-path shikshan.iso.intoto.jsonl \
  --source-uri github.com/shikshan-mantra/shikshan-mantra-os \
  --source-tag $TAG
```

## Verify Cosign signatures

```bash
curl -sLO https://github.com/shikshan-mantra/shikshan-mantra-os/releases/download/$TAG/shikshan.iso.bundle
cosign verify-blob \
  --bundle shikshan.iso.bundle \
  --certificate-identity-regexp '^https://github.com/shikshan-mantra/shikshan-mantra-os/.+' \
  --certificate-oidc-issuer 'https://token.actions.githubusercontent.com' \
  artifacts/shikshan.iso
```

## What to do if the hashes don't match

A mismatch is **not** necessarily an attack — common causes:
1. **Timestamp drift in the build** — file mtime included in some intermediate format. Check whether `scripts/build/reproduce.sh` invokes `live-build` with `--linux-kernel-timestamp-fixed`. ADR-pending.
2. **Snapshot expired** — the snapshot.debian.org pin may have been GC'd at the very long tail. File an issue; we treat this as a release-process bug.
3. **Container image drift** — the pinned `debian:trixie` image was re-tagged by Debian. Use the digest pin (`debian@sha256:...`) from the ADR-0001 follow-up.

If you've ruled out (1)–(3) and the hash still differs, treat as P0 incident — file from `.github/ISSUE_TEMPLATE/security-incident.yml` and follow [incident-response.md § signing-failure](../security/incident-response.md#signing-failure-p1).
