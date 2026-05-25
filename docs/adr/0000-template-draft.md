<!--
This file is the canonical ADR template for Shikshan Mantra OS.

It is a STRUCTURAL SCAFFOLD only — it carries no architectural decision and
introduces no public interface. It is listed as an immutable seed in
`policies/protected-paths.yml` and may not be edited; replace it only by
superseding it via a new template ADR.

Format: MADR 3.0.0 — https://adr.github.io/madr/
File naming: `NNNN-<kebab-case-title>.md` per [docs/adr/README.md](README.md).
-->

---
status: "proposed"
date: YYYY-MM-DD
decision-makers: ["@<gh-handle-1>", "@<gh-handle-2>"]
consulted: ["@<gh-handle>"]
informed: ["@shikshan/<team>"]
---

# NNNN — {Short imperative title of the decision}

## Context and Problem Statement

{Describe the context and the forces in play, including technological, political,
social, and project-local. State the problem as a free-form question. Two to five
sentences.}

## Decision Drivers

* {driver — e.g. "must preserve audit-chain hermeticity"}
* {driver — e.g. "must work on 2 GB RAM target"}
* {driver — e.g. "must not introduce a network step into the ISO build"}

## Considered Options

* {Option 1 — short label}
* {Option 2 — short label}
* {Option 3 — short label}

## Decision Outcome

Chosen option: **"{Option N}"**, because {one-sentence justification rooted in
the decision drivers}.

### Consequences

* **Good**, because {positive consequence; tie back to a decision driver}.
* **Good**, because {positive consequence}.
* **Bad**, because {negative consequence we are accepting}.
* **Neutral**, because {trade-off worth noting}.

### Confirmation

{How will compliance with this ADR be confirmed in code? Name the test, the
CI check, the audit-chain query, or the manual review step. E.g. "extended
`scripts/policy/check-protected-paths.py` to assert ...".}

## Pros and Cons of the Options

### {Option 1}

* **Good**, because {pro}.
* **Neutral**, because {neutral}.
* **Bad**, because {con}.

### {Option 2}

* **Good**, because {pro}.
* **Bad**, because {con}.

### {Option 3}

* **Good**, because {pro}.
* **Bad**, because {con}.

## Supply-chain and audit implications

{If this ADR changes how upstream code, signing keys, or audit rows are produced,
state it here. Otherwise write "None — no change to upstream pins, signing
material, or audit-row format.".}

## Rollback plan

{How is this decision reverted if it proves wrong? One paragraph. Reference the
specific commit(s), policy edits, or PRs that would need to be undone.}

## More Information

* Related ADRs: {0000-... , 0000-...}
* Related policies: {policies/...yml}
* Related runbooks: {docs/runbooks/...md}
* External references: {URLs, RFCs, upstream issues}
