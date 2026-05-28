---
status: "proposed"
date: 2026-05-28
decision-makers: ["@shikshan/platform"]
consulted: []
informed: ["@shikshan/platform"]
---

# 0011 — Vidyarthi engine IPC: subprocess + JSON-RPC over stdio

## Context and Problem Statement

Vidyarthi is the new interactive practice-engine app for Shikshan Mantra OS
(working name; see [PLAN.md](../../PLAN.md) and the `project_vidyarthi_initiative`
memory entry). Each `content_type` it hosts — SQL, web, code, CTF, quiz — needs
to execute student submissions and return graded results. The frontend
(PyGObject/GTK4, decided in ADR-0012) must talk to a per-exercise *engine*
without sharing process memory, because some engines (CTF labs, code runners)
will eventually execute untrusted student input. This ADR locks the IPC
mechanism: how does the frontend frame messages to engines and back, what is
the engine's lifetime, and which streams carry which data?

## Decision Drivers

* Must support per-call sandboxing (bubblewrap + seccomp; ADR-0015 follow-up).
* Must fit the 2 GB RAM target — no extra long-lived daemons.
* Must remain debuggable from a Python REPL or shell pipe.
* Must crash-isolate the frontend from a runaway engine.
* Must not require new system services or D-Bus interface XML.

## Considered Options

* Subprocess per exercise attempt, JSON-RPC 2.0 framed over the child's
  stdin/stdout (newline-delimited).
* A long-lived D-Bus session daemon (`org.shikshan.Vidyarthi.Engine1`) with
  one method per RPC.
* In-process Python plugins loaded into the GTK frontend via `importlib`.
* HTTP/JSON over a loopback Unix socket or 127.0.0.1 port.
* Unix domain socket with a custom length-prefixed framing.

## Decision Outcome

Chosen option: **"Subprocess per exercise attempt, JSON-RPC 2.0 over stdio
(newline-delimited)"**, because it gives free crash isolation, trivially
composes with bubblewrap (the frontend just spawns `bwrap … engine-binary`),
adds no long-lived daemon, and is the simplest thing that can carry the methods
defined below.

### Engine RPC methods (locked surface)

* `init(engine_id, exercise_spec) -> capabilities`
* `load_exercise(exercise_id) -> ack | error`
* `run(submission) -> result`
* `grade(submission) -> {score, success, feedback}`
* `shutdown() -> ack`

Detailed semantics, error codes, and notification shapes are spec'd in
`docs/architecture/vidyarthi-engine-rpc.md` (SMO-0530).

### Framing and stream conventions

* **Framing:** JSON-RPC 2.0 (https://www.jsonrpc.org/specification), one
  object per line (newline-delimited). No `Content-Length` headers, no
  multipart. Each `\n`-terminated UTF-8 line is exactly one JSON-RPC
  request, response, or notification.
* **stdin:** frontend → engine. Requests and notifications only.
* **stdout:** engine → frontend. Responses and engine-originated
  notifications only. Engines MUST NOT print free-form text on stdout.
* **stderr:** engine → frontend, free-form diagnostics. The frontend
  captures stderr to `~/.local/share/shikshan/vidyarthi/engine-<pid>.log`
  for the user-visible debug pane.

### Subprocess lifetime

Lifetime is **one process per exercise attempt**. The frontend spawns a
fresh engine subprocess on each `load_exercise` from the catalog UI;
on `shutdown` (or any non-zero exit, or stdin EOF) it reaps the process
and frees its resources. The frontend respawns for the next exercise.
There is no engine pool, no warm-start, no shared state across exercises.

### Consequences

* **Good**, because each exercise attempt has its own address space and
  sandbox boundary — ADR-0015 can layer `bwrap --ro-bind` + seccomp on
  top with no IPC changes.
* **Good**, because a crashed engine cannot corrupt the frontend or
  other exercises; the GTK process keeps running and surfaces the engine
  exit code in the UI.
* **Good**, because stdio is the most debuggable IPC primitive on Linux:
  a maintainer can pipe `echo '{"jsonrpc":"2.0","method":"grade",...}'`
  into the engine binary and read the response, no D-Bus introspection
  needed.
* **Good**, because no long-lived daemon — fits the 2 GB RAM target;
  idle engines consume zero memory.
* **Bad**, because we pay subprocess fork/exec cost on every exercise
  load (~30–80 ms on the 2 GB target). Acceptable for interactive
  practice; not acceptable for high-frequency batch grading (out of
  scope for Vidyarthi v1).
* **Neutral**, because notifications and progress events fit naturally
  into JSON-RPC's notification frame but the frontend must implement a
  reader loop rather than handler callbacks.

### Confirmation

Compliance is verified by:

* `tests/engines/test_sql_engine.py` (filed in SMO-0560) — spawns the
  SQL engine subprocess, sends 100 grade RPCs with fixed input, asserts
  deterministic JSON output and a single-line-per-message wire shape.
* `tests/e2e/test_vidyarthi_sql_mvp.sh` (filed in SMO-0590) — end-to-end
  ISO boot → launcher → engine spawn → grade → engine exit, asserting
  the process is reaped and stderr is captured to the log path above.

## Pros and Cons of the Options

### Subprocess + JSON-RPC stdio

* **Good**, because trivial bwrap composition.
* **Good**, because crash isolation is free.
* **Bad**, because fork/exec cost per exercise.

### D-Bus session daemon

* **Good**, because rich introspection, well-known on Linux desktop.
* **Bad**, because heavyweight on 2 GB target; activation is brittle on
  live sessions; per-call sandboxing requires extra plumbing.
* **Bad**, because adds a system-service contract we'd have to govern.

### In-process Python plugins

* **Good**, because zero IPC cost.
* **Bad**, because no isolation — a crash in a code engine kills the
  GTK frontend; sandbox boundary is impossible.

### HTTP/JSON over loopback

* **Good**, because reuses familiar tooling.
* **Bad**, because port allocation, extra serialization, no natural
  lifetime tie between client and server.

### Unix socket + custom framing

* **Good**, because more efficient than stdio.
* **Bad**, because more code than stdio for no isolation gain over
  the chosen option.

## Supply-chain and audit implications

None — no change to upstream pins, signing material, or audit-row format.
Engine binaries ship in the `shikshan-engines-core` Debian package
(stub filed in SMO-0540) and are signed as part of the normal apt
metadata chain.

## Rollback plan

If this decision proves wrong (e.g., fork/exec latency on real 2 GB
hardware turns out to be unusable in practice), supersede ADR-0011 with
a new ADR specifying the replacement (most likely a long-lived engine
process with a per-exercise reset RPC, or a D-Bus daemon if multi-app
sharing becomes a requirement). The replacement ADR must also revisit
ADR-0012 (frontend stack assumes synchronous JSON-RPC reader loop) and
ADR-0015 (sandbox primitive composes with subprocess lifetime). Revert
sequence: open superseding ADR, update SMO-0530 spec, regenerate engine
implementations, update tests in SMO-0560/0590.

## More Information

* Related ADRs: 0012 (frontend stack), 0014 (xAPI telemetry), 0015
  (sandbox primitive)
* Related tasks: SMO-0510 (schema content-type wiring), SMO-0530
  (engine RPC spec), SMO-0560 (SQL engine MVP), SMO-0570 (sandbox
  profile), SMO-0590 (end-to-end test)
* External references:
  * JSON-RPC 2.0 — https://www.jsonrpc.org/specification
  * `bwrap(1)` — https://manpages.debian.org/bookworm/bubblewrap/bwrap.1.en.html
