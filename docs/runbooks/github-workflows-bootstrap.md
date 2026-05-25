# Runbook — GitHub Workflows Bootstrap

The sandbox running the AI agent that scaffolded this repo denies writes to `.github/workflows/` (a standard sandbox defense-in-depth: agents cannot directly inject CI). All workflow definitions live here as fenced code blocks; a maintainer creates the files once.

**Every `name:` in this runbook MUST match exactly the `context:` strings in `.github/rulesets/main-branch.json` and `.github/rulesets/release-tags.json`** — they are the keys binding workflows to branch protection.

## One-time bootstrap

```bash
mkdir -p .github/workflows
# Then create each file below from its fenced code block.
git add .github/workflows/
git commit -S -m "ci(workflows): bootstrap CI pipeline (touches-ci, two-team review required)"
```

---

## A) Policy / lint / commit-format workflows (always-on)

### `.github/workflows/ci-lint.yml`

```yaml
---
name: "lint / yaml-shell-md"
on:
  pull_request:
  push:
    branches: [main]
permissions:
  contents: read
concurrency:
  group: lint-${{ github.ref }}
  cancel-in-progress: true
jobs:
  lint:
    runs-on: ubuntu-latest
    timeout-minutes: 10
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.12" }
      - run: pip install pre-commit yamllint
      - run: pre-commit run --all-files --show-diff-on-failure
```

### `.github/workflows/ci-commit-lint.yml`

```yaml
---
name: "lint / conventional-commits"
on:
  pull_request:
permissions:
  contents: read
  pull-requests: read
jobs:
  commitlint:
    runs-on: ubuntu-latest
    timeout-minutes: 5
    steps:
      - uses: actions/checkout@v4
        with: { fetch-depth: 0 }
      - uses: wagoid/commitlint-github-action@v6
        with:
          configFile: .commitlintrc.json
          failOnWarnings: true
```

Add `.commitlintrc.json` at repo root:
```json
{
  "extends": ["@commitlint/config-conventional"],
  "rules": {
    "type-enum": [2, "always", ["feat","fix","chore","docs","refactor","perf","test","ci","build","security","adr"]],
    "subject-case": [2, "always", ["sentence-case","lower-case"]],
    "header-max-length": [2, "always", 100]
  }
}
```

### `.github/workflows/ci-protected-paths.yml`

```yaml
---
name: "policy / protected-paths"
on:
  pull_request:
permissions:
  contents: read
  pull-requests: read
jobs:
  check:
    runs-on: ubuntu-latest
    timeout-minutes: 5
    steps:
      - uses: actions/checkout@v4
        with: { fetch-depth: 0 }
      - uses: actions/setup-python@v5
        with: { python-version: "3.12" }
      - run: pip install pyyaml
      - run: |
          python scripts/policy/check-protected-paths.py \
            --base "origin/${{ github.base_ref }}" --head HEAD
```

### `.github/workflows/ci-sign-verify.yml`

```yaml
---
name: "security / commit-signatures"
on:
  pull_request:
permissions:
  contents: read
jobs:
  verify:
    runs-on: ubuntu-latest
    timeout-minutes: 10
    steps:
      - uses: actions/checkout@v4
        with: { fetch-depth: 0 }
      - uses: sigstore/cosign-installer@v3
      - name: Verify every commit signed via gitsign / Rekor
        run: |
          set -euo pipefail
          BASE="origin/${{ github.base_ref }}"
          for c in $(git rev-list "$BASE..HEAD"); do
            echo "::group::commit $c"
            git verify-commit "$c" || (echo "::error::unsigned commit $c"; exit 1)
            echo "::endgroup::"
          done
```

### `.github/workflows/ci-secrets-scan.yml`

```yaml
---
name: "security / gitleaks"
on:
  pull_request:
  push:
    branches: [main]
permissions:
  contents: read
jobs:
  gitleaks:
    runs-on: ubuntu-latest
    timeout-minutes: 10
    steps:
      - uses: actions/checkout@v4
        with: { fetch-depth: 0 }
      - uses: gitleaks/gitleaks-action@v2
        env:
          GITLEAKS_ENABLE_UPLOAD_ARTIFACT: "true"
```

### `.github/workflows/ci-trufflehog.yml`

```yaml
---
name: "security / trufflehog"
on:
  pull_request:
  push:
    branches: [main]
permissions:
  contents: read
jobs:
  trufflehog:
    runs-on: ubuntu-latest
    timeout-minutes: 10
    steps:
      - uses: actions/checkout@v4
        with: { fetch-depth: 0 }
      - uses: trufflesecurity/trufflehog@main
        with:
          path: ./
          base: ${{ github.event.repository.default_branch }}
          head: HEAD
          extra_args: --only-verified
```

### `.github/workflows/ci-schema-validate.yml`

```yaml
---
name: "validate / json-schema"
on:
  pull_request:
    paths:
      - "modules/**"
      - "policies/**"
      - "config/includes.chroot/etc/shikshan/**"
      - "tasks/**"
permissions:
  contents: read
jobs:
  validate:
    runs-on: ubuntu-latest
    timeout-minutes: 5
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.12" }
      - run: pip install jsonschema pyyaml
      - run: bash scripts/verify/verify-manifests.sh
```

### `.github/workflows/ci-audit-chain.yml`

```yaml
---
name: "audit / chain-integrity"
on:
  pull_request:
    paths:
      - "docs/audit/**"
      - "scripts/audit/**"
  push:
    branches: [main]
permissions:
  id-token: write     # for OIDC → KMS to fetch HMAC key
  contents: read
jobs:
  verify:
    runs-on: ubuntu-latest
    timeout-minutes: 10
    steps:
      - uses: actions/checkout@v4
        with: { fetch-depth: 0 }
      - uses: actions/setup-python@v5
        with: { python-version: "3.12" }
      - name: Fetch HMAC key via OIDC → KMS
        env:
          ACTIONS_ID_TOKEN_REQUEST_URL: ${{ env.ACTIONS_ID_TOKEN_REQUEST_URL }}
          ACTIONS_ID_TOKEN_REQUEST_TOKEN: ${{ env.ACTIONS_ID_TOKEN_REQUEST_TOKEN }}
        run: |
          # Replace with your KMS/Vault fetch. The output MUST land in
          # SHIKSHAN_AUDIT_HMAC_KEY and SHIKSHAN_AUDIT_HMAC_KEY_V<n> env vars.
          # See docs/runbooks/rotate-signing-key.md for the production wiring.
          echo "SHIKSHAN_AUDIT_HMAC_KEY=$(./scripts/dev/fetch-audit-key.sh)" >> "$GITHUB_ENV"
      - name: Verify chain (strict)
        run: |
          python scripts/audit/verify-chain.py --strict \
            --since-commit "origin/${{ github.base_ref }}"
```

---

## B) SAST / supply-chain workflows

### `.github/workflows/ci-sast-semgrep.yml`

```yaml
---
name: "security / semgrep"
on:
  pull_request:
permissions:
  contents: read
  security-events: write
jobs:
  semgrep:
    runs-on: ubuntu-latest
    timeout-minutes: 15
    container:
      image: returntocorp/semgrep:latest
    steps:
      - uses: actions/checkout@v4
      - run: semgrep ci --config p/ci --config policies/semgrep/
```

### `.github/workflows/ci-codeql.yml`

```yaml
---
name: "security / codeql"
on:
  pull_request:
  schedule:
    - cron: "0 6 * * 1"   # weekly Monday 06:00 UTC
permissions:
  contents: read
  security-events: write
jobs:
  analyze:
    runs-on: ubuntu-latest
    timeout-minutes: 30
    strategy:
      matrix:
        language: [python, javascript]
    steps:
      - uses: actions/checkout@v4
      - uses: github/codeql-action/init@v3
        with: { languages: ${{ matrix.language }} }
      - uses: github/codeql-action/analyze@v3
```

### `.github/workflows/ci-license-scan.yml`

```yaml
---
name: "compliance / license-scan"
on:
  pull_request:
    paths:
      - "config/package-lists/**"
      - "config/packages.chroot/**"
      - "modules/**"
permissions:
  contents: read
jobs:
  scancode:
    runs-on: ubuntu-latest
    timeout-minutes: 20
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.12" }
      - run: pip install scancode-toolkit
      - run: scancode --license --json-pp scan.json modules/ config/packages.chroot/
      - name: Deny GPL-incompatible
        run: python scripts/verify/check-license-compatibility.py scan.json
```

### `.github/workflows/ci-sbom.yml`

```yaml
---
name: "build / sbom-cyclonedx"
on:
  workflow_run:
    workflows: ["build / iso-clean-room"]
    types: [completed]
permissions:
  contents: read
jobs:
  sbom:
    if: ${{ github.event.workflow_run.conclusion == 'success' }}
    runs-on: ubuntu-latest
    timeout-minutes: 20
    steps:
      - uses: actions/download-artifact@v4
        with: { name: shikshan-iso }
      - uses: anchore/sbom-action@v0
        with:
          format: cyclonedx-json
          output-file: shikshan.cdx.json
          file: shikshan.iso
      - uses: actions/upload-artifact@v4
        with: { name: sbom-cyclonedx, path: shikshan.cdx.json }
```

### `.github/workflows/ci-cve-scan.yml`

```yaml
---
name: "security / cve-grype"
on:
  workflow_run:
    workflows: ["build / sbom-cyclonedx"]
    types: [completed]
permissions:
  contents: read
jobs:
  grype:
    if: ${{ github.event.workflow_run.conclusion == 'success' }}
    runs-on: ubuntu-latest
    timeout-minutes: 15
    steps:
      - uses: actions/download-artifact@v4
        with: { name: sbom-cyclonedx }
      - uses: anchore/scan-action@v5
        with:
          sbom: shikshan.cdx.json
          fail-build: true
          severity-cutoff: high
```

---

## C) Build / ISO / QEMU smoke workflows

### `.github/workflows/ci-build-iso.yml`

```yaml
---
name: "build / iso-clean-room"
on:
  pull_request:
    paths:
      - "auto/**"
      - "config/**"
      - "modules/**"
      - "scripts/build/**"
  schedule:
    - cron: "0 22 * * *"   # nightly
  push:
    tags: ["v*.*.*"]
permissions:
  contents: read
jobs:
  build:
    runs-on: ubuntu-latest
    timeout-minutes: 60
    container:
      image: debian:trixie    # pinned per ADR-0001
    steps:
      - uses: actions/checkout@v4
      - run: apt-get update && apt-get install -y live-build qemu-utils
      - run: bash scripts/build/build-iso.sh
      - run: sha256sum artifacts/shikshan.iso | tee artifacts/shikshan.iso.sha256
      - uses: actions/upload-artifact@v4
        with: { name: shikshan-iso, path: "artifacts/shikshan.iso*" }
```

### `.github/workflows/ci-lintian.yml`

```yaml
---
name: "build / lintian"
on:
  workflow_run:
    workflows: ["build / iso-clean-room"]
    types: [completed]
permissions:
  contents: read
jobs:
  lintian:
    if: ${{ github.event.workflow_run.conclusion == 'success' }}
    runs-on: ubuntu-latest
    timeout-minutes: 15
    container: { image: "debian:trixie" }
    steps:
      - uses: actions/checkout@v4
      - uses: actions/download-artifact@v4
        with: { name: shikshan-iso }
      - run: apt-get update && apt-get install -y lintian
      - run: bash tests/lintian/run-lintian.sh shikshan.iso
```

### `.github/workflows/ci-qemu-bios.yml` (template; copy for uefi/persistence/installer/filtering/module-launch)

```yaml
---
name: "e2e / qemu-bios"
on:
  workflow_run:
    workflows: ["build / iso-clean-room"]
    types: [completed]
permissions:
  contents: read
jobs:
  boot:
    if: ${{ github.event.workflow_run.conclusion == 'success' }}
    runs-on: ubuntu-latest
    timeout-minutes: 30
    steps:
      - uses: actions/checkout@v4
      - uses: actions/download-artifact@v4
        with: { name: shikshan-iso }
      - run: sudo apt-get update && sudo apt-get install -y qemu-system-x86 ovmf
      - run: bash tests/qemu/boot-bios.sh shikshan.iso
```

For `ci-qemu-uefi.yml`, `ci-qemu-persistence.yml`, `ci-qemu-installer.yml`, `ci-qemu-filtering.yml`, `ci-qemu-module-launch.yml`: copy the above, change `name:` to the matching context string, and change the script path under `tests/qemu/`.

### `.github/workflows/ci-reproducible.yml`

```yaml
---
name: "release / reproducible"
on:
  push:
    tags: ["v*.*.*"]
permissions:
  contents: read
jobs:
  rebuild:
    runs-on: ubuntu-latest
    timeout-minutes: 90
    strategy:
      matrix:
        builder: [a, b]
    container: { image: "debian:trixie" }
    steps:
      - uses: actions/checkout@v4
      - run: apt-get update && apt-get install -y live-build
      - run: bash scripts/build/reproduce.sh
      - uses: actions/upload-artifact@v4
        with:
          name: iso-build-${{ matrix.builder }}
          path: artifacts/shikshan.iso

  diff:
    needs: rebuild
    runs-on: ubuntu-latest
    steps:
      - uses: actions/download-artifact@v4
        with: { name: iso-build-a, path: a/ }
      - uses: actions/download-artifact@v4
        with: { name: iso-build-b, path: b/ }
      - run: cmp a/shikshan.iso b/shikshan.iso
```

---

## D) Release workflows

### `.github/workflows/release-slsa.yml`

```yaml
---
name: "release / slsa-provenance"
on:
  push:
    tags: ["v*.*.*"]
permissions:
  id-token: write
  contents: write
  actions: read
jobs:
  provenance:
    uses: slsa-framework/slsa-github-generator/.github/workflows/generator_generic_slsa3.yml@v2.0.0
    with:
      base64-subjects: "${{ needs.hash.outputs.subjects }}"
      upload-assets: true
```

### `.github/workflows/release-cosign-sign.yml`

```yaml
---
name: "release / cosign-sign"
on:
  workflow_run:
    workflows: ["release / slsa-provenance"]
    types: [completed]
permissions:
  id-token: write
  contents: write
jobs:
  sign:
    if: ${{ github.event.workflow_run.conclusion == 'success' }}
    runs-on: ubuntu-latest
    timeout-minutes: 15
    steps:
      - uses: sigstore/cosign-installer@v3
      - uses: actions/download-artifact@v4
        with: { name: shikshan-iso }
      - run: cosign sign-blob --yes --bundle shikshan.iso.bundle shikshan.iso
      - uses: actions/upload-artifact@v4
        with: { name: cosign-artifacts, path: shikshan.iso.bundle }
      - name: Sign audit tail
        run: |
          TAIL=$(sqlite3 docs/audit/audit.db \
            "SELECT entry_hash FROM audit_entries ORDER BY sequence_number DESC LIMIT 1;")
          echo "$TAIL" > audit-tail.txt
          cosign sign-blob --yes --bundle audit-tail.bundle audit-tail.txt
```

### `.github/workflows/release-publish.yml`

```yaml
---
name: "release / publish"
on:
  workflow_run:
    workflows: ["release / cosign-sign"]
    types: [completed]
permissions:
  contents: write
jobs:
  publish:
    if: ${{ github.event.workflow_run.conclusion == 'success' }}
    runs-on: ubuntu-latest
    timeout-minutes: 10
    steps:
      - uses: actions/checkout@v4
      - uses: actions/download-artifact@v4
        with: { path: artifacts/ }
      - uses: softprops/action-gh-release@v2
        with:
          files: |
            artifacts/shikshan-iso/shikshan.iso
            artifacts/sbom-cyclonedx/shikshan.cdx.json
            artifacts/cosign-artifacts/shikshan.iso.bundle
            artifacts/cosign-artifacts/audit-tail.bundle
          generate_release_notes: true
          fail_on_unmatched_files: true
```

---

## E) Agent task validation workflows

### `.github/workflows/agent-task-validate.yml`

```yaml
---
name: "agent / task-contract"
on:
  pull_request:
    types: [opened, synchronize, reopened, labeled]
permissions:
  contents: read
  pull-requests: read
jobs:
  validate:
    if: ${{ contains(github.event.pull_request.labels.*.name, 'agent-task') ||
            startsWith(github.head_ref, 'agent/') }}
    runs-on: ubuntu-latest
    timeout-minutes: 5
    steps:
      - uses: actions/checkout@v4
        with: { fetch-depth: 0 }
      - uses: actions/setup-python@v5
        with: { python-version: "3.12" }
      - run: pip install jsonschema pyyaml
      - name: Extract task ID from branch name
        id: task
        run: |
          TASK_ID=$(echo "${{ github.head_ref }}" | grep -oE 'SMO-[0-9]{4}')
          echo "id=$TASK_ID" >> "$GITHUB_OUTPUT"
          test -n "$TASK_ID"
      - name: Verify task contract exists and validates
        run: |
          python -m jsonschema -i "tasks/in-progress/${{ steps.task.outputs.id }}.yml" \
            tasks/schema/task.schema.yml
      - name: Verify changed files are subset of task.I.files_in_scope
        run: |
          python scripts/policy/check-allowlist.py \
            --task "tasks/in-progress/${{ steps.task.outputs.id }}.yml" \
            --base "origin/${{ github.base_ref }}" --head HEAD
```

### `.github/workflows/agent-budget-check.yml`

```yaml
---
name: "agent / budget"
on:
  pull_request:
    types: [opened, synchronize, reopened]
permissions:
  contents: read
  pull-requests: read
jobs:
  budget:
    if: ${{ startsWith(github.head_ref, 'agent/') }}
    runs-on: ubuntu-latest
    timeout-minutes: 5
    steps:
      - uses: actions/checkout@v4
        with: { fetch-depth: 0 }
      - uses: actions/setup-python@v5
        with: { python-version: "3.12" }
      - run: pip install pyyaml
      - name: Compare declared R vs absolute_ceiling
        run: |
          TASK_ID=$(echo "${{ github.head_ref }}" | grep -oE 'SMO-[0-9]{4}')
          python scripts/policy/check-budget.py \
            --task "tasks/in-progress/${TASK_ID}.yml" \
            --pr "${{ github.event.pull_request.number }}" \
            --diff-base "origin/${{ github.base_ref }}"
```

### `.github/workflows/ci-labeler.yml`

```yaml
---
name: "labeler / sensitive-paths"
on:
  pull_request_target:
permissions:
  contents: read
  pull-requests: write
jobs:
  triage:
    runs-on: ubuntu-latest
    timeout-minutes: 5
    steps:
      - uses: actions/labeler@v5
        with:
          repo-token: "${{ secrets.GITHUB_TOKEN }}"
          configuration-path: .github/labeler.yml
          sync-labels: true
```

---

## Pre-merge sanity test

After landing all workflows, file a no-op PR (e.g., comment-only doc edit). Verify in the Checks tab that exactly 23 required checks run and all pass. If a check name doesn't appear, the binding in `.github/rulesets/main-branch.json` is incorrect — fix the typo, do NOT loosen the ruleset.

## When you add a new workflow

1. Open a `touches-ci` PR.
2. Add the workflow file with a stable, unique `name:`.
3. Add the matching `context:` entry to `.github/rulesets/main-branch.json`.
4. Update the table in `.github/workflows/README.md` (and `.github/rulesets/README.md`).
5. Get two-team approval (devex + security).
