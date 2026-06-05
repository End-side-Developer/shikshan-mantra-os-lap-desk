---
status: "accepted"
date: 2026-06-05
decision-makers: ["@shikshan/platform"]
consulted: []
informed: ["@shikshan/content", "@shikshan/security"]
---

# 0019 — Vidyarthi code engine runtime: Python 3 stdlib, stdin/stdout grading, per-test timeout

## Context and Problem Statement

The Vidyarthi batch (SMO-0500..0617) ships SQL as the only sub-engine. The
exercise schema skeleton for `sub_engine=code`
([`modules/catalogs/schemas/exercises/code.schema.json`](../../modules/catalogs/schemas/exercises/code.schema.json),
SMO-0513) is already committed but the engine itself — the subprocess that
executes Python submissions and grades them — has never been implemented.

ADR-0011 locks the IPC: every engine is a subprocess speaking JSON-RPC 2.0
over stdio. ADR-0015 locks the sandbox: every engine runs inside a bubblewrap
namespace with a seccomp allowlist. This ADR fills in what is specific to the
**code** engine: what the learner's code executes in, how grading works, what
the timeout and resource-limit contract is, and what language extensions are
explicitly out of scope.

## Decision Drivers

* Must be testable on the Windows maintainer workstation with only `python3`
  (no GTK, no bwrap, no ISO) — same constraint as ADR-0018.
* Must honour the 2 GB RAM target: no daemon, no interpreter pool, minimal
  per-run overhead.
* Must block all network from inside the code sandbox.
* Must accept a per-exercise configurable wall-clock timeout
  (`max_execution_ms` in the exercise YAML, per `code.schema.json`).
* Phase-3 scope is Python only; the engine must not pretend to be more general
  than it is.

## Considered Options

* **A** — Call `exec(code_string)` inside the engine process, capture `sys.stdout`.
* **B** — Write submission to a temp file; spawn a **child `python3` subprocess**
  inside the sandbox; feed each test_case input on stdin; compare stdout to
  expected_output (strip-exact match).
* **C** — Compile to a `.pyc` in memory; run inside a `RestrictedPython` environment.

## Decision Outcome

Chosen option: **"B — child python3 subprocess per test_case"**, because it
gives true process isolation between the engine (JSON-RPC host) and the
learner's code, makes timeout enforcement trivial (`subprocess.run(timeout=…)`),
and keeps the engine code pure stdlib with no third-party sandboxing library
needed.

### Grading contract

For each `grade` RPC received by the code engine:

1. Write `params.submission.code` to a `NamedTemporaryFile` in `/tmp`
   (always deleted in a `finally` block).
2. For each `test_case` in the loaded exercise's `test_cases` array:
   * Call `subprocess.run([sys.executable, tmp_file], input=test_case.input,
     capture_output=True, text=True, timeout=max_execution_ms/1000)`.
   * Compare `proc.stdout.strip()` to `test_case.expected_output.strip()`
     (exact match after whitespace strip on both sides).
3. If **all** test_cases pass: `{score: 1, success: true, feedback: PASS_FEEDBACK}`.
4. If **any** test_case fails: `{score: 0, success: false, feedback: FAIL_FEEDBACK}`.
   Feedback includes the first failing test_case's expected vs actual (visible
   test_cases only; hidden test_cases report failure without exposing
   expected_output).
5. On `subprocess.TimeoutExpired`: return JSON-RPC error **`-32003`** with
   `message: "execution timeout"`. The temp file is still cleaned up.
6. On Python `SyntaxError` (detected at compile time before spawning):
   return `{score: 0, success: false}` with `feedback.en` containing the
   literal string `"SyntaxError"` so tests can assert on it.

### Methods

| Method | Behaviour |
|---|---|
| `init` | Return `{engine_id: "code", capabilities: ["grade"]}` |
| `load_exercise` | Load exercise YAML from the module bundle; hold in memory |
| `grade` | Execute per grading contract above |
| `run` | **Not supported.** Return JSON-RPC error `-32601` (method not found) |
| `shutdown` | Write `{result: "ok"}` to stdout; exit 0 |

### Language and runtime constraints (locked for Phase-3)

* **Python 3 only.** `code.schema.json` enforces `"language": {"enum": ["python"]}`.
  No JavaScript, Go, Java, or multi-language dispatch in this engine.
* **Stdlib only.** The engine subprocess imports nothing beyond the Python
  standard library. No PyPI packages are installed in the sandbox path; the
  seccomp profile denies `socket`/`connect` so network imports would fail even
  if attempted.
* **Single-file submission.** The learner submits a single code string
  (`submission.code`); multi-file projects are out of scope.
* **No persistent state.** Each grade call spawns a fresh child process; no
  state leaks between test_case runs or between learners.

### Timeout and resource limits

| Limit | Value | Source |
|---|---|---|
| Per-test wall timeout | `max_execution_ms` ÷ 1000 s | exercise YAML (100..30000 ms, per schema) |
| Default timeout if absent | 10 s | `code.schema.json` default |
| Address space (AS) | 256 MB | `prlimit` via bwrap wrapper (comment in `sandbox.bwrap`) |
| Max processes (NPROC) | 8 | `prlimit` via bwrap wrapper |
| CPU time | 20 s | `prlimit` via bwrap wrapper (hard ceiling above any per-test timeout) |

`prlimit` values are documented in `engines/code/sandbox.bwrap` as comments;
they are applied by the EngineClient's bwrap invocation on Linux.

### Sandbox composition

The code engine reuses ADR-0015's pattern unchanged:

* `engines/code/sandbox.bwrap` — bubblewrap flag file (`--unshare-net`,
  `--unshare-pid`, `--unshare-ipc`, `--unshare-uts`, `--tmpfs /tmp`,
  read-only bind of the engine bundle).
* `engines/code/seccomp.json` — `libseccomp` allowlist that adds `execve`,
  `fork`, `clone` (needed for `python3` interpreter startup) to the base SQL
  allowlist, and explicitly denies `socket`, `connect`, `bind`. Default action
  is `SCMP_ACT_ERRNO(EACCES)` (not `KILL`) to allow graceful Python error
  handling on a blocked syscall.
* EngineClient applies bwrap + seccomp **on Linux only** when
  `VIDYARTHI_SANDBOX=auto` (or environment default). On Windows the engine is
  direct-spawned (no bwrap), which allows dev/test iteration without a Linux
  environment.

### Bilingual feedback requirement

All engine-originated feedback dicts **must** have both `en` and `hi` keys.
The engine ships two hardcoded locale dicts (`PASS_FEEDBACK`, `FAIL_FEEDBACK`,
`TIMEOUT_FEEDBACK`) with English and Hindi strings. Content-rich per-test
feedback (failing test details) is appended to the `en` string only; `hi`
carries the generic pass/fail message. This mirrors the pattern in
`engines/sql/main.py`.

### Consequences

* **Good** — the child-subprocess model gives real process isolation; a
  fork-bomb or memory-exhausting submission cannot reach the engine's JSON-RPC
  loop.
* **Good** — timeout is enforced at the Python `subprocess` level, not a
  custom alarm; reliable across platforms.
* **Good** — pure stdlib: no PyPI dependency, no `pip install` step in the ISO
  hook, no supply-chain exposure.
* **Bad** — one `python3` startup (~30–80 ms) per test_case per grade call.
  Acceptable for interactive practice (exercises have 1–5 test_cases);
  unacceptable for batch grading (out of scope).
* **Neutral** — each engine limits Phase-3 to one language; adding JavaScript
  later requires a new `engines/js/` tree with its own ADR.

### Confirmation

Compliance is verified by:

* `tests/engines/test_code_engine.py` (SMO-0806) — JSON-RPC lifecycle:
  init → load_exercise → grade (correct, wrong, syntax error, timeout) → shutdown.
* `tests/e2e/test_vidyarthi_python_mvp.sh` (SMO-0807) — boots ISO, drives
  Vidyarthi desktop, submits hello-world, asserts xAPI row in `learner.db`.
* `python scripts/audit/verify-chain.py --db docs/audit/audit.db` — chain
  intact after all SMO-0800..0808 tasks merge.

## More Information

* Related ADRs: [0011](0011-engine-ipc.md) (IPC framing), [0015](0015-sandbox-primitive.md)
  (bubblewrap + seccomp), [0018](0018-vidyarthi-desktop-app.md) (GTK-free core pattern).
* Related schema: [`modules/catalogs/schemas/exercises/code.schema.json`](../../modules/catalogs/schemas/exercises/code.schema.json).
* Related tasks: SMO-0801 (engine implementation), SMO-0802 (sandbox profiles),
  SMO-0803 (python-basics module), SMO-0806 (tests), SMO-0807 (E2E).
* MADR 3.x — https://adr.github.io/madr/
