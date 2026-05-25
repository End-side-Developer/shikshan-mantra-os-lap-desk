# config/archives/

APT source lists, pinning preferences, and archive keys for the live-build process.

| File | Purpose | Edit policy |
|---|---|---|
| `debian.list.chroot` | Main Debian repos pinned to snapshot.debian.org | PROTECTED (touches-signing) |
| `debian.pref.chroot` | APT pinning priorities | PROTECTED (touches-signing) |
| `debian.key.chroot` | Debian archive keyring (binary; not committed — pulled at build time per ADR-NN) | PROTECTED (touches-signing) |

## Why everything here is protected

A silent change to a `.list.chroot` URL or a `.key.chroot` key can substitute the package source. That is the textbook supply-chain attack. The `touches-signing` label requires:
- 2 approvals from `@shikshan/security` + `@shikshan/release-managers`
- A signed (gpg-signed-tag) commit
- An ADR documenting the change

`debian.key.chroot` is NOT committed to the repo in v1. The build script pulls it from a pinned Debian keyring package at chroot time, validated against the keyring's published fingerprint. See [docs/runbooks/rotate-signing-key.md § B](../../docs/runbooks/rotate-signing-key.md#b-debian-archive-key-update) for the rotation procedure.

## Adding a third-party repository

Do not. v1 ships from Debian's main + security + updates only. Adding a third-party repo requires:
1. ADR justifying the dependency
2. A new `.list.chroot`, `.pref.chroot` (priority ≤ Debian's), and `.key.chroot` file
3. Two-team approval per `touches-signing`

Any package needed but not in Debian should first be evaluated against in-house packaging under `config/packages.chroot/` (also protected).
