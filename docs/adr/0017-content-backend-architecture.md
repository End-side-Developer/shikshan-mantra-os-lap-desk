---
status: "proposed"
date: 2026-06-01
decision-makers: ["@shikshan/platform", "@shikshan/governance"]
consulted: ["@shikshan/security"]
informed: ["@shikshan/content"]
---

# 0017 — Content backend architecture: VirtualBox host-only, second Debian VM, FastAPI + Uvicorn + systemd, self-signed CA, `/health` phase-1 scope

## Context and Problem Statement

[PLAN.md](../../PLAN.md) and [docs/architecture/overview.md](../../docs/architecture/overview.md)
reserve "School sync server" and "Community catalog server" as optional external integrations
the OS may reach, but the repo carries no server reference implementation — per
[docs/architecture/api/README.md](../../docs/architecture/api/README.md), a server is
explicitly out of scope for the current auth API spec. The OS needs a content/catalog
backend so it can later download advanced modules. The full system (auth, catalog, signed
bundle downloads, persistent storage, container packaging) is too large for one increment.

How do we stand up a minimal, reproducible content backend that a developer can run
alongside the Shikshan Mantra OS live image, prove end-to-end connectivity, and leave a
clean separation between infrastructure choices and future API surface?

## Decision Drivers

* Must work on a single Windows developer workstation running VirtualBox — no dedicated
  server or cloud account required.
* Must not modify the ISO build pipeline or ship server code inside the ISO
  (per [ADR-0001](0001-debian-live-build.md) hermeticity requirement).
* Must not block on auth-v1 implementation — connectivity must be provable with a trivial
  `/health` endpoint before any business logic is written.
* Must keep the reference implementation out of the ISO SBOM
  (per [ADR-0003](0003-vendor-strategy.md) vendor strategy — `vendor/` is gitignored, not
  built into the image).
* Must provide a stable runtime config path on the OS side so future tasks can add
  auth-v1, catalog, and content endpoints without re-litigating topology or config format.
* Must keep phase-1 scope narrow: prove the HTTPS round-trip; defer everything else.

## Considered Options

* **A** — Backend runs on the Windows host (native Python process or WSL).
* **B** — Backend runs in a second Debian VM on a VirtualBox host-only network.
* **C** — Backend is containerised on the Windows host (Docker Desktop for Windows).

## Decision Outcome

Chosen option: **"B — Backend in a second Debian VM on a VirtualBox host-only network"**,
because it most closely approximates the eventual production topology (two Debian machines
on a private LAN), requires no additional tooling beyond VirtualBox (already the
hypervisor for the OS VM), and isolates the backend process from Windows-host quirks such
as WSL networking or Docker Desktop NAT.

### Locked decisions

1. **Hypervisor:** VirtualBox (on the Windows host). Two VMs share one host-only adapter
   named `vboxnet-smo` on `192.168.56.0/24`. OS VM gets `.10`; backend VM gets `.20`.
   NAT adapters may be attached transiently for provisioning but are disabled before the
   connectivity proof so the test validates the host-only path, not the internet path.

2. **Backend placement:** a second Debian 13 VM (`smo-be-vm`), not on the Windows host
   and not in the OS VM. The OS VM is a live image; running a server inside it would
   violate the read-only image principle and the 2 GB RAM target.

3. **Backend stack:** Python 3 + FastAPI + Uvicorn under `systemd`
   (`vendor/backend/systemd/smo-backend.service`). Chosen for its minimal footprint,
   no build step, and the maintainer's Python fluency. The service binds to the
   host-only interface on port 8443 over TLS.

4. **TLS:** self-signed dev CA generated once on `smo-be-vm`; CA cert distributed to the
   OS VM at `/etc/shikshan/backend-ca.crt` (referenced in
   `/etc/shikshan/backend.yml`). The OS side pins that CA cert — no system-store trust
   required. In production the CA cert path is replaced with a real CA; no code changes.

5. **OS-side runtime config:** `/etc/shikshan/backend.yml`, validated against
   `modules/catalogs/schemas/backend-config.schema.json`. Keys: `backend.url`,
   `backend.ca_cert_path`, `backend.timeout_ms`. Mirrors the `auth.yml` convention
   already established in the OS config tree.

6. **Phase-1 endpoint:** `GET /health → 200 {"status":"ok","version":"0.1.0"}`. No auth,
   no catalog, no content. The single hard gate for this plan is the OS VM reaching this
   endpoint over HTTPS with the pinned CA, NAT disabled, in under 1 second.

7. **Reference impl location:** `vendor/backend/` per
   [ADR-0003](0003-vendor-strategy.md). The directory is gitignored; only the source
   tree under `vendor/backend/` (tracked) holds the FastAPI app, `pyproject.toml`,
   and the systemd unit. It is **not** materialised into the ISO build root.

### Consequences

* **Good**, because a developer with VirtualBox already installed can follow the runbooks
  and have a working `/health` endpoint in under an hour without any cloud account.
* **Good**, because the topology mirrors production — two Debian machines, private LAN,
  HTTPS with a CA cert — so future tasks slot in without topology rework.
* **Good**, because the `vendor/backend/` placement keeps the backend source auditable
  (tracked in git, pre-commit hooks apply) while keeping it out of the ISO SBOM.
* **Good**, because `/etc/shikshan/backend.yml` + a JSON Schema locks the runtime config
  contract now, before any auth or content tasks are attempted.
* **Bad**, because developers need VirtualBox and a second VM — higher setup cost than
  a native process or WSL.
* **Bad**, because the self-signed CA must be manually distributed from the backend VM
  to the OS VM; there is no automated CA provisioning in phase 1.
* **Neutral**, because phase 1 defers auth, catalog, content, container packaging, and
  persistent storage — those follow-up tasks must each produce their own ADR or task
  contract extending this one.

### Deferred (explicitly out of scope for phase 1)

* Auth-v1 implementation (login / refresh / logout endpoints).
* Content APIs (`/catalog`, `/modules/{id}`, signed bundle downloads).
* Persistent storage (SQLite or PostgreSQL backend for the server).
* Public TLS (Let's Encrypt or internal PKI replacing the self-signed dev CA).
* Observability (metrics, structured logging, health-check alerting).
* Container packaging (Docker / Podman image for the backend service).

### Confirmation

* SMO-0705 (`tests/connectivity/test_health_roundtrip.sh`) is the single hard gate: OS VM
  (NAT adapter disabled) reaches `https://192.168.56.20:8443/health` with the pinned CA
  cert, receives `200 {"status":"ok","version":"0.1.0"}`, in under 1 second.
* `bash scripts/verify/verify-manifests.sh` validates
  `modules/catalogs/schemas/backend-config.schema.json` (SMO-0704).
* `python scripts/audit/verify-chain.py --db docs/audit/audit.db` continues to pass
  after each task in the SMO-0700..0705 batch.
* CODEOWNERS routes `/docs/adr/` PRs to `@shikshan/governance` for governance review.

## Pros and Cons of the Options

### Option A — Backend on the Windows host (native Python or WSL)

* **Good**, because no second VM is required — lower initial setup cost.
* **Bad**, because WSL networking is notoriously fragile across VirtualBox host-only
  adapters; the "works on my machine" failure surface is large.
* **Bad**, because the topology diverges from production: a Windows process or WSL VM is
  not a Debian server on a private LAN.
* **Bad**, because Windows Defender and antivirus interact unpredictably with a listening
  Python process on a non-standard port, requiring per-machine firewall exceptions.

### Option B — Second Debian VM, VirtualBox host-only network (chosen)

* **Good**, because the topology matches eventual production — two Debian machines, one
  private LAN segment, HTTPS.
* **Good**, because VirtualBox is already the hypervisor for the OS VM — no new tooling.
* **Good**, because the host-only adapter is easy to inspect and firewall from both the
  Windows host and inside the VMs.
* **Bad**, because provisioning a second VM is more work than a native process.
* **Neutral**, because the static IP assignments (`.10`/`.20`) are conventions, not
  enforcement; runbook discipline is the guard.

### Option C — Backend containerised on the Windows host (Docker Desktop)

* **Good**, because containers are more reproducible than a bare VM — `docker compose up`
  vs. a multi-step provisioning runbook.
* **Bad**, because Docker Desktop for Windows uses a HyperV or WSL2 backend that
  interacts poorly with VirtualBox host-only networking on the same host (they use
  different hypervisor layers and can conflict).
* **Bad**, because introducing Docker Desktop adds a second hypervisor technology to the
  developer environment, increasing setup complexity.
* **Bad**, because the topology still diverges from production — a Docker container on
  the Windows host is not a Debian VM on a private LAN.

## Supply-chain and audit implications

This ADR introduces `vendor/backend/` as a new tracked directory. Per
[ADR-0003](0003-vendor-strategy.md) mechanics, `vendor/backend/` is tracked in git
(the source tree, not a materialised clone), but its content is **not** copied into
`config/`, `modules/`, or `scripts/`, so:

* No `Source-Upstream:` or `Source-License:` commit trailers are required for SMO-0703
  (the backend skeleton is original code, not upstream vendor content).
* `vendor/backend/` does **not** appear in the ISO SBOM — the live-build pipeline never
  reads from `vendor/`.
* No change to the audit-row format or to signing material.
* `scripts/audit/verify-chain.py` continues to run unchanged; the new files fall outside
  its current scope.

## Rollback plan

If the host-only topology proves unworkable (e.g. VirtualBox host-only networking is
blocked by a site policy), a new ADR must supersede this one with
`status: superseded` and `supersedes: 0017`. The superseding ADR must:

1. Replace the `vendor/backend/` skeleton (a single `git revert` or a new commit
   removing the directory is sufficient — it is not in `policies/protected-paths.yml`
   `deny:`).
2. Remove or replace `modules/catalogs/schemas/backend-config.schema.json` and
   `config/includes.chroot/etc/shikshan/backend.yml.example` via a follow-up PR that
   carries an `allowlist-override` label if those paths fall under a deny rule at the
   time of rollback.
3. Archive SMO-0701..0705 tasks as `obsolete` and open new tasks under the replacement
   plan.

The ADR-0017 file itself is retained with `status: superseded`; it is not
in `policies/protected-paths.yml` `deny:` and may be edited to add the forward link.

## More Information

* Related ADRs:
  * [ADR-0001](0001-debian-live-build.md) — Debian 13.5 + live-build hermeticity;
    constrains that the ISO build must not fetch from `vendor/backend/`.
  * [ADR-0003](0003-vendor-strategy.md) — vendor strategy; `vendor/backend/` follows
    the tracked-source convention (not a gitignored clone).
* Related tasks:
  * SMO-0701 — Backend VM provisioning runbook.
  * SMO-0702 — VirtualBox host-only network guide.
  * SMO-0703 — Backend reference implementation skeleton (`vendor/backend/`).
  * SMO-0704 — OS-side backend client config schema.
  * SMO-0705 — E2E connectivity test + acceptance doc (plan gate).
* Related plan: [plans/active/content-backend-bootstrap.md](../../plans/active/content-backend-bootstrap.md)
* Related policies: `policies/protected-paths.yml` (vendor path governance, to be updated
  if `vendor/backend/` requires a deny entry in a follow-up task).
* External references:
  * FastAPI — https://fastapi.tiangolo.com/
  * Uvicorn — https://www.uvicorn.org/
  * VirtualBox host-only networking — https://www.virtualbox.org/manual/ch06.html#network_hostonly
  * MADR 3.x — https://adr.github.io/madr/
