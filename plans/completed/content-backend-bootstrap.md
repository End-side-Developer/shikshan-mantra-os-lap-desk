---
slug: content-backend-bootstrap
title: Content backend bootstrap — phase 1 connectivity (SMO-0700..SMO-0705)
status: completed
linked_adr: docs/adr/0017-content-backend-architecture.md
linked_tasks:
  - SMO-0700
  - SMO-0701
  - SMO-0702
  - SMO-0703
  - SMO-0704
  - SMO-0705
created: 2026-06-01
completed: 2026-06-02
---

## Context

[PLAN.md](../../PLAN.md) and [docs/architecture/overview.md](../../docs/architecture/overview.md)
both reserve "School sync server" and "Community catalog server" as *optional external
integrations* the OS may talk to. Today the repo has a frozen client-side auth API spec
([docs/architecture/api/auth-v1.yaml](../../docs/architecture/api/auth-v1.yaml)) but
**no server reference implementation** — explicitly out of scope per
[docs/architecture/api/README.md](../../docs/architecture/api/README.md). There is also
no networking guide for a dev VM running the OS to reach a backend, and no runtime config
schema for a content-server URL.

The maintainer wants to ship our own content/catalog backend so the OS can later download
advanced content. The full system is too large for one plan, so this plan is scoped to
**phase 1: stand up the backend in its own VM, make the OS-VM reach it over a host-only
VirtualBox network, and prove it with a `/health` round-trip + written guides.** A
follow-up plan adds the actual content APIs once connectivity is solid.

User-locked decisions:

- **Hypervisor:** VirtualBox (on the Windows host).
- **Backend placement:** runs inside a **second Debian VM**, not on the Windows host.
- **Scope of this plan:** connectivity + `/health` only — no auth, no catalog, no content.
- **ADR:** new ADR-0017 locks the architectural choices.

## Approach

### Topology (locked)

```text
                Windows host (dev workstation)
                          │
                          │  VirtualBox host-only network "vboxnet-smo"  (192.168.56.0/24)
              ┌───────────┼────────────┐
              │           │            │
       ┌──────▼─────┐  ┌──▼──────┐    │
       │ smo-os-vm  │  │ smo-be-vm│   │
       │ Debian 13.5│  │ Debian 13│   │
       │ Shikshan   │  │ Backend  │   │
       │ Mantra OS  │  │ FastAPI  │   │
       └────────────┘  └──────────┘   │
              │            ▲          │
              └── HTTPS ───┘ /health  │
                  (CA pinned)         │
```

- One host-only adapter shared by both VMs. NAT stays attached only for transient apt
  provisioning, and is disabled before the connectivity test, so the proof is that the OS
  reaches the backend over the host-only path (not via the internet).
- Backend stack: **Python 3 + FastAPI + Uvicorn** under `systemd`, self-signed TLS (dev
  CA generated once on the backend VM; CA cert distributed to the OS VM via
  `/etc/shikshan/backend.yml`).
- Single endpoint: `GET /health → 200 {"status":"ok","version":"0.1.0"}`.

### Locked interfaces

- **Backend listen address:** `https://<smo-be-vm-host-only-ip>:8443/health`.
- **OS-side runtime config:** `/etc/shikshan/backend.yml`, schema
  `modules/catalogs/schemas/backend-config.schema.json`. Keys: `backend.url`,
  `backend.ca_cert_path`, `backend.timeout_ms`. Mirrors the existing `auth.yml`
  convention.
- **Reference impl location:** `vendor/backend/` (per
  [ADR-0003](../../docs/adr/0003-vendor-strategy.md) — reference server, not shipped in
  the ISO).

### Deferred (next plan)

- Auth-v1 implementation (login/refresh/logout).
- Content APIs (`/catalog`, `/modules/{id}`, signed bundle downloads).
- Persistent storage, public TLS, observability, container packaging.

## Task breakdown

- **SMO-0700** — ADR-0017 content backend architecture — author the ADR locking VirtualBox
  host-only topology, second-VM placement, FastAPI+Uvicorn+systemd, self-signed CA,
  `/etc/shikshan/backend.yml` contract, `/health` as the phase-1 endpoint.
- **SMO-0701** — Backend VM provisioning runbook —
  `docs/runbooks/backend-vm-bootstrap.md`: VirtualBox VM creation, Debian 13 netinst,
  transient NAT + host-only adapter, unprivileged `smo-be` user, dev CA + server cert
  with `subjectAltName=IP:<host-only-ip>`.
- **SMO-0702** — VirtualBox networking guide —
  `docs/runbooks/virtualbox-host-only-network.md`: host-only adapter `vboxnet-smo`
  setup, static IP assignments (OS=`.10`, backend=`.20`), Windows Defender firewall rule,
  common pitfalls.
- **SMO-0703** — Backend reference impl skeleton — `vendor/backend/`: pyproject,
  `src/smo_backend/app.py` (FastAPI `/health` only), Uvicorn entrypoint,
  `systemd/smo-backend.service`, README.
- **SMO-0704** — OS-side backend client config schema —
  `modules/catalogs/schemas/backend-config.schema.json` +
  `config/includes.chroot/etc/shikshan/backend.yml.example`, plus `lint-manifest` skill
  update.
- **SMO-0705** — E2E connectivity test + acceptance doc —
  `tests/connectivity/test_health_roundtrip.sh` (OS-VM NAT disabled, curl `/health` with
  pinned CA, 200 in <1s) + `docs/runbooks/connectivity-smoke-test.md`. Closes the plan.

### Sequencing

```text
SMO-0700 (ADR)
   ├──► SMO-0701, SMO-0702, SMO-0703, SMO-0704  (parallel)
                                                  │
                                                  └──► SMO-0705 (E2E test)   ← gates plan archive
```

## Verification

Plan is "done" when:

1. ADR-0017 merged with the four locked decisions above.
2. Both runbooks (0701, 0702) are followable end-to-end on a clean Windows host.
3. The backend reference impl boots under systemd in `smo-be-vm`, serves `/health` over
   HTTPS, survives `systemctl restart`.
4. SMO-0705's E2E test passes: OS-VM (NAT disabled, only host-only active) reaches the
   backend-VM's `/health` over HTTPS with the pinned CA, returns 200 + correct JSON, in
   under 1 second. **This is the single hard gate.**
5. This plan auto-archives to `plans/completed/` after SMO-0705 merges, per the
   `/auto-task` step-5a lifecycle bootstrapped by [[plans-folder-bootstrap]] (SMO-0600).
