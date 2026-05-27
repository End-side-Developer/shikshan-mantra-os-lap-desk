---
status: "proposed"
date: 2026-05-26
decision-makers: ["@shikshan/platform", "@shikshan/devex"]
consulted: []
informed: ["@shikshan/release-managers"]
---

# 0008 — QEMU smoke success criteria (BIOS + UEFI, 2 GB RAM, serial markers)

## Context and Problem Statement

Shikshan Mantra OS targets 64-bit low-end devices with 2 GB RAM (PLAN.md line 4;
AGENTS.md §13 "2 GB RAM ceiling for the default profile"). Before shipping an ISO,
we need an automated gate that proves the image actually boots on the target
hardware class. A full UI test (desktop rendering, audio, GPU) is expensive and
belongs in a later phase; for now we need a lightweight smoke that answers one
question: **does the live session reach a usable login state within the documented
RAM ceiling?**

ADR-0001 (Debian 13.5 + live-build — to be seeded; pre-allocated in
`policies/protected-paths.yml`) establishes the top-level live-build commitment.
PLAN.md line 35 requires "Boot: QEMU BIOS, QEMU UEFI, 2 GB RAM profile" as an
explicit gating matrix. The scripts `tests/qemu/boot-bios.sh` and
`tests/qemu/boot-uefi.sh` already implement those smokes, but no decision record
explains the success regex, the 540-second inner deadline, the 600-second outer
process cap, or the 2048 MB RAM choice.

**Free-form question:** What constitutes a passing QEMU smoke for the Shikshan ISO
under the 2 GB RAM ceiling?

## Out of scope

The following are explicitly excluded from this ADR and will be addressed in later
tasks:

- Desktop interaction (Phase-8, SMO-0090..SMO-0093)
- Persistence write/read (separate task)
- Installer flow / Calamares end-to-end (separate task)

## Decision Drivers

* Must work within the 2 GB RAM ceiling without masking regressions.
* Must run headless in CI without an in-guest agent or network setup.
* Must cover both BIOS and UEFI boot paths.
* Must give a deterministic pass/fail signal that CI can enforce as a required check.
* Must keep CI wall-clock cost predictable (target: ≤20 min per full BIOS+UEFI run).

## Considered Options

**Success detection:**

* Option A — Serial-regex on serial console stdout
* Option B — SSH probe into the live session
* Option C — virtio-console / qemu-guest-agent exit-status channel

**RAM size:**

* Option R1 — 1024 MB
* Option R2 — 2048 MB
* Option R3 — 4096 MB

**Inner success-marker deadline:**

* Option T1 — 300 s
* Option T2 — 540 s
* Option T3 — 900 s

## Decision Outcome

Chosen options: **Option A (serial-regex)**, **Option R2 (2048 MB)**, **Option T2
(540 s inner deadline)**.

The canonical invocation for each boot path is:

### BIOS

```bash
timeout 600 qemu-system-x86_64 \
  -m 2048 \
  -cdrom "$ISO" \
  -boot d \
  -nographic \
  -no-reboot \
  -serial mon:stdio \
  -display none \
  -device virtio-net-pci,netdev=n0 \
  -netdev user,id=n0 \
  2>&1 | tee "$LOG"
```

### UEFI

```bash
timeout 600 qemu-system-x86_64 \
  -m 2048 \
  -drive if=pflash,format=raw,readonly=on,file="$OVMF_CODE" \
  -drive if=pflash,format=raw,file="$VARS_TMP" \
  -cdrom "$ISO" \
  -boot d \
  -nographic \
  -no-reboot \
  -serial mon:stdio \
  -display none \
  -device virtio-net-pci,netdev=n0 \
  -netdev user,id=n0 \
  2>&1 | tee "$LOG"
```

`$VARS_TMP` is a per-run writable copy of `OVMF_VARS.fd` (created by `boot-uefi.sh`,
removed on `EXIT` via `trap`).

### Pass/fail criteria

| Parameter | Value |
|---|---|
| RAM | **2048 MB** |
| Outer hard kill | `timeout 600` (QEMU process) |
| Inner success-marker deadline | **540 s** from boot |
| Success regex (ERE) | `lightdm.*autologin\|shikshan.local login` |
| Exit 0 | marker found within deadline |
| Exit 2 | deadline exceeded |
| Exit 3 | QEMU exited before marker |

The 60-second gap between the 540 s inner deadline and the 600 s outer `timeout`
is intentional: it allows the script to kill the QEMU process and emit a
human-readable timeout message before the outer cap fires.

The `SUCCESS_RE` shell variable in each script is the single source of truth and
must match the literal regex above. Changing one without changing the other is a
contract violation.

### Consequences

* **Bad / accepted risk:** false-positive risk — any future serial-log line that
  incidentally matches `lightdm.*autologin` or `shikshan.local login` will trip the
  success marker. In practice the patterns are narrow enough (LightDM autologin
  emission and getty's hostname-prefixed prompt) that false positives are unlikely,
  but they are not impossible. Callers must treat a green smoke as a necessary, not
  sufficient, condition for release.
* **Bad / known gap:** no headless GUI probe — a passing smoke does NOT prove the
  LightDM session actually renders, that audio initialises, or that the GPU is
  accessible. Those checks are intentionally deferred to Phase-8 (SMO-0090..0093).
* **Bad / cost:** CI wall-clock cost — BIOS + UEFI together consume approximately
  20 CI minutes per run (each capped at 600 s QEMU + OVMF setup + log upload).
  This is documented so the deadline is recognised as a cost lever: tightening
  T2 below 540 s reduces CI cost but risks false-negatives on slow targets.
* **Good / upgrade path:** the `SUCCESS_RE` variable in each script is the sole
  change surface for future regex evolution. Deeper checks (X session, audio, GPU
  init) can be added as additional ERE alternations under a superseding ADR without
  touching the outer script structure.
* **Good / reproducibility:** the 2048 MB ceiling and 540 s deadline are now
  auditable constants; any regression that inflates boot time past 540 s on a
  2 GB VM will be caught before release.

### Confirmation

Compliance is confirmed by:

- `tests/qemu/boot-bios.sh` (exists) — canonical BIOS smoke; required-check name
  `e2e / qemu-bios`.
- `tests/qemu/boot-uefi.sh` (exists) — canonical UEFI smoke; required-check name
  `e2e / qemu-uefi`.
- `tests/qemu/run-smoke.sh` (to be added in **SMO-0308**) — wrapper that invokes
  both scripts sequentially and collects exit codes.
- `.github/workflows/ci-qemu-smoke.yml` (to be added in **SMO-0310**) — CI
  workflow that gates PRs on `e2e / qemu-bios` and `e2e / qemu-uefi`.

The `SUCCESS_RE` value in each script must match the literal regex in this ADR.
Divergence is a contract violation detectable by `tests/smoke/test_auto_config_flags.sh`
(to be added in SMO-0303).

## Pros and Cons of the Options

### Success detection

#### Option A — Serial-regex on serial console stdout (chosen)

* **Good**, because it requires zero in-guest packages or RAM overhead — the serial
  console is a QEMU built-in, enabled by `-nographic -serial mon:stdio`.
* **Good**, because it works identically under BIOS and UEFI without any per-path
  adaptation.
* **Bad**, because the regex is an approximate pattern; it is possible (though
  unlikely) for a different log line to match before the real login is ready.

#### Option B — SSH probe into the live session

* **Good**, because it gives a semantically stronger signal (an SSH session means
  the network stack and sshd are both functional).
* **Bad**, because it requires `openssh-server` in the live image, increasing image
  size and RAM usage — both constrained at 2 GB.
* **Bad**, because it adds a QEMU user-mode networking step, key material, and a
  host-side SSH client invocation, making the test setup more fragile.

#### Option C — virtio-console / qemu-guest-agent exit-status channel

* **Good**, because it provides a clean, programmatic exit signal from the guest.
* **Bad**, because it requires `qemu-guest-agent` installed in the live image —
  another package on the 2 GB budget.
* **Bad**, because it adds a host-side virtio socket probe, which is more complex
  than a serial-log grep and harder to debug when it fails.

### RAM size

#### Option R1 — 1024 MB

* **Bad**, because PLAN.md targets 2 GB devices; testing at 1 GB misrepresents the
  documented floor and allows regressions that would only appear at 2 GB to pass.

#### Option R2 — 2048 MB (chosen)

* **Good**, because it matches the PLAN.md "2GB RAM" target and AGENTS.md §13
  "2 GB RAM ceiling for the default profile" exactly.
* **Good**, because a failure at 2048 MB is directly actionable — it maps to a
  real device class.

#### Option R3 — 4096 MB

* **Bad**, because it is above the documented ceiling; regressions that only appear
  at 2 GB would silently pass.

### Deadline

#### Option T1 — 300 s

* **Bad**, because empirical cold-start time on a 2 GB VM — including live-boot
  initrd, LightDM startup, and potential snapshot-mirror download latency —
  regularly exceeds 300 s, producing false-negatives on legitimate builds.

#### Option T2 — 540 s (chosen)

* **Good**, because it covers the observed worst-case cold-start on slow CI runners
  with the snapshot.debian.org mirror cost factored in.
* **Good**, because the 60-second gap to the 600 s outer cap gives the script time
  to report a clean timeout message.
* **Neutral**, because it is a heuristic, not a formal bound; it may need revisiting
  if CI infrastructure changes significantly.

#### Option T3 — 900 s

* **Bad**, because it is too lax — a genuine boot-time regression of 5+ minutes
  would pass undetected until release.

## Supply-chain and audit implications

None — this ADR documents existing behaviour of existing test scripts. No upstream
pins, signing material, or audit-row format changes.

## Rollback plan

The success regex can be evolved under a semver-like rule without superseding this
ADR:

- **Tighten** (more restrictive — e.g., require both alternations to match): allowed
  only after one full release has passed with the existing regex green on both BIOS
  and UEFI.
- **Loosen** (more permissive — e.g., add a new alternation): requires a superseding
  ADR using this same template, with a new false-positive analysis in the
  Consequences section.

Full revert: write a superseding ADR with `status: superseded` set on ADR-0008 and
a forward link to the new ADR; restore `SUCCESS_RE` in `tests/qemu/boot-bios.sh`
and `tests/qemu/boot-uefi.sh` to their prior values; update `run-smoke.sh`
(SMO-0308) if the wrapper bakes in the regex.

## More Information

* Related ADRs:
  - ADR-0001 (Debian 13.5 + live-build — to be seeded; pre-allocated in
    `policies/protected-paths.yml`)
  - ADR-0007 (live-build config flags — pending SMO-0301; documents the `--apt-recommends false`
    and `LB_BOOTAPPEND_LIVE` values that appear on the serial console at boot)
* Related tasks: SMO-0303 (auto/config remediation + smoke flag test), SMO-0308
  (run-smoke.sh wrapper), SMO-0310 (CI QEMU workflow)
* Related scripts: `tests/qemu/boot-bios.sh`, `tests/qemu/boot-uefi.sh`,
  `tests/qemu/README.md`
* External references:
  - QEMU `-nographic` + `-serial mon:stdio`: https://www.qemu.org/docs/master/system/invocation.html
  - OVMF firmware (Debian): `apt show ovmf`
  - PLAN.md §Boot matrix (line 35)
  - AGENTS.md §13 (2 GB RAM ceiling)
