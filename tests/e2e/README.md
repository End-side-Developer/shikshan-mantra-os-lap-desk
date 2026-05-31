# tests/e2e — Vidyarthi v1.0 end-to-end integration tests

## What `test_vidyarthi_sql_mvp.sh` asserts

The v1.0 milestone gate. Fails the build if any non-skipped stage fails.

| Stage | What it checks | Tasks |
|------:|----------------|-------|
| 1 | ISO artifact present in `releases/` | SMO-0500 |
| 2 | ISO boots to login prompt under QEMU (-enable-kvm, 2 GB RAM) | SMO-0550 |
| 3 | `src/main.py` compiles; `AdwApplicationWindow` in `window.blp` | SMO-0550 |
| 4 | sql-basics `manifest.yml` title "SQL Basics"; `01-select.yml` exists | SMO-0510 |
| 5 | SQL engine spawns inside `bwrap` user namespace (uid_map non-empty) | SMO-0570 |
| 6 | `grade("SELECT * FROM employees;")` → `score > 0`, `success = true` | SMO-0560 |
| 7 | xAPI `scored` statement present in `learner.db` after grade | SMO-0503/0531 |
| 8 | `scripts/audit/verify-chain.py` exits 0 | SMO-0503 |

Architecture references:
[vidyarthi-engine-rpc.md](../docs/architecture/vidyarthi-engine-rpc.md) ·
[vidyarthi-xapi-subset.md](../docs/architecture/vidyarthi-xapi-subset.md)

## Host prerequisites

| Tool | Debian package | Stages |
|------|----------------|--------|
| `qemu-system-x86_64` | `qemu-system-x86` | 2 |
| `/dev/kvm` | kernel kvm module | 2 |
| `python3`, `pyyaml` | `python3-yaml` | 3, 6, 7, 8 |
| `bwrap` | `bubblewrap` | 5, 6, 7 |
| `sqlite3` (CLI) | `sqlite3` | 7 |

## Running locally

```bash
bash tests/e2e/test_vidyarthi_sql_mvp.sh
```

The test creates an isolated `$HOME` via `mktemp -d` and removes it on exit,
so it never writes to the developer's real `~/.local/share/shikshan/`.
Expected runtime: 15–30 minutes (QEMU stage 2); seconds for static stages.

## SKIP vs FAIL

- **Exit 77 (SKIP)** — a required prereq is absent (`qemu-system-x86_64`,
  `/dev/kvm`, or the ISO). Not a build failure. To build an ISO:
  `bash scripts/build/build-iso.sh`.
- **Exit 1 (FAIL)** — at least one stage returned FAIL. Check `stderr` for
  `FAIL [stage_N]` lines. Stages are independent; `bwrap`-unavailable causes
  stages 5, 6, 7 to SKIP (not FAIL) but does not abort earlier stages.
- **Exit 0 (PASS)** — all non-skipped stages passed.
