# Shikshan Mantra OS

An open-source Debian-based education OS for 2 GB RAM laptops, with school-safe defaults, offline-first learning content, signed module catalogs, and AI as a learning assistant.

> **Status:** v1 in development. See [PLAN.md](PLAN.md) for the canonical product spec.

## What it is

- **Base:** Debian 13.5 "trixie" via `live-build`
- **Target:** 64-bit low-end devices, 2 GB RAM minimum
- **Desktop:** LXQt default, IceWM rescue/ultra-low-resource mode
- **Boot paths:** Live USB, VM, install-to-disk (Calamares)
- **Learning:** Kolibri (offline) + custom module launcher (coding via Blockly/Scratch, AR via WebXR with desktop fallback, AI literacy, cyber safety, guidebooks, practical labs)
- **Languages:** Hindi + English at parity
- **Safety:** DNS filtering, Firefox/Chromium enterprise policies, optional E2Guardian, admin override
- **AI:** Offline AI lessons, prompt practice, optional browser/WebGPU experiments, optional server/cloud assistant — no required local LLM
- **Modules:** Signed manifests, official catalog + approved community catalogs
- **Progress:** Local SQLite, optional sync to school/community server

## How this repository is governed

This codebase is largely implemented by AI agents (Claude Code, Copilot, and peers) and reviewed by a human maintainer team. To make agent work observable and safe:

- **[AGENTS.md](AGENTS.md)** is the universal contract every agent must follow before any edit.
- **[policies/](policies/)** declares protected paths, the agent allowlist, sensitive-change labels, token budgets, and escalation.
- **[tasks/](tasks/)** is the file-system-backed task queue with a formal contract schema.
- Every Edit/Write writes a hash-chained row into the audit log ([docs/audit/audit-log-spec.md](docs/audit/audit-log-spec.md)).
- Every commit is signed via Sigstore gitsign (keyless OIDC).
- Releases produce SLSA L2+ provenance, SBOM (CycloneDX), and Cosign signatures.
- Sensitive paths require two-team CODEOWNERS approval enforced by GitHub Rulesets.

If you are an AI agent: stop and read [AGENTS.md](AGENTS.md).

## Repository layout

```
AGENTS.md, CLAUDE.md, AGENT_CARD.md   ← agent governance
policies/                              ← allow/deny lists, labels, budgets, escalation
tasks/                                 ← agent task queue (open/in-progress/completed/blocked)
docs/
  adr/                                 ← architecture decision records (MADR)
  architecture/  security/  runbooks/  governance/  audit/
auto/  config/                         ← Debian live-build (per Debian Live Manual)
modules/                               ← first-party learning modules + signed catalog
scripts/
  audit/  build/  verify/  policy/  dev/
tests/
  smoke/  integration/  qemu/  lintian/  fixtures/
.claude/                               ← Claude Code hooks, subagents, skills, commands
.github/
  workflows/  rulesets/  ISSUE_TEMPLATE/  CODEOWNERS  mergify.yml  renovate.json
```

## For humans contributing code

See [CONTRIBUTING.md](CONTRIBUTING.md). The short version:
1. File an issue using `.github/ISSUE_TEMPLATE/agent-task.yml` (yes, humans use the same template — the contract is uniform).
2. Open a branch `human/<your-handle>/<short-slug>` or `agent/SMO-NNNN-<slug>` if you are using an agent harness.
3. Add or update an ADR if the change is architectural.
4. Add tests.
5. Sign commits with gitsign.
6. Pass all required checks listed in [.github/rulesets/main-branch.json](.github/rulesets/main-branch.json).

## Building locally (preview — full skeleton arrives with Phase 7)

```bash
sudo apt install live-build qemu-system-x86 cosign syft grype lintian pre-commit
bash scripts/dev/bootstrap.sh
bash scripts/build/build-iso.sh
bash scripts/verify/verify-iso.sh artifacts/shikshan.iso
```

## License

GPL-3.0-or-later for OS code, build configuration, and scripts. Learning content under per-module licenses declared in each manifest (`license` field). See [LICENSE](LICENSE).

## Security

Report vulnerabilities per [SECURITY.md](SECURITY.md).
