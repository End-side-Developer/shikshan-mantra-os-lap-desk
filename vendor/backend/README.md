# smo-backend — Shikshan Mantra OS content backend (phase-1)

First-party reference implementation of the content/catalog backend. **Phase 1
is connectivity only:** a single `GET /health` endpoint over TLS. No auth, no
catalog, no content — those are deferred to follow-up plans.

Authoritative decision: [docs/adr/0017-content-backend-architecture.md](../../docs/adr/0017-content-backend-architecture.md).
Plan: [plans/active/content-backend-bootstrap.md](../../plans/active/content-backend-bootstrap.md).

> **Not a vendored upstream clone.** This is original first-party code that
> happens to live under `vendor/` per [ADR-0003](../../docs/adr/0003-vendor-strategy.md).
> It is tracked in git, but **never read by the ISO build** and **not in the
> SBOM**. See [vendor/README.md](../README.md).

## The endpoint

```text
GET /health  ->  200  {"status": "ok", "version": "0.1.0"}
```

The contract is locked by ADR-0017 decision #6; `tests/test_health.py` enforces
the exact status and body.

## Local development

```bash
cd vendor/backend
python -m venv .venv && . .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -e ".[dev]"

# Plain HTTP (no cert paths given):
python -m smo_backend --host 127.0.0.1 --port 8443
curl http://127.0.0.1:8443/health

# TLS (both cert paths given — self-signed dev CA, see SMO-0701 runbook):
python -m smo_backend --host 127.0.0.1 --port 8443 \
    --certfile server.crt --keyfile server.key
curl --cacert ca.crt https://127.0.0.1:8443/health
```

TLS turns on only when **both** `--certfile` and `--keyfile` are supplied;
otherwise the server speaks plain HTTP.

## Tests

```bash
cd vendor/backend
pip install -e ".[dev]"
pytest
```

## systemd install (smo-be-vm)

`systemd/smo-backend.service` runs the app as the unprivileged `smo-be` user,
restarts on failure, and reads its TLS cert + key from `/etc/smo-backend/`.

```bash
sudo cp systemd/smo-backend.service /etc/systemd/system/smo-backend.service
sudo systemctl daemon-reload
sudo systemctl enable --now smo-backend
```

Prerequisites (provisioned by
[docs/runbooks/backend-vm-bootstrap.md](../../docs/runbooks/backend-vm-bootstrap.md),
SMO-0701): the `smo-be` user, the source tree at `/opt/smo-backend`, and the
cert/key at `/etc/smo-backend/server.crt` / `server.key`.

### Two different config trees — do not conflate

- `/etc/smo-backend/` — **server-side** (this VM): the TLS cert + key the
  backend serves with.
- `/etc/shikshan/backend.yml` — **OS-VM client-side** (SMO-0704): the URL,
  pinned CA cert path, and timeout the OS uses to reach this backend.

They live on different hosts and are unrelated.
