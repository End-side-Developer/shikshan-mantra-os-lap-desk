<!--
ADR-0003 — Vendor strategy.

Establishes how upstream third-party source is pinned, materialised locally, and
integrated into the repo. Drafted under task SMO-0101 on 2026-05-25.

Format: MADR 3.0.0 — https://adr.github.io/madr/
File naming: per docs/adr/README.md.

This ADR is `proposed`. It becomes binding only on merge to `main`. If
superseded, mark this file `status: superseded` and link forward to the new ADR.
-->

---
status: "proposed"
date: 2026-05-25
decision-makers: ["@shikshan/governance", "@shikshan/security"]
consulted: ["@shikshan/devex", "@shikshan/platform"]
informed: ["@shikshan/content"]
---

# 0003 — Vendor strategy: manifest-pinned, gitignored clones, copy-with-attribution

## Context and Problem Statement

Shikshan Mantra OS will eventually need to incorporate code, configuration, and
content from upstream third-party projects (e.g. accessibility tooling, locale
data, exemplar Firefox policies). The repository operates under strict-mode AI
governance: every edit is auditable, the audit chain must be hermetic, and the
ISO build (`live-build`, per ADR-0001) must not perform network fetches at build
time. The Software Bill of Materials (SBOM) we emit must reflect only what ships
in the ISO — nothing that lives transiently in a contributor checkout.

How do we pin, materialise, and integrate upstream source so that the audit
chain stays hermetic, the SBOM stays self-contained, the repo stays small
enough for low-bandwidth contributors, and every byte of upstream code carries
a verifiable license attribution at the moment it lands in the repo?

## Decision Drivers

* Must preserve audit-chain hermeticity (per ADR-0002 once seeded — referenced
  here by number).
* Must keep the SBOM self-contained — supply-chain provenance reflects only
  what ships in the ISO.
* Must not introduce a network step into the ISO build itself (per AGENTS.md
  §12).
* Must keep repo size bounded for low-bandwidth contributors (PLAN.md's 2 GB
  RAM target implies low-end developer environments too).
* Must enable per-pin SPDX license attribution at commit time.
* Must compose cleanly with existing protected-paths and agent-allowlist
  enforcement (policies/protected-paths.yml, policies/agent-allowlist.yml).

## Considered Options

* git submodules
* git subtrees
* git-LFS pointers to upstream tarballs
* Manifest-pinned local clones (gitignored) + copy-with-attribution + sync tool

## Decision Outcome

Chosen option: **"Manifest-pinned local clones (gitignored) + copy-with-attribution + sync tool"**,
because it is the only option that simultaneously preserves audit-chain
hermeticity (no transitive recursive history, no network at build) and keeps
the SBOM self-contained (only copied bytes are tracked, every copy carries an
SPDX trailer at the commit that introduced it).

Mechanics:

* `vendor/MANIFEST.yml` lists each upstream with fields `name`, `upstream_url`,
  `pinned_commit` (40-char hex SHA), `license` (SPDX identifier),
  `integration_targets` (array of repo-relative paths), `last_synced` (ISO
  date), `reviewer_team` (GitHub team handle).
* `vendor/<name>/` clones are local-only — `.gitignore` excludes them. Only
  `vendor/MANIFEST.yml`, `vendor/README.md`, and `vendor/.gitkeep` are tracked.
* Sync tool `scripts/dev/vendor-sync.py` (delivered by SMO-0104) exposes
  `check | pull | verify` subcommands.
* Integration is **copy-with-attribution**: each commit that copies vendor
  content into `config/`, `modules/`, or `scripts/` carries two trailers:
  * `Source-Upstream: vendor/<name>@<short-SHA>`
  * `Source-License: <SPDX-identifier>`
* The `live-build` ISO pipeline never reads from `vendor/`. Deletion of
  `vendor/` does not break the ISO.
* Policy enforcement: `vendor/**` lands on `policies/protected-paths.yml`
  `deny:`; `vendor/MANIFEST.yml` is the sole exception on
  `policies/agent-allowlist.yml` `allow:`; pin updates carry the
  `vendor-pin-update` label (one security-team reviewer) defined in
  `policies/sensitive-change-labels.yml`.

### Consequences

* **Good**, because the repo stays small — only the manifest and copied
  fragments live in git history, not entire upstream trees.
* **Good**, because every integrated byte carries an SPDX license attribution
  in the commit log, satisfying the per-pin license trail requirement.
* **Good**, because the SBOM reflects only what shipped — `vendor/` clones
  are absent from the build root.
* **Good**, because rollback is a single `git revert` of the copy commit; the
  manifest pin remains for forensic trace.
* **Good**, because the audit chain stays hermetic — no submodule recursion,
  no LFS trust root, no surprise network fetch during build.
* **Good**, because the `vendor-pin-update` label gates upstream version bumps
  behind a security-team reviewer.
* **Bad**, because developers must run `scripts/dev/vendor-sync.py --pull`
  locally to materialise clones before reading or copying upstream source.
* **Bad**, because CI cannot directly verify upstream content — it can only
  confirm the pinned SHA is present in `vendor/MANIFEST.yml`.
* **Neutral**, because this introduces two follow-up artifacts:
  `modules/catalogs/schemas/vendor-manifest.schema.json` (SMO-0105) and
  `scripts/dev/vendor-sync.py` (SMO-0104).

### Confirmation

* `scripts/dev/vendor-sync.py --check` (SMO-0104) validates
  `vendor/MANIFEST.yml` against the JSON Schema (SMO-0105).
* `scripts/policy/check-protected-paths.py` asserts `vendor/**` is in `deny:`
  and `vendor/MANIFEST.yml` is in `allow:`.
* `scripts/audit/verify-chain.py` will be extended (follow-up, out of scope
  for this ADR) to assert that `Source-Upstream:` commit trailers match an
  entry in `vendor/MANIFEST.yml`.
* CODEOWNERS routes `/vendor/MANIFEST.yml` and any PR carrying
  `vendor-pin-update` to `@shikshan/security`.

## Pros and Cons of the Options

### git submodules

* **Good**, because submodules are a native git primitive familiar to
  contributors.
* **Bad**, because recursive clones break audit-chain hermeticity — the
  build root no longer corresponds to a single commit graph.
* **Bad**, because signed-commit verification becomes harder: each submodule
  has its own signing posture we do not control.
* **Bad**, because CI runners must be configured for `--recurse-submodules`,
  a footgun that silently disappears upstream content if forgotten.
* **Bad**, because submodule URLs become a supply-chain attack surface that
  `protected-paths.yml` cannot easily reason about (the URL is in
  `.gitmodules`, not in the file content).

### git subtrees

* **Good**, because the working tree is a single self-contained repo — no
  recursive clone, no submodule URL to defend.
* **Bad**, because subtree merges inflate repo history with upstream commits,
  ballooning clone size and breaking PLAN.md's low-bandwidth target.
* **Bad**, because every protected-path check must scan a much larger history,
  raising CI cost.
* **Bad**, because audit-DB rows multiply with each upstream commit pulled in,
  diluting the audit signal.
* **Bad**, because diffs include upstream churn, obscuring the actual
  Shikshan change in review.

### git-LFS pointers to upstream tarballs

* **Good**, because LFS pointers are tiny in-tree, keeping the working repo
  small.
* **Bad**, because LFS is designed for large binaries, not for pinning
  versioned source; the SHA semantics differ.
* **Bad**, because LFS adds a non-git trust root (the LFS server) outside our
  signing posture.
* **Bad**, because LFS bandwidth is paid and metered, raising contributor
  cost for what should be a development convenience.
* **Bad**, because LFS does not address the core hermeticity question — at
  build time we still need a fetch step or a pre-populated cache.

### Manifest-pinned local clones (gitignored) + copy-with-attribution + sync tool

* **Good**, because only the manifest is tracked; the repo stays small.
* **Good**, because pins are explicit 40-char SHAs in a single auditable file.
* **Good**, because license attribution is mandatory at copy time via commit
  trailers — there is no path to landing upstream code without it.
* **Good**, because the SBOM is self-contained: only files actually copied
  appear in the build root and the SBOM scanner sees them.
* **Good**, because deletion of `vendor/` cannot break the ISO — a hard
  guarantee that `live-build` reads only tracked content.
* **Bad**, because contributors must run a local sync step before they can
  read or copy upstream source.
* **Bad**, because CI cannot inspect upstream content directly — it can only
  verify the SHA is pinned in the manifest.
* **Neutral**, because this approach requires us to land a JSON Schema and a
  sync tool as follow-ups (SMO-0104, SMO-0105).

## Supply-chain and audit implications

This ADR introduces two commit-trailer conventions that the audit chain
must learn to recognise:

* `Source-Upstream: vendor/<name>@<short-SHA>` — names the manifest entry and
  the upstream short-SHA from which the copied bytes originate.
* `Source-License: <SPDX-identifier>` — the SPDX license under which the
  copied bytes are redistributed.

Both trailers are mandatory on any commit that copies vendor content into
`config/`, `modules/`, or `scripts/`. `scripts/audit/verify-chain.py` will be
extended (follow-up task) to assert that every such commit carries both
trailers and that the named manifest entry exists with the cited SHA.

Policy intersections this ADR commits to (implementation by the follow-up
PRs that edit `policies/`, not by this ADR):

* `policies/protected-paths.yml` `deny:` gains `vendor/**` — agents may not
  edit anything under `vendor/` by default.
* `policies/agent-allowlist.yml` `allow:` gains `vendor/MANIFEST.yml` as the
  sole exception — pin updates ride the allowlist with the `vendor-pin-update`
  label.
* `policies/sensitive-change-labels.yml` gains a `vendor-pin-update` label
  requiring one `team:security` reviewer.

No change is made to the audit-row format or to the signing material.

## Rollback plan

A single vendor copy is rolled back by `git revert` on the copy commit that
introduced upstream content into `config/`, `modules/`, or `scripts/`. The
matching `vendor/MANIFEST.yml` entry stays in place for forensic trace; its
`last_synced` field is rolled back in a follow-up commit so the manifest
continues to reflect ground truth.

If the entire vendor strategy is rolled back, a new ADR must supersede this
one (`status: superseded`, with `supersedes: 0003` and forward link). The
superseding ADR additionally requires an `allowlist-override` PR to remove
`vendor/**` from `policies/protected-paths.yml` `deny:` and to remove the
`vendor/MANIFEST.yml` exception from `policies/agent-allowlist.yml` `allow:`.
Under strict mode, that PR carries two distinct human reviewers from two
distinct CODEOWNERS teams per `policies/protected-paths.yml`
`sensitive_review_required: 2`.

## More Information

* Related ADRs:
  * ADR-0001 (Debian 13.5 + live-build) — establishes that the ISO build is
    hermetic and must not fetch at build time.
  * ADR-0002 (SQLite hash-chained audit log) — establishes the hermeticity
    requirement this ADR preserves.
* Related policies:
  * `policies/protected-paths.yml` — `vendor/**` deny entry (added in
    follow-up PR; cross-referenced by this ADR).
  * `policies/agent-allowlist.yml` — `vendor/MANIFEST.yml` allow exception
    (added in follow-up PR).
  * `policies/sensitive-change-labels.yml` — `vendor-pin-update` label
    (added in follow-up PR).
  * `policies/escalation-matrix.yml` — `shikshan/security` is the escalation
    contact for `vendor-pin-update` PRs.
* Related follow-up tasks:
  * SMO-0104 — implement `scripts/dev/vendor-sync.py` with
    `check | pull | verify` subcommands.
  * SMO-0105 — author `modules/catalogs/schemas/vendor-manifest.schema.json`.
* External references:
  * SPDX License List — https://spdx.org/licenses/
  * MADR 3.x — https://adr.github.io/madr/
  * Reproducible Builds project — https://reproducible-builds.org/
