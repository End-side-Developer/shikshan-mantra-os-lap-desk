# tests/smoke/

Quick shell scripts that assert structural and content invariants **without
running live-build or booting a VM**. Each script exits 0 silently on pass
and non-zero with a `FAIL: <reason>` line on stderr on miss.

Run all smoke tests locally:

```bash
bash tests/smoke/test_repo_layout.sh
bash tests/smoke/test_protected_paths_policy.sh
bash tests/smoke/test_auto_config_flags.sh
bash tests/smoke/test_hook_0010_locale.sh
bash tests/smoke/test_hook_0020_user_student.sh
bash tests/smoke/test_hook_0030_autologin.sh
bash tests/smoke/test_hook_0040_dnsmasq_school_safe.sh
```

## Hook static-analysis tests (SMO-0305)

Each test below greps the corresponding
`config/hooks/live/*.hook.chroot` source file for required patterns and
optionally runs `shellcheck -s sh` against it.

| Test | Hook | What it asserts |
|---|---|---|
| `test_hook_0010_locale.sh` | `0010-locale-default.hook.chroot` | `#!/bin/sh`, `set -eu`, `locale-gen`, `en_IN UTF-8`, `hi_IN UTF-8`, `update-locale ... en_IN.UTF-8` |
| `test_hook_0020_user_student.sh` | `0020-user-student.hook.chroot` | `#!/bin/sh`, `set -eu`, `adduser --disabled-password`, `--uid 1000`, groups `audio video plugdev netdev`, `passwd -l root` |
| `test_hook_0030_autologin.sh` | `0030-autologin.hook.chroot` | `#!/bin/sh`, `set -eu`, `50-shikshan-autologin.conf`, `autologin-user=student`, `autologin-session=lxqt` |
| `test_hook_0040_dnsmasq_school_safe.sh` | `0040-dnsmasq-school-safe.hook.chroot` | `#!/bin/sh`, `set -eu`, `shikshan-school-safe.conf`, `server=1.1.1.3`, `server=1.0.0.3`, `no-resolv`, `systemctl enable dnsmasq` |

**Pre-commit / CI wiring:** deferred to SMO-0308 (smoke-runner orchestrator).
These tests are not yet enumerated in `.pre-commit-config.yaml`.
