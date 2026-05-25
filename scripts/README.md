# scripts/

Helper scripts for the build pipeline, verification, policy enforcement, and developer bootstrap.

| Subdir | Purpose | Protection |
|---|---|---|
| [audit/](audit/) | Audit-log writer, verifier, exporter | PROTECTED — `scripts/audit/**` |
| [build/](build/) | ISO build wrappers, reproducibility, SBOM | Agent-editable |
| [verify/](verify/) | Artifact verifiers (ISO, manifests, license, SLSA) | `verify-slsa.sh` PROTECTED; others agent-editable |
| [policy/](policy/) | Protected-paths + allowlist + budget enforcement | PROTECTED — `scripts/policy/**` |
| [dev/](dev/) | One-time developer setup | Agent-editable |

## Conventions

- Bash scripts use `#!/usr/bin/env bash` and `set -euo pipefail`.
- Python scripts use `#!/usr/bin/env python3` and target Python 3.12+.
- All scripts emit `[<name>] <message>` log lines so pipelines are diff-able.
- Exit codes are documented in each script's docstring; tests assert on them.

## Adding a script

1. Pick the right subdir.
2. If it enforces policy, put it under `scripts/policy/` — and accept that it becomes PROTECTED.
3. Add a brief description to the parent README's table.
4. Add a test under `tests/integration/` exercising the exit codes.
