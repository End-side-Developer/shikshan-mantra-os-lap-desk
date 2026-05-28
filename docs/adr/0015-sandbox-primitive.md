---
status: "proposed"
date: 2026-05-28
decision-makers: ["@shikshan/platform"]
consulted: []
informed: ["@shikshan/platform"]
---

# 0015 — Vidyarthi sandbox primitive: bubblewrap + seccomp

## Context and Problem Statement

Each Vidyarthi engine subprocess (ADR-0011) executes learner-submitted
code or queries. On a 2 GB RAM laptop used by students, a misconfigured
query or a deliberately malicious script must not be able to read
other users' home directories, write outside the module bundle, open
network connections, or fork-bomb the host. We need to pick a single
Linux sandbox primitive that wraps every engine subprocess, is
available in Debian main, and does not require setuid root. The
sandbox is the final safety layer — it complements the application-level
limits already present in each engine (query timeouts, output truncation).

## Decision Drivers

* Must not require setuid root on the live system
  (child-safe deployment, no escalation surface).
* Must be available in Debian main (snapshot.debian.org pin, ADR-0007).
* Must compose naturally with subprocess + stdin/stdout IPC (ADR-0011)
  — the launcher wraps `bwrap … engine-binary` transparently.
* Must support read-only bind-mount of the module bundle directory.
* Must support seccomp allowlist to restrict the syscall surface.
* Must block network by default (no-new-network-namespace or
  `--unshare-net`).

## Considered Options

* **bubblewrap (`bwrap`)** — the Flatpak sandbox primitive; in Debian
  main as `bubblewrap`.
* **firejail** — in Debian main; designed for application confinement.
* **nsjail** — Google's namespace + seccomp sandbox; not in Debian main.
* **systemd-nspawn** — in Debian main; full container-style isolation.

## Decision Outcome

Chosen option: **"bubblewrap (`bwrap`) + seccomp allowlist"**, because
it is the Linux desktop sandboxing primitive already used by Flatpak,
has no setuid root, composes trivially with subprocess exec (it is a
plain exec wrapper), and its seccomp filter format is standard
(`libseccomp` JSON).

### Sandbox invocation pattern

The launcher spawns every engine as:

```sh
bwrap \
  --ro-bind /usr/share/shikshan/modules/<module-id> /module \
  --ro-bind /usr/share/shikshan/vidyarthi/engines/<sub_engine> /engine \
  --tmpfs /tmp \
  --proc /proc \
  --dev /dev \
  --unshare-net \
  --unshare-pid \
  --unshare-ipc \
  --unshare-uts \
  --die-with-parent \
  --seccomp 7 \
  /engine/main.py
```

where fd 7 carries the seccomp BPF bytecode compiled at launcher
startup from `engines/<sub_engine>/seccomp.json` using `libseccomp`.

The engine process sees:

* `/module` — the module bundle directory, read-only.
* `/engine` — the engine binary tree, read-only.
* `/tmp` — a private tmpfs for scratch.
* No home directory, no `/var`, no `/etc` (except what is explicitly
  bind-mounted by future per-engine needs declared in the task
  contract).
* No network namespace.
* No ability to create child processes beyond what is whitelisted in
  the seccomp profile.

### Seccomp allowlist strategy

Each engine ships a `seccomp.json` (a `libseccomp` syscall allowlist)
in its engine tree. The base SQL engine allowlist permits: `read`,
`write`, `close`, `fstat`, `lseek`, `mmap`, `mprotect`, `munmap`,
`brk`, `exit_group`, `futex`, `clock_gettime`, `getpid`, `gettid`,
`getrandom`, `rt_sigprocmask`, `rt_sigreturn`, `sigaltstack`. All
other syscalls return `EPERM`. The full allowlist for SMO-0570
(SQL engine sandbox) is defined there; other engine tasks extend
from this base.

### Consequences

* **Good**, because `bwrap` has no setuid binary and no persistent
  daemon — it is pure Linux namespaces + `execvp`. A bug in the
  sandbox cannot gain root.
* **Good**, because the invocation pattern is a transparent exec
  wrapper; the launcher does not change how it communicates with the
  engine (stdin/stdout JSON-RPC, ADR-0011) — it only changes how it
  spawns the process.
* **Good**, because `--die-with-parent` ensures orphan cleanup even
  if the launcher is killed via `SIGKILL`.
* **Good**, because the module bundle is bind-mounted read-only; the
  engine cannot modify lesson content.
* **Neutral**, because seccomp profiles must be maintained per engine
  type; adding a new engine requires a new `seccomp.json`. This is
  the desired friction — it forces explicit review of each engine's
  syscall needs.
* **Bad**, because `bwrap` does not provide a user-namespace overlay
  in all Debian trixie kernel configurations. If the kernel has
  `user.max_user_namespaces = 0`, bwrap fails. Mitigation: the
  `shikshan-vidyarthi` postinst script checks and logs a warning;
  in the live ISO the kernel config is under our control (ADR-0007).

### Confirmation

Compliance is verified by:

* `tests/engines/test_sql_sandbox_escape.sh` (SMO-0570) — attempts
  file write outside `/module`, network connection, and fork-bomb
  from inside the bwrap sandbox; all three must fail with non-zero
  exit or EPERM.
* `tests/build/test_vidyarthi_skeleton.sh` (SMO-0550) — asserts
  `bwrap` is installed and executable on the test system.

## Pros and Cons of the Options

### bubblewrap + seccomp

* **Good**, because no setuid, Flatpak-proven, transparent exec wrapper.
* **Good**, because `--die-with-parent` gives reliable cleanup.
* **Bad**, because user namespace availability depends on kernel config.

### firejail

* **Good**, because high-level profile language, rich Debian ecosystem.
* **Bad**, because firejail requires a **setuid root** binary
  (`/usr/bin/firejail`). On a child-targeted OS this creates a
  privileged-code surface that must be audited on every Debian update.
* **Bad**, because firejail's profile language is line-noise compared
  to explicit bwrap flags; it is harder to audit in a task contract.

### nsjail

* **Good**, because very fine-grained, well documented, production-
  proven at Google.
* **Bad**, because it is **not in Debian main**; pulling it in would
  require a vendor pin or a new apt source — both violate ADR-0007's
  reproducible-from-snapshot-debian-org requirement.

### systemd-nspawn

* **Good**, because full container isolation, well integrated with
  Debian.
* **Bad**, because designed for full OS containers, not single-process
  sandboxes; startup cost and resource usage are much higher than bwrap
  for a process that lives ~30 seconds.
* **Bad**, because requires root or the `systemd-container` capability
  — exactly what we are trying to avoid.

## Supply-chain and audit implications

`bubblewrap` ships in Debian main (`bubblewrap`, version ≥ 0.4.1 for
`--seccomp` fd support). `libseccomp` (`python3-seccomp`) is also in
Debian main and is used to compile the per-engine `seccomp.json`
allowlists at package install time. No new apt sources. No setuid
binaries introduced.

## Rollback plan

If bubblewrap proves insufficient (e.g., a kernel CVE bypasses the
namespace isolation, or user-namespace availability breaks on a new
hardware target), supersede ADR-0015 with a replacement ADR. Most
likely replacement is nsjail (if it enters Debian main) or a Flatpak
runtime wrapper that provides stronger isolation. Revert steps: update
the launcher's spawn path in `src/engine_host.py`, replace all
`seccomp.json` profiles with the new format, update SMO-0570 and all
engine tests.

## More Information

* Related ADRs: 0011 (engine subprocess lifetime), 0012 (frontend
  spawns the bwrap-wrapped subprocess)
* Related tasks: SMO-0570 (SQL engine bwrap profile + seccomp allowlist),
  SMO-0560 (SQL engine MVP)
* External references:
  * bubblewrap — https://github.com/containers/bubblewrap
  * libseccomp — https://github.com/seccomp/libseccomp
  * bwrap(1) — https://manpages.debian.org/bookworm/bubblewrap/bwrap.1.en.html
