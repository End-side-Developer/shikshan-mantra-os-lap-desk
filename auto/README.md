# auto/

Live-build wrapper scripts per [Debian Live Manual § Build automation](https://live-team.pages.debian.net/live-manual/html/live-manual/customizing-the-build.en.html#auto-scripts).

| Script | Purpose | Protection |
|---|---|---|
| `config` | Encapsulates `lb config` with locked project parameters | `touches-bootloader` (two-team review) |
| `build` | Runs `lb build` and moves output to `artifacts/` | `touches-bootloader` |
| `clean` | Purges live-build state | `touches-bootloader` |

All three are PROTECTED. Agents may not edit them without `allowlist-override` + two-team approval. The CODEOWNERS line `/auto/  @shikshan/platform @shikshan/security` enforces this.

## Why this is so tightly controlled

`auto/config` decides every build-time parameter — distribution, mirrors, kernel, persistence encryption, boot append options. A silent edit here could:
- Pull from a different mirror (supply-chain risk)
- Change kernel cmdline to disable safety features
- Switch off persistence encryption
- Add non-free repositories

Any change here is a security-class change and requires an ADR.

## Invocation

```bash
# Inside the pinned debian:trixie build container, as root:
./auto/build
```

For maintainer-facing instructions see [docs/runbooks/build-iso-locally.md](../docs/runbooks/build-iso-locally.md).
