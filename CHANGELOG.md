# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog 1.1.0](https://keepachangelog.com/en/1.1.0/), and this project adheres to [Semantic Versioning 2.0.0](https://semver.org/spec/v2.0.0.html).

AI agents may append entries under `## [Unreleased]` only — never modify a released section. The `append_only:` rule in [policies/agent-allowlist.yml](policies/agent-allowlist.yml) enforces this.

## [Unreleased]

### Added
- Enterprise AI-controlled development scaffold:
  - `AGENTS.md` universal agent contract (agents.md spec)
  - `CLAUDE.md` Claude Code addendum
  - `AGENT_CARD.md` per-agent capability card
  - Root governance: `README.md`, `LICENSE` (GPL-3.0-or-later), `SECURITY.md`, `CODE_OF_CONDUCT.md`, `CONTRIBUTING.md`
- `PLAN.md` — canonical v1 product spec (pre-existing)

### Changed
- (none)

### Removed
- (none)

### Security
- Repository governance defaults set to strict mode: protected paths, two-person rule on sensitive paths, hash-chained audit log, SLSA L2+ target for releases.

[Unreleased]: https://github.com/shikshan-mantra/shikshan-mantra-os/compare/v0.0.0...HEAD
