# Runbook — Seed ADRs Bootstrap (human-only)

The three seed ADRs below are in `policies/protected-paths.yml` `deny:`, which means the AI agent that scaffolded this repo could not write them itself. **This is correct** — the seed ADRs document the foundational decisions an AI agent should never overwrite. They are created once, by a human, before the AI starts work.

A maintainer creates these three files exactly as below:

- `docs/adr/0000-template.md`
- `docs/adr/0001-debian-live-build.md`
- `docs/adr/0002-audit-log-storage.md`

Then commits with a signed commit. After this commit, the deny list takes effect.

---

## `docs/adr/0000-template.md`

```markdown
---
# This template follows MADR 3.x — https://adr.github.io/madr/
# COPY this file to `NNNN-<kebab-title>.md`. Do not edit this template
# directly; it is in policies/protected-paths.yml deny:.
status: "proposed"        # proposed | accepted | rejected | deprecated | superseded by [LINK]
date: "YYYY-MM-DD"
deciders: ["@shikshan/governance", "@shikshan/maintainers"]
consulted: ["@shikshan/security"]
informed: ["@shikshan/devex"]
tags: []
---

# NNNN. Short title in present tense

## Context and Problem Statement

What is the issue we are seeing that motivates this decision? What forces are at play? Frame it as a question.

## Decision Drivers

- Driver 1 (e.g., reproducible builds)
- Driver 2 (e.g., 2 GB RAM ceiling)
- Driver 3 (e.g., school-safe defaults)

## Considered Options

- Option A — one line
- Option B — one line
- Option C — one line

## Decision Outcome

Chosen option: **Option X**, because <one-sentence justification>.

### Consequences

- ✅ Positive: ...
- ⚠️ Negative: ...
- 🔁 Follow-up tasks (linked): `tasks/open/SMO-NNNN.yml`

### Confirmation

How will we verify the decision was implemented correctly?

- Test or CI gate: ...
- Metric or KPI: ...

## Pros and Cons of the Options

### Option A
- 👍 ...
- 👎 ...

### Option B
- 👍 ...
- 👎 ...

### Option C
- 👍 ...
- 👎 ...

## More Information

- Links to supporting docs, RFCs, prior art
- Links to the issue or task contract that triggered this ADR
```

---

## `docs/adr/0001-debian-live-build.md`

```markdown
---
status: "accepted"
date: "2026-05-25"
deciders: ["@shikshan/governance", "@shikshan/maintainers", "@shikshan/platform"]
consulted: ["@shikshan/security", "@shikshan/safety"]
informed: ["@shikshan/devex", "@shikshan/content"]
tags: ["foundation", "base-os", "build"]
---

# 0001. Adopt Debian 13.5 "trixie" + live-build as the base OS and build tool

## Context and Problem Statement

We need an OS base and build mechanism that (a) runs on 2 GB RAM 64-bit devices, (b) supports a school-safe default configuration with admin override, (c) ships an offline-first learning stack, (d) can be reproduced by anyone with the same source, and (e) can be governed by AI agents performing most implementation work without those agents being able to silently inject binary blobs.

## Decision Drivers

- 2 GB RAM ceiling (rules out heavy default desktops like GNOME/KDE)
- Free + open license
- Offline-first usage (favors a mature package ecosystem with snapshot pinning)
- Reproducible builds (favors `snapshot.debian.org` + declarative pipelines)
- Strict AI governance: no manual remastering scripts; everything declarative
- Long-term support window (Debian stable ~5-year window fits school deployment)
- Hindi + English locales must be first-class

## Considered Options

- **Option A:** Debian 13.5 "trixie" + `live-build`
- **Option B:** Ubuntu 24.04 LTS + cubic/livefs-edit
- **Option C:** Alpine + custom apk-based pipeline
- **Option D:** Roll our own minimal base via `debootstrap` + bash

## Decision Outcome

Chosen option: **Option A — Debian 13.5 + live-build**, because Debian's snapshot archive enables byte-reproducible builds, `live-build` is a declarative pipeline that maps 1:1 onto our governance model (every artifact has a config source file in `config/`), and the Debian stable lifecycle matches schools' multi-year refresh cycles.

### Consequences

- ✅ Reproducible builds via `snapshot.debian.org` pins (`config/archives/debian.list.chroot`)
- ✅ Declarative `auto/config`, `config/hooks/`, `config/package-lists/` map cleanly to `policies/agent-allowlist.yml`
- ✅ Lightweight LXQt + IceWM available out-of-the-box in default repos
- ✅ Hindi/English locales and fonts are first-class
- ⚠️ Some non-free firmware for older laptops requires an explicit ADR + signed-commit flow
- 🔁 Follow-up: ADRs needed for Calamares installer config, persistence layout, bootloader signing

### Confirmation

- `ci-build-iso.yml` produces a clean ISO from this repo in <60 minutes
- `ci-reproducible.yml` rebuilds the same tag on two independent runners and the SHA-256 matches
- A 2 GB-RAM QEMU smoke boots to a usable LXQt session

## Pros and Cons of the Options

### Option A — Debian 13.5 + live-build
- 👍 Mature snapshot.debian.org for reproducibility
- 👍 Declarative pipeline aligns with AI governance
- 👍 LXQt + IceWM + Kolibri all packaged
- 👎 Fewer modern UX conveniences than Ubuntu tooling

### Option B — Ubuntu 24.04 LTS + cubic/livefs-edit
- 👍 Larger ecosystem of derivatives, smoother UX
- 👎 cubic is interactive; remastering pipelines tend to be imperative
- 👎 Snap dependency creep complicates 2 GB-RAM target

### Option C — Alpine + custom apk
- 👍 Smallest footprint
- 👎 Tiny educational-content package ecosystem
- 👎 musl libc compatibility risk for some learning apps

### Option D — Roll our own (debootstrap + bash)
- 👍 Maximum control
- 👎 Massive ongoing maintenance burden
- 👎 Anti-pattern for AI governance

## More Information

- [Debian Live Manual](https://live-team.pages.debian.net/live-manual/html/live-manual.en.html)
- [Debian 13.5 trixie release](https://www.debian.org/releases/trixie/)
- [snapshot.debian.org](https://snapshot.debian.org)
- [Reproducible Builds — Debian](https://wiki.debian.org/ReproducibleBuilds)
- PLAN.md ("Locked choices: Debian live-build, 2GB 64-bit target ...")
```

---

## `docs/adr/0002-audit-log-storage.md`

```markdown
---
status: "accepted"
date: "2026-05-25"
deciders: ["@shikshan/governance", "@shikshan/security", "@shikshan/maintainers"]
consulted: ["@shikshan/devex", "@shikshan/release-managers"]
informed: ["@shikshan/platform"]
tags: ["governance", "audit", "security", "ai"]
---

# 0002. SQLite hash-chained audit log with OIDC-bound HMAC

## Context and Problem Statement

AI agents perform most edits in this repository. To make every state change observable, attributable, and tamper-evident, we need an audit log that:

1. Is append-only in storage, not just by policy
2. Detects reordering, deletion, and modification of past entries
3. Attributes each entry to a specific agent (via OIDC subject) or human (via GitHub handle + signed commit)
4. Survives review by people who weren't online when the action happened
5. Has no signing keys stored in the repo or in long-lived CI secrets
6. Adds no external infrastructure dependency for a greenfield project

## Decision Drivers

- Tamper-evidence at the storage layer
- Greenfield project — no external infra
- AI-agent attribution via Sigstore OIDC subjects
- Forensic readability by humans without running the repo locally
- Performance: append + verify completes in seconds for ≥100k rows
- Survives key rotation

## Considered Options

- **Option A:** SQLite at `docs/audit/audit.db` with append-only triggers, hash-chained rows, HMAC signed via OIDC→KMS, periodic JSONL exports
- **Option B:** JSONL-only at `docs/audit/log.jsonl`, hash-chained, HMAC signed
- **Option C:** External log shipper (e.g., a managed transparency log like Rekor per entry)
- **Option D:** No structured audit log — rely on `git log` + PR review

## Decision Outcome

Chosen option: **Option A — SQLite + hash chain + OIDC-bound HMAC + JSONL exports**, because it provides storage-layer append-only enforcement (triggers), fast indexed verification, no external infrastructure, key custody outside the repo, and periodic JSONL exports for human review and downstream consumers.

### Consequences

- ✅ Tamper-evident at storage layer: `RAISE(ABORT)` triggers reject UPDATE/DELETE
- ✅ `verify-chain.py` walks ~100k rows in <1s on commodity hardware
- ✅ No long-lived secret: HMAC key issued per CI run via GitHub OIDC → KMS
- ✅ JSONL exports under `docs/audit/exports/` are append-only artifacts for offline review
- ✅ Release-time cosign signature on the latest `entry_hash` pins the chain into Sigstore Rekor
- ⚠️ Binary `audit.db` complicates Git diffs — mitigated by `-diff -merge` gitattribute and the rule that only `scripts/audit/append-entry.py` writes
- ⚠️ Concurrent agent sessions need WAL mode + advisory locks — implemented in `append-entry.py`
- 🔁 Follow-up: monthly export workflow, incident-response runbook section

### Confirmation

- `ci-audit-chain.yml` runs `verify-chain.py --strict` on every PR touching `docs/audit/**`
- `release-cosign-sign.yml` signs the tail `entry_hash` on every tag
- Manual `python scripts/audit/verify-chain.py --db docs/audit/audit.db` exits 0 on a clean chain

## Pros and Cons of the Options

### Option A — SQLite + hash chain + OIDC-bound HMAC
- 👍 Storage-layer append-only (triggers)
- 👍 Fast indexed verification
- 👍 Atomic appends with WAL
- 👍 No external infra
- 👎 Binary file in Git; needs gitattribute care

### Option B — JSONL only
- 👍 Human-readable, Git-diff-friendly
- 👎 No append-only enforcement at the file level
- 👎 Concurrent appends race more easily
- 👎 Verification requires reading the entire file each time

### Option C — External transparency log (Rekor per entry)
- 👍 Strongest tamper-evidence
- 👎 Latency: every Edit/Write hits a network service
- 👎 Network dependency for offline-first dev workflow
- 👎 Significant operational overhead for a greenfield repo

### Option D — `git log` + PR review only
- 👍 Zero new infrastructure
- 👎 Doesn't capture pre-commit edits or rejected attempts
- 👎 No HMAC; trivially forged with a re-author
- 👎 Doesn't satisfy OWASP Agentic Top 10 §2 audit requirements

## More Information

- [docs/audit/audit-log-spec.md](../audit/audit-log-spec.md) — full schema and protocol
- [scripts/audit/append-entry.py](../../scripts/audit/append-entry.py)
- [scripts/audit/verify-chain.py](../../scripts/audit/verify-chain.py)
- [Sigstore gitsign](https://docs.sigstore.dev/cosign/keyless/)
- [NIST AI 600-1](https://www.nist.gov/itl/ai-risk-management-framework)
- [SLSA v1.1 build provenance](https://slsa.dev/spec/v1.1/)
```

---

## Commit them

```bash
# After creating the three files exactly as above:
git add docs/adr/0000-template.md docs/adr/0001-debian-live-build.md docs/adr/0002-audit-log-storage.md
git commit -S -m "adr: seed 0000-template, 0001-debian-live-build, 0002-audit-log-storage"
```

From this point on, agents are free to add `0003-*.md` and onward, but cannot edit these three seeds (protected-paths.yml enforces).
