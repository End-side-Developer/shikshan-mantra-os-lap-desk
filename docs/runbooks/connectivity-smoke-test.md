# Connectivity smoke test — OS-VM → backend-VM `/health`

> **This test is the plan-level HARD GATE for
> [plans/completed/content-backend-bootstrap.md](../../plans/completed/content-backend-bootstrap.md).**
> The plan does not archive until
> [`tests/connectivity/test_health_roundtrip.sh`](../../tests/connectivity/test_health_roundtrip.sh)
> passes on a fresh pair of VMs. Locks: [ADR-0017](../adr/0017-content-backend-architecture.md).

This runbook walks a maintainer through running the gate manually. It proves the
Shikshan Mantra OS VM reaches the backend VM's `/health` endpoint over HTTPS with
a pinned CA — over the **host-only** network, not the internet — returning
`200 {"status":"ok"}` in under one second.

## Prerequisites

Complete these first (each has its own runbook):

1. **[backend-vm-bootstrap.md](backend-vm-bootstrap.md)** (SMO-0701) — `smo-be-vm`
   provisioned; `smo-backend.service` active and serving `/health` on
   `192.168.56.20:8443`; dev CA generated.
2. **[virtualbox-host-only-network.md](virtualbox-host-only-network.md)** (SMO-0702)
   — `vboxnet-smo` adapter up; OS VM `.10`, backend VM `.20`.
3. On `smo-os-vm`: the pinned CA cert present at **`/etc/shikshan/backend-ca.crt`**
   and `/etc/shikshan/backend.yml` populated (see
   [backend.yml.example](../../config/includes.chroot/etc/shikshan/backend.yml.example),
   SMO-0704). The test reads `url` and `ca_cert_path` from that file.

## Run the gate

On the **backend VM**, confirm the service is up:

```bash
systemctl is-active smo-backend          # -> active
curl --cacert /etc/smo-backend/pki/ca.crt https://192.168.56.20:8443/health
```

On the **OS VM**:

```bash
# 1. Disable the NAT adapter so the host-only path is the ONLY route.
#    In VirtualBox: smo-os-vm > Settings > Network > Adapter 1 (NAT) > untick
#    "Cable Connected" (or detach), leave Adapter 2 (host-only) attached.
ip route show default        # expect NO output — no default route

# 2. Run the gate.
bash tests/connectivity/test_health_roundtrip.sh
```

Expected output:

```text
Probing https://192.168.56.20:8443/health with CA /etc/shikshan/backend-ca.crt (max 1s)...
  http_code=200 time_total=0.0xx s body={"status":"ok","version":"0.1.0"}
PASS: https://192.168.56.20:8443/health -> 200 {"status":"ok"} in 0.0xx s
```

The script exits `0` on PASS and non-zero on any failed assertion (status,
body, sub-second timing, or unreadable CA).

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `pinned CA cert not readable` | CA not copied to OS VM | Re-run the `scp ... /etc/shikshan/backend-ca.crt` step in backend-vm-bootstrap.md |
| `curl failed (TLS / timeout / connection)` | service down, wrong IP, or NAT-only route | `systemctl status smo-backend` on the backend VM; confirm host-only `.20` reachable (`ping 192.168.56.20`) |
| `SSL certificate problem` | wrong CA or cert SAN mismatch | Confirm server cert `subjectAltName = IP:192.168.56.20`; re-copy the matching CA |
| `expected HTTP 200, got 000` | curl hit `--max-time` (round-trip too slow / no route) | Verify NAT is disabled and the host-only adapter is up |
| `WARN: a default route is present` | NAT adapter still attached | Disable it so the gate proves the host-only path |

## What "pass" means for the plan

A green run here satisfies verification step 4 of the bootstrap plan and is the
sole hard gate for archiving it to `plans/completed/`. Auth, catalog, and
content APIs are explicitly **out of scope** — they follow in a later plan
(ADR-0017 "Deferred").
