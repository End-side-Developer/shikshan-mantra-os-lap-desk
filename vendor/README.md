<!--
vendor/README.md — scaffolded under task SMO-0102 on 2026-05-25.
Authoritative decision: docs/adr/0003-vendor-strategy.md.
-->

# vendor/

Staging area for **manifest-pinned, gitignored local clones** of upstream
third-party source. This directory exists only to host developer-side material
that informs copy-with-attribution commits into the rest of the repo. It is
**never read by the ISO build** and is **not part of the SBOM**.

Authoritative decision: [docs/adr/0003-vendor-strategy.md](../docs/adr/0003-vendor-strategy.md).

## What lives here

Tracked (committed) files only:

- `vendor/README.md` — this file.
- `vendor/MANIFEST.yml` — the single source of truth for upstream pins. Each
  entry records `name`, `upstream_url`, `pinned_commit` (40-char hex SHA),
  `license` (SPDX identifier), `integration_targets`, `last_synced`, and
  `reviewer_team`. The schema lands in SMO-0105 at
  `modules/catalogs/schemas/vendor-manifest.schema.json`.
- `vendor/.gitkeep` — placeholder so the directory survives empty checkouts.
- `vendor/backend/` — **first-party** content-backend reference impl (phase-1
  `/health` server), NOT a vendored upstream clone. Tracked, but still never
  built into the ISO or the SBOM. See [vendor/backend/README.md](backend/README.md)
  and [ADR-0017](../docs/adr/0017-content-backend-architecture.md). It is
  carved out of the `vendor/*/**` deny rule in `policies/protected-paths.yml`.

Untracked (local-only) material:

- `vendor/<name>/` — each entry's local clone. These directories are
  intentionally **gitignored**. The `.gitignore` rules that enforce this are
  added in **SMO-0103** as a separate policy-override PR; this task (SMO-0102)
  stays within the `docs` budget and does not edit `.gitignore` itself.

If you find an unexpected `vendor/<name>/` directory committed to history, that
is a policy violation — escalate per
[policies/escalation-matrix.yml](../policies/escalation-matrix.yml).

## Workflow

The sync tool `scripts/dev/vendor-sync.py` lands in **SMO-0104** and exposes
three subcommands:

```bash
# Validate vendor/MANIFEST.yml against the JSON Schema (SMO-0105).
python scripts/dev/vendor-sync.py check

# Materialise (or fast-forward) each entry's local clone in vendor/<name>/
# to its pinned_commit. No network calls during the ISO build itself.
python scripts/dev/vendor-sync.py pull

# Confirm each local clone's HEAD matches the manifest's pinned_commit
# and that the recorded SPDX license file is present.
python scripts/dev/vendor-sync.py verify
```

CI cannot inspect upstream content directly. It can only assert that the SHA
in `vendor/MANIFEST.yml` is well-formed and that every
`Source-Upstream:` trailer it sees in a commit references a manifest entry.

## Commit-trailer convention

Any commit that copies bytes out of `vendor/<name>/` and into `config/`,
`modules/`, or `scripts/` **must** carry both of these trailers:

```text
Source-Upstream: vendor/<name>@<short-SHA>
Source-License: <SPDX-identifier>
```

- `<name>` matches the `name` field of a `vendor/MANIFEST.yml` entry.
- `<short-SHA>` is the 7- to 12-character prefix of that entry's
  `pinned_commit`.
- `<SPDX-identifier>` is taken from the [SPDX License List](https://spdx.org/licenses/)
  and matches the entry's `license` field.

A copy commit without both trailers will be rejected by the extended
`scripts/audit/verify-chain.py` (follow-up after SMO-0104/SMO-0105).

## ISO build never reads from vendor/

The `live-build` pipeline (ADR-0001) reads only tracked content from `config/`
and `modules/`. Deleting `vendor/` cannot break the ISO; this is a hard
property of the vendor strategy, not an emergent behaviour. If a build step
ever appears to require `vendor/`, that is a bug — file an issue, do not patch
the build.

## Policy intersections (informational)

Per ADR-0003, the following policy edits are queued behind this scaffold:

- `policies/protected-paths.yml` `deny:` gains `vendor/**` (SMO-0103).
- `policies/agent-allowlist.yml` `allow:` gains `vendor/MANIFEST.yml` as the
  sole exception (SMO-0103).
- `policies/sensitive-change-labels.yml` gains `vendor-pin-update`, requiring
  one `team:security` reviewer (SMO-0103).

Until SMO-0103 lands, treat `vendor/**` as **de facto protected** — do not
edit anything here outside of an explicit task contract whose
`I.files_in_scope` names the path.
