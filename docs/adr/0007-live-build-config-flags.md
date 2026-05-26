---
status: "proposed"
date: 2026-05-26
decision-makers: ["@shikshan/platform", "@shikshan/security"]
consulted: ["@shikshan/release-managers"]
informed: ["@shikshan/devex"]
---

# 0007 — Locked `lb config` flag set for the Phase-3 live-build ISO

## Context and Problem Statement

ADR-0001 (seed; live-build commitment, per `policies/protected-paths.yml`) commits Shikshan Mantra OS to Debian live-build as the ISO production toolchain, but does not enumerate the specific `lb config` invocation parameters. The declarative wrapper at `auto/config` has been authored without a paired architectural record explaining why each flag value was chosen, which makes auditing future changes (binary image type, persistence encryption, debian-installer disposition, kernel flavour selection, APT `Recommends` policy) impossible against a written baseline. Phase-3 needs a frozen, grep-able flag list so that the smoke test under SMO-0303 and the QEMU boot tests under SMO-0305 / SMO-0308 have something concrete to assert against.

Which `lb config` flag values are locked for the v1 Phase-3 ISO, and what is the rationale tying each value to a project decision driver (2 GB RAM target, snapshot reproducibility, UEFI+BIOS dual-boot surface, persistence-encryption default-on, hermetic builds)?

## Decision Drivers

* 2 GB RAM target — Recommends-by-default would blow the memory ceiling at first boot, so APT defaults must be tightened at image-build time.
* Snapshot reproducibility — the same `lb config` invocation must produce a byte-equivalent ISO when paired with a pinned snapshot mirror.
* UEFI + BIOS dual surface — single image must boot on legacy BIOS firmware and on UEFI without a separate build.
* Persistence-encryption default-on — when a user opts into persistence, the volume must be LUKS-encrypted, never plaintext.
* No-network builds — once configured, `lb build` must not reach out to anything other than the pinned snapshot mirror declared under `config/archives/`.
* Grep-ability for SMO-0303 smoke test — flag values must be expressible as literal strings that a shell-level assertion can match.

## Considered Options

For the three axes where there is a real choice, the alternatives are:

* `--apt-recommends`: `true` / `false` / per-task-list overrides
* `--debian-installer`: `none` / `live` / `true`
* `--binary-images`: `iso` / `iso-hybrid` / `hdd`

## Decision Outcome

Chosen options:

* `--apt-recommends false` — required by the 2 GB RAM ceiling; per-package opt-ins live in `config/package-lists/*.list.chroot`.
* `--debian-installer none` — Calamares is shipped in the live session and replaces d-i; carrying d-i too would bloat the ISO and split the install surface.
* `--binary-images iso-hybrid` — single artifact stickable to USB and burnable to DVD; satisfies the dual-boot surface driver with one output.

The full, locked Phase-3 flag set is:

* `--distribution trixie`  (Debian 13.5)
* `--architectures amd64`  (v1 is 64-bit only)
* `--bootloaders syslinux,grub-efi`  (BIOS + UEFI)
* `--binary-images iso-hybrid`  (USB-stickable + DVD bootable)
* `--debian-installer none`  (replaced by Calamares from the live session)
* `--initramfs live-boot`
* `--union-filesystem overlay`
* `--apt-recommends false`  (2 GB RAM ceiling)
* `--memtest none`
* `--linux-flavours amd64`, `--linux-packages linux-image-amd64`
* `--firmware-chroot true`  (non-free-firmware allowed for hardware support; gated by `debian.list.chroot`)
* `LB_PERSISTENCE=true` with `LB_PERSISTENCE_ENCRYPTION=luks`
* `LB_BOOTAPPEND_LIVE` includes `locales=en_IN.UTF-8 keyboard-layouts=us hostname=shikshan username=student`
* Mirror: snapshot.debian.org pin (delegated to `config/archives/debian.list.chroot` under `touches-signing`)

**Note on current divergence.** The canonical invocation lives in `auto/config`; current divergence (persistence flags missing from the `lb config` invocation, duplicate `LB_LINUX_FLAVOURS`, `deb.debian.org` placeholder mirror) is tracked under SMO-0303. This ADR records the *target* locked state; SMO-0303 closes the gap in the wrapper script.

### Consequences

* **Good**, because `--apt-recommends false` keeps first-boot RSS inside the 2 GB RAM ceiling and forces every Recommended package to be reviewed explicitly in `config/package-lists/`.
* **Good**, because pairing the locked flag set with the snapshot pin (delegated to ADR-0001 / `debian.list.chroot`) makes the ISO bit-for-bit reproducible from any clean build host.
* **Good**, because `--bootloaders syslinux,grub-efi` together with `--binary-images iso-hybrid` lets a single artifact cover both BIOS and UEFI machines — no separate ARM-style image to maintain.
* **Good**, because `LB_PERSISTENCE=true` with `LB_PERSISTENCE_ENCRYPTION=luks` makes encrypted persistence the only on-disk option; there is no plaintext fallback path.
* **Bad**, because `--debian-installer none` removes the conventional Debian installer fallback — if Calamares breaks in the live session, the only install path is gone until Calamares is repaired.
* **Neutral**, because `--firmware-chroot true` admits non-free-firmware into the chroot for hardware coverage; this is gated by `config/archives/debian.list.chroot` and surfaces in the SBOM rather than being silent.

### Confirmation

Compliance with this ADR will be confirmed by:

* `tests/smoke/test_auto_config_flags.sh` — added in SMO-0303 — greps `auto/config` for each locked flag value and fails the build if any line drifts.
* `tests/qemu/boot-bios.sh` and `tests/qemu/boot-uefi.sh` — added in SMO-0305 and SMO-0308 — boot the produced ISO under both firmware surfaces in QEMU and assert that the live session reaches the Calamares chooser.

## Pros and Cons of the Options

### `--apt-recommends`

* `true` — **Good**, because users get the upstream-recommended package experience by default. **Bad**, because Recommends typically pull in fonts, language packs, and helper daemons that push the live image well past 2 GB RSS at first boot.
* `false` (chosen) — **Good**, because every Recommended package becomes an explicit opt-in in `config/package-lists/`, which is auditable. **Bad**, because the maintainer of each package list has to know which Recommends are actually wanted.
* per-task-list — **Good**, because lists could selectively opt in. **Bad**, because live-build does not natively support per-list Recommends scoping; implementing it would require a custom hook and a new policy surface.

### `--debian-installer`

* `none` (chosen) — **Good**, because Calamares already covers the install path; dropping d-i shrinks the ISO and removes a parallel maintenance surface. **Bad**, because there is no fallback installer if Calamares regresses.
* `live` — **Good**, because it ships d-i alongside Calamares. **Bad**, because two installers in one image means two test surfaces and user confusion.
* `true` — **Good**, because it ships the standard d-i. **Bad**, because Calamares would then be redundant and the project goal of a friendlier live-session install would be defeated.

### `--binary-images`

* `iso` — **Good**, because pure ISO-9660 is the most portable format. **Bad**, because it cannot be `dd`'d to a USB stick reliably without a separate hybrid step.
* `iso-hybrid` (chosen) — **Good**, because the same file boots from DVD and from a USB stick written with `dd`. **Bad**, because the hybrid layout adds a partition-table header that some legacy burning tools warn about.
* `hdd` — **Good**, because it is the canonical USB image format. **Bad**, because it cannot be burned to optical media, which the schools in scope still rely on.

## Supply-chain and audit implications

The snapshot mirror pin (`snapshot.debian.org` timestamp) is *not* settled by this ADR. It is delegated to ADR-0001 + `config/archives/debian.list.chroot`, both of which carry the `touches-signing` label and require the two-team review path in `policies/protected-paths.yml`. This ADR does not change `scripts/audit/append-entry.py`, the audit-row schema, the audit chain, or any signing material — the audit chain query at `scripts/audit/verify-chain.py` is unaffected.

## Rollback plan

If a locked flag value proves wrong in practice, revert by:

1. Edit `auto/config` to restore the previous flag value(s). `auto/**` carries the `touches-bootloader` label and requires the `allowlist-override` PR path with two-team review (platform + security).
2. Write a superseding ADR (`status: superseded, supersedes: 0007`) that documents the new locked set and the rationale for the change.
3. Update `tests/smoke/test_auto_config_flags.sh` (SMO-0303) to match the new locked values; the test must remain green on the same commit.

## More Information

* Related ADRs:
  * ADR-0001 (seed; live-build commitment) — referenced via `policies/protected-paths.yml`.
  * [ADR-0003 — Vendor strategy](0003-vendor-strategy.md).
  * [ADR-0006 — Release artifact bundle layout](0006-release-artifact-layout.md).
* Related tasks:
  * SMO-0303 — reconcile `auto/config` with this locked flag set and land the smoke test.
  * SMO-0304 — package-list refresh aligned with `--apt-recommends false`.
  * SMO-0305 — QEMU BIOS boot test.
  * SMO-0308 — QEMU UEFI boot test.
* Out of scope:
  * Mirror URL pin — delegated to ADR-0001 + `config/archives/debian.list.chroot` under the `touches-signing` label.
* External references:
  * https://live-team.pages.debian.net/live-manual/html/live-manual/examples.en.html
  * https://manpages.debian.org/bookworm/live-build/lb_config.1.en.html
  * https://manpages.debian.org/bookworm/live-build/live-build.7.en.html
