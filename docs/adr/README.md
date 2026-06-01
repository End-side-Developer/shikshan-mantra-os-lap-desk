# Architecture Decision Records

We use [MADR 3.x](https://adr.github.io/madr/) for ADRs.

## File naming

`NNNN-<kebab-case-title>.md` — zero-padded sequence number. Numbers are assigned in PR
order, not reservation order — open the PR, then number.

## Lifecycle

1. **Proposed:** open via `.github/ISSUE_TEMPLATE/adr-request.yml`, draft using [0000-template.md](0000-template.md).
2. **Accepted:** merged to `main`. The decision is now binding.
3. **Superseded:** a later ADR explicitly supersedes; the old ADR keeps `status: superseded`
   and links to the new one. Do not delete superseded ADRs.

## Immutable seeds

These ADRs are in `policies/protected-paths.yml` `deny:` — they cannot be edited, only superseded:

- [0000-template.md](0000-template.md) — the templaitself
- [0001-debian-live-build.md](0001-debian-live-build.md) — base OS + build tool choice
- [0002-audit-log-storage.md](0002-audit-log-storage.md) — SQLite hash-chained audit log

## Index

| # | Title | Status |
|---|---|---|
| 0000 | Template | n/a |
| 0001 | Adopt Debian 13.5 + live-build as the base | accepted |
| 0002 | SQLite hash-chained audit log with OIDC-bound HMAC | accepted |
| 0017 | Content backend architecture (VirtualBox host-only, second VM, FastAPI, /health) | proposed |

## Adding an ADR

1. Copy `0000-template.md` to `NNNN-<slug>.md` where NNNN is next free number.
2. Fill in every YAML frontmatter field and every body section.
3. Reference the ADR file path in the implementation PR body.
4. ADR PRs are governance-reviewed (CODEOWNERS routes `/docs/adr/` to governance + maintainers).
