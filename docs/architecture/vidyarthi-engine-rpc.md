# Vidyarthi Engine RPC Protocol

**Version:** 1.0.0 · **Status:** Normative · **Governs:** ADR-0011 · **Filed:** SMO-0530

---

## Overview

Each Vidyarthi practice engine runs as a short-lived child process.
The GTK frontend communicates with it over the child's stdin/stdout
using **JSON-RPC 2.0** with newline-delimited framing.

```text
Frontend → stdin  → Engine   (requests + client notifications)
Frontend ← stdout ← Engine   (responses + server notifications)
Frontend ← stderr ← Engine   (free-form diagnostics, captured to log)
```

One newline-terminated UTF-8 line = one JSON-RPC object.
Engines MUST NOT write free-form text to stdout.

---

## Subprocess lifecycle

```text
Frontend                       Engine
  │                              │
  ├─ exec bwrap … engine-binary ─┤
  │                              │
  ├──── init() ─────────────────►│  (first message; must complete before others)
  │◄─── result ─────────────────┤
  │                              │
  ├──── load_exercise() ────────►│
  │◄─── result ─────────────────┤
  │                              │
  ├──── run() ──────────────────►│  (zero or more)
  │◄─── result / notifications ─┤
  │                              │
  ├──── grade() ────────────────►│
  │◄─── result ─────────────────┤
  │                              │
  ├──── shutdown() ─────────────►│
  │◄─── result ─────────────────┤
  │                              │
  │         (process exits 0) ───┘
```

The frontend MUST call `init` before any other method.
The engine MUST exit with code 0 after responding to `shutdown`.
If the frontend sends EOF on stdin, the engine MUST treat it as `shutdown`.
The `--die-with-parent` bwrap flag ensures cleanup if the frontend crashes.

---

## Message framing

Every message is a single line of UTF-8 JSON followed by `\n`.

**Request:**

```json
{"jsonrpc": "2.0", "id": 1, "method": "grade", "params": {"submission": "SELECT * FROM employees"}}
```

**Response (success):**

```json
{"jsonrpc": "2.0", "id": 1, "result": {"score": 100, "success": true, "feedback": []}}
```

**Response (error):**

```json
{"jsonrpc": "2.0", "id": 1, "error": {"code": -32001, "message": "timeout", "data": {"elapsed_ms": 5012}}}
```

**Server notification** (no `id`; frontend must not reply):

```json
{"jsonrpc": "2.0", "method": "progress", "params": {"pct": 42, "message": "running assertion 3/7"}}
```

---

## Methods

### `init`

Initialise the engine for one exercise attempt.

**Request params:**

| Field | Type | Required | Description |
|---|---|---|---|
| `engine_id` | string | yes | Engine identifier (e.g. `"sql"`) |
| `exercise_spec` | object | yes | Parsed exercise YAML content (sub-engine-specific schema) |
| `bundle_path` | string | yes | Absolute path to the module bundle directory (inside the sandbox this is `/module`) |
| `locale` | string | yes | `"en"` or `"hi"` |
| `policy` | object | no | Subset of policy.yml relevant to this engine (e.g. `allowed_sub_engines`) |

**Result:**

| Field | Type | Description |
|---|---|---|
| `ok` | boolean | `true` on success |
| `engine_version` | string | SemVer of the engine binary |
| `capabilities` | array of string | Supported method names beyond the base set |

**Errors:** `-32600` (invalid params), `-32001` (engine initialisation failed).

---

### `load_exercise`

Load a specific exercise from the already-initialised bundle.

**Request params:**

| Field | Type | Required | Description |
|---|---|---|---|
| `exercise_id` | string | yes | Exercise `id` from the bundle's exercises list |

**Result:**

| Field | Type | Description |
|---|---|---|
| `prompt` | object | `{"en": "...", "hi": "..."}` |
| `starter` | string | Pre-filled editor content |
| `metadata` | object | Engine-specific display metadata (e.g. fixture table names for SQL) |

---

### `run`

Execute the learner's submission without grading. Used for "run" button
before the learner submits.

**Request params:**

| Field | Type | Required | Description |
|---|---|---|---|
| `submission` | string | yes | Learner input (SQL string, code string, HTML string, etc.) |

**Result:**

| Field | Type | Description |
|---|---|---|
| `output` | string | Raw output (query result table, stdout, rendered HTML snippet, …) |
| `diagnostics` | array | Array of `{level, message}` objects. `level` is one of `error`, `warning`, `info`. |
| `elapsed_ms` | integer | Execution time inside the sandbox |

**Server notifications:** `progress` (optional, for long-running executions).

---

### `grade`

Execute the submission and apply all grading assertions.

**Request params:** same as `run`.

**Result:**

| Field | Type | Description |
|---|---|---|
| `score` | integer | 0–100 |
| `success` | boolean | `score >= rubric.pass_threshold` |
| `feedback` | array | Per-assertion feedback objects `{"assertion_index": N, "passed": bool, "message": {"en": "...", "hi": "..."}}` |
| `hints_unlocked` | integer | Number of hints the learner may now see |
| `xapi_statements` | array | xAPI statement objects (see `vidyarthi-xapi-subset.md`) |

---

### `shutdown`

Graceful shutdown. Engine must flush any pending writes, then exit 0.

**Request params:** none.

**Result:**

| Field | Type | Description |
|---|---|---|
| `ok` | boolean | Always `true` |

---

## Error codes

| Code | Meaning |
|---|---|
| `-32700` | Parse error (malformed JSON) |
| `-32600` | Invalid request (missing required field) |
| `-32601` | Method not found |
| `-32001` | Engine init failed |
| `-32002` | Exercise not found in bundle |
| `-32003` | Execution timeout |
| `-32004` | Sandbox violation (syscall blocked by seccomp) |
| `-32005` | Fixture load error |

---

## Versioning

The protocol version is the engine binary's SemVer returned in `init.result.engine_version`.
The frontend MUST accept any engine with a compatible major version.
Breaking changes require a major version bump and a new ADR superseding ADR-0011.

---

## Related

- [ADR-0011](../adr/0011-engine-ipc.md) — IPC mechanism decision
- [ADR-0015](../adr/0015-sandbox-primitive.md) — bwrap + seccomp wrapping
- [vidyarthi-xapi-subset.md](vidyarthi-xapi-subset.md) — telemetry shape
- `modules/catalogs/schemas/exercises/` — per-engine exercise specs
