# config/

Declarative live-build configuration. Per [Debian Live Manual § Customization overview](https://live-team.pages.debian.net/live-manual/html/live-manual/customization-overview.en.html), everything live-build does to the image is driven by this tree.

```
config/
├── archives/             # APT sources (.list.chroot), pinning (.pref.chroot), keys (.key.chroot)
├── bootloaders/          # GRUB/syslinux assets (PROTECTED — touches-bootloader)
├── hooks/
│   ├── live/             # *.hook.chroot — run inside the chroot
│   └── normal/           # *.hook.binary — run during image assembly
├── includes.chroot/      # Files copied into the live system at chroot path
│   ├── etc/
│   ├── usr/
│   └── var/
├── package-lists/        # *.list.chroot installed packages
├── packages.chroot/      # Custom .deb files (PROTECTED — touches-packages)
└── preseed/              # Calamares preseed
```

## Agent-editable vs protected

| Subpath | Agent allowed? | Required label on PR |
|---|---|---|
| `archives/debian.list.chroot` | No (signed pin) | `touches-signing` |
| `archives/*.key.*` | No | `touches-signing` |
| `bootloaders/**` | No | `touches-bootloader` |
| `packages.chroot/**` | No | `touches-packages` (signed commit required) |
| `hooks/live/**`, `hooks/normal/**` | Yes | `touches-platform` (default review) |
| `includes.chroot/etc/firefox/**` | No directly | `touches-safety-defaults` |
| `includes.chroot/etc/shikshan/**` | Yes (with parity check) | `touches-safety-defaults` |
| `includes.chroot/usr/share/shikshan/**` | Yes | default |
| `package-lists/*.list.chroot` | Yes | default (license-scan check) |
| `preseed/**` | Yes | default |

See `policies/agent-allowlist.yml` for the canonical list.

## Reproducibility

The `archives/debian.list.chroot` pin to `snapshot.debian.org` is what makes our builds reproducible across machines and time. Changing the pin requires:
1. ADR documenting why
2. Two-team approval (security + release-managers)
3. Reproducibility re-validation in `ci-reproducible.yml`
