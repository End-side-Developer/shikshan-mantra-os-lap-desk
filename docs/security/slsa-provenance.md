# SLSA Provenance

We target **SLSA v1.1 Level 2+** for every release. This doc explains what that means concretely and how to verify.

## What SLSA L2 requires

- **Source:** version-controlled, change history retained (✅ Git on GitHub)
- **Build:** scripted (✅ `auto/build` via `live-build` + `scripts/build/build-iso.sh`)
- **Provenance:** generated, signed, verifiable (✅ slsa-github-generator emits in-toto DSSE, signed via Sigstore)
- **Authentication:** provenance authenticates the build itself (✅ GitHub OIDC subject in the certificate)
- **Hosted build platform:** the build runs on a hosted CI controlled by us, not by the requester (✅ GitHub Actions on `ubuntu-latest`)

## Beyond L2 (we partially satisfy L3)

- Build is reproducible (ADR-0001 + `ci-reproducible.yml`) — strong evidence of build-platform integrity.
- Build definitions derived from source: yes, every action and every `live-build` config lives in this repo.
- Hardened CI: GitHub-hosted runners; no self-hosted runners; ephemeral.

We do not currently claim L3 because we have not yet completed an independent audit of the build platform.

## In-toto attestation format

We emit a DSSE envelope with predicate type `https://slsa.dev/provenance/v1`:

```json
{
  "_type": "https://in-toto.io/Statement/v1",
  "subject": [{"name": "shikshan.iso", "digest": {"sha256": "..."}}],
  "predicateType": "https://slsa.dev/provenance/v1",
  "predicate": {
    "buildDefinition": {
      "buildType": "https://slsa.dev/buildtypes/github-actions-workflow/v1",
      "externalParameters": { "workflow": ".github/workflows/ci-build-iso.yml" },
      "internalParameters": {},
      "resolvedDependencies": [
        { "uri": "git+https://github.com/shikshan-mantra/shikshan-mantra-os@refs/tags/v0.1.0",
          "digest": {"gitCommit": "..."} },
        { "uri": "https://snapshot.debian.org/archive/debian/<timestamp>/",
          "digest": {"sha256": "..."} }
      ]
    },
    "runDetails": {
      "builder": { "id": "https://github.com/actions/runner" },
      "metadata": { "invocationId": "...", "startedOn": "...", "finishedOn": "..." },
      "byproducts": []
    }
  }
}
```

## Generating provenance

`release-slsa.yml` calls `slsa-framework/slsa-github-generator/.github/workflows/generator_generic_slsa3.yml@v2.0.0`. We use the generic generator because the build runs `live-build` in a Debian container — not a stock Go/Node build that the language-specific generators cover.

The generator:
1. Receives `base64-subjects` (the SHA-256 of `shikshan.iso` from `ci-build-iso.yml`).
2. Runs in a separate, isolated workflow run (cannot be tampered with from the main build).
3. Emits the attestation, signs it with cosign keyless via GitHub OIDC.
4. Uploads `shikshan.iso.intoto.jsonl` as a release asset.

## Verifying provenance

```bash
# Install slsa-verifier
go install github.com/slsa-framework/slsa-verifier/v2/cli/slsa-verifier@latest

slsa-verifier verify-artifact shikshan.iso \
  --provenance-path shikshan.iso.intoto.jsonl \
  --source-uri github.com/shikshan-mantra/shikshan-mantra-os \
  --source-tag v0.1.0
```

A success means: the ISO was produced by `ci-build-iso.yml` from this repo, on a hosted GitHub Actions runner, for this exact tag.

## When verification matters

- A school deployment must verify before flashing USBs at scale
- A package mirror must verify before re-hosting
- A community catalog re-distributor must verify before pinning a version
- Any incident response that questions whether the published ISO matches the source

The verification command above is the same command our `scripts/verify/verify-slsa.sh` runs.
