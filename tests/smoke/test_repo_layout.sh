#!/usr/bin/env bash
# tests/smoke/test_repo_layout.sh
#
# Asserts the load-bearing files and directories exist. A scaffolding
# regression test — catches accidental deletes during big refactors.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$REPO_ROOT"

errors=0

_must_exist() {
  if [[ ! -e "$1" ]]; then
    echo "[layout] MISSING $1" >&2
    errors=$((errors + 1))
  fi
}

# Governance
_must_exist AGENTS.md
_must_exist CLAUDE.md
_must_exist AGENT_CARD.md
_must_exist SECURITY.md
_must_exist LICENSE
_must_exist CODE_OF_CONDUCT.md
_must_exist CHANGELOG.md
_must_exist CONTRIBUTING.md
_must_exist README.md
_must_exist PLAN.md

# Policies
_must_exist policies/protected-paths.yml
_must_exist policies/agent-allowlist.yml
_must_exist policies/sensitive-change-labels.yml
_must_exist policies/token-budgets.yml
_must_exist policies/escalation-matrix.yml

# Pre-commit
_must_exist .pre-commit-config.yaml
_must_exist .yamllint
_must_exist .markdownlint.yaml

# Audit
_must_exist docs/audit/audit-log-spec.md
_must_exist docs/audit/keys.json
_must_exist scripts/audit/append-entry.py
_must_exist scripts/audit/verify-chain.py
_must_exist scripts/audit/export-jsonl.py

# .claude
_must_exist .claude/settings.json
_must_exist .claude/agents/planner.md
_must_exist .claude/agents/builder.md
_must_exist .claude/agents/reviewer.md
_must_exist .claude/hooks/pre-tool-use/protected-paths.sh
_must_exist .claude/hooks/post-tool-use/audit-append.sh

# live-build
_must_exist auto/config
_must_exist auto/build
_must_exist auto/clean
_must_exist config/archives/debian.list.chroot
_must_exist config/package-lists/desktop-lxqt.list.chroot
_must_exist config/hooks/live/0040-dnsmasq-school-safe.hook.chroot
_must_exist config/includes.chroot/etc/shikshan/policy.yml

# Tasks
_must_exist tasks/README.md
_must_exist tasks/schema/task.schema.yml
_must_exist tasks/examples/SMO-9001-add-module-manifest.yml

# Docs
_must_exist docs/architecture/overview.md
_must_exist docs/architecture/threat-model.md
_must_exist docs/security/signing-policy.md
_must_exist docs/security/incident-response.md
_must_exist docs/governance/owasp-agentic-top10.md
_must_exist docs/MODEL_CARD.md
_must_exist docs/glossary.md

if [[ $errors -gt 0 ]]; then
  echo "[layout] $errors missing file(s)" >&2
  exit 1
fi
echo "[layout] OK — all load-bearing files present"
