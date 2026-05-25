# Runbook — GitHub Rulesets Bootstrap

The sandbox running the AI agent that scaffolded this repo could not write into `.github/rulesets/` (security-sensitive metadata directory). The three required ruleset JSONs are embedded below as fenced code blocks. A maintainer with full filesystem access creates them once, then imports.

## Step 1 — Create the directory and write the three files

```bash
mkdir -p .github/rulesets
```

### `.github/rulesets/main-branch.json`

```json
{
  "$comment": "GitHub Ruleset for the `main` branch. Import via: `gh api -X POST /repos/:owner/:repo/rulesets --input .github/rulesets/main-branch.json`. The `required_status_checks[].context` strings MUST match the `name:` of each workflow in .github/workflows/. Changes to this file are touches-policy and need two-team approval (governance + security + devex).",
  "name": "main-branch-protection",
  "target": "branch",
  "enforcement": "active",
  "conditions": {
    "ref_name": { "include": ["refs/heads/main"], "exclude": [] }
  },
  "bypass_actors": [],
  "rules": [
    { "type": "deletion" },
    { "type": "non_fast_forward" },
    { "type": "required_linear_history" },
    {
      "type": "pull_request",
      "parameters": {
        "required_approving_review_count": 1,
        "dismiss_stale_reviews_on_push": true,
        "require_code_owner_review": true,
        "require_last_push_approval": true,
        "required_review_thread_resolution": true
      }
    },
    { "type": "required_signatures" },
    {
      "type": "required_status_checks",
      "parameters": {
        "strict_required_status_checks_policy": true,
        "do_not_enforce_on_create": false,
        "required_status_checks": [
          { "context": "lint / yaml-shell-md" },
          { "context": "validate / json-schema" },
          { "context": "policy / protected-paths" },
          { "context": "security / gitleaks" },
          { "context": "security / trufflehog" },
          { "context": "security / semgrep" },
          { "context": "security / codeql" },
          { "context": "security / commit-signatures" },
          { "context": "lint / conventional-commits" },
          { "context": "compliance / license-scan" },
          { "context": "audit / chain-integrity" },
          { "context": "build / iso-clean-room" },
          { "context": "build / sbom-cyclonedx" },
          { "context": "build / lintian" },
          { "context": "security / cve-grype" },
          { "context": "e2e / qemu-bios" },
          { "context": "e2e / qemu-uefi" },
          { "context": "e2e / persistence" },
          { "context": "e2e / installer" },
          { "context": "e2e / web-filtering" },
          { "context": "e2e / module-launch" },
          { "context": "agent / task-contract" },
          { "context": "agent / budget" }
        ]
      }
    },
    {
      "type": "merge_queue",
      "parameters": {
        "check_response_timeout_minutes": 60,
        "grouping_strategy": "HEADGREEN",
        "max_entries_to_build": 5,
        "max_entries_to_merge": 5,
        "merge_method": "SQUASH",
        "min_entries_to_merge": 1,
        "min_entries_to_merge_wait_minutes": 5
      }
    }
  ]
}
```

### `.github/rulesets/protected-paths.json`

```json
{
  "$comment": "Extra restrictions when a PR touches a sensitive path. Layered on top of main-branch.json (most restrictive rule wins). Requires 2 reviewers from 2 distinct CODEOWNERS teams.",
  "name": "protected-paths-extra",
  "target": "branch",
  "enforcement": "active",
  "conditions": {
    "ref_name": { "include": ["refs/heads/main"], "exclude": [] }
  },
  "bypass_actors": [
    { "actor_id": 0, "actor_type": "OrganizationAdmin", "bypass_mode": "always" }
  ],
  "rules": [
    {
      "type": "pull_request",
      "parameters": {
        "required_approving_review_count": 2,
        "dismiss_stale_reviews_on_push": true,
        "require_code_owner_review": true,
        "require_last_push_approval": true,
        "required_review_thread_resolution": true
      },
      "$applies_when_labels": [
        "touches-bootloader",
        "touches-signing",
        "touches-policy",
        "touches-ci",
        "touches-audit",
        "touches-packages",
        "touches-safety-defaults",
        "allowlist-override"
      ]
    },
    {
      "type": "required_status_checks",
      "parameters": {
        "strict_required_status_checks_policy": true,
        "required_status_checks": [
          { "context": "security / semgrep" },
          { "context": "security / codeql" },
          { "context": "security / commit-signatures" },
          { "context": "audit / chain-integrity" },
          { "context": "release / reproducible" }
        ]
      }
    }
  ]
}
```

### `.github/rulesets/release-tags.json`

```json
{
  "$comment": "Ruleset for release tags. Only signed tags matching vX.Y.Z[-suffix] allowed. SLSA + cosign checks required before the tag is accepted as a release.",
  "name": "release-tags",
  "target": "tag",
  "enforcement": "active",
  "conditions": {
    "ref_name": { "include": ["refs/tags/v*.*.*", "refs/tags/v*.*.*-*"], "exclude": [] }
  },
  "bypass_actors": [],
  "rules": [
    { "type": "deletion" },
    { "type": "non_fast_forward" },
    { "type": "required_signatures" },
    {
      "type": "tag_name_pattern",
      "parameters": {
        "operator": "regex",
        "pattern": "^v[0-9]+\\.[0-9]+\\.[0-9]+(-[A-Za-z0-9.]+)?$",
        "negate": false
      }
    },
    {
      "type": "required_status_checks",
      "parameters": {
        "strict_required_status_checks_policy": true,
        "required_status_checks": [
          { "context": "release / reproducible" },
          { "context": "release / slsa-provenance" },
          { "context": "release / cosign-sign" },
          { "context": "release / publish" }
        ]
      }
    }
  ]
}
```

## Step 2 — Import each ruleset into the repository

```bash
for f in .github/rulesets/*.json; do
  gh api -X POST \
    -H "Accept: application/vnd.github+json" \
    /repos/:owner/:repo/rulesets \
    --input "$f"
done
```

## Required-status-check naming contract

Every `context` string above MUST match a `name:` field in a workflow under `.github/workflows/`. The full mapping table lives in `.github/rulesets/README.md` (also embedded below for reference).

| Ruleset context | Workflow file |
|---|---|
| `lint / yaml-shell-md` | `ci-lint.yml` |
| `validate / json-schema` | `ci-schema-validate.yml` |
| `policy / protected-paths` | `ci-protected-paths.yml` |
| `security / gitleaks` | `ci-secrets-scan.yml` |
| `security / trufflehog` | `ci-trufflehog.yml` |
| `security / semgrep` | `ci-sast-semgrep.yml` |
| `security / codeql` | `ci-codeql.yml` |
| `security / commit-signatures` | `ci-sign-verify.yml` |
| `lint / conventional-commits` | `ci-commit-lint.yml` |
| `compliance / license-scan` | `ci-license-scan.yml` |
| `audit / chain-integrity` | `ci-audit-chain.yml` |
| `build / iso-clean-room` | `ci-build-iso.yml` |
| `build / sbom-cyclonedx` | `ci-sbom.yml` |
| `build / lintian` | `ci-lintian.yml` |
| `security / cve-grype` | `ci-cve-scan.yml` |
| `e2e / qemu-bios` | `ci-qemu-bios.yml` |
| `e2e / qemu-uefi` | `ci-qemu-uefi.yml` |
| `e2e / persistence` | `ci-qemu-persistence.yml` |
| `e2e / installer` | `ci-qemu-installer.yml` |
| `e2e / web-filtering` | `ci-qemu-filtering.yml` |
| `e2e / module-launch` | `ci-qemu-module-launch.yml` |
| `agent / task-contract` | `agent-task-validate.yml` |
| `agent / budget` | `agent-budget-check.yml` |
| `release / reproducible` | `ci-reproducible.yml` |
| `release / slsa-provenance` | `release-slsa.yml` |
| `release / cosign-sign` | `release-cosign-sign.yml` |
| `release / publish` | `release-publish.yml` |
