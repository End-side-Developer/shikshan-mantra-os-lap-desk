# Runbook — Protected `config/` Bootstrap

The sandbox correctly enforced our own `policies/protected-paths.yml` deny list while the scaffolding agent ran. Three protected files need to be created by a human (with `touches-bootloader`, `touches-packages`, or `touches-safety-defaults` two-team review) before they will exist.

## File 1 — `config/bootloaders/README.md`

```markdown
# config/bootloaders/

PROTECTED — every file under this directory is gated by `touches-bootloader` (security + platform two-team approval) per `policies/sensitive-change-labels.yml`.

## Why protected

The bootloader is the **first** code that runs on the device. Silent modification could bypass measured-boot integrity, disable kernel security parameters, substitute the kernel image, or add a hidden boot entry.

## Contents (added by Phase 8 task SMO-0070)

config/bootloaders/
├── isolinux/
│   ├── isolinux.cfg          # main menu (Live | Rescue | Install | Verify ISO)
│   ├── menu.cfg
│   └── splash.png
└── grub-efi/
    ├── grub.cfg
    └── shikshan-theme/

Until SMO-0070 lands, live-build uses Debian's defaults. The defaults are safe but unbranded.

## Editing rules

1. Open `touches-bootloader` PR (auto-labelled by `.github/labeler.yml`).
2. ADR documenting the change.
3. 2 distinct approvals from `@shikshan/security` + `@shikshan/platform`.
4. Reproducibility check must pass post-merge (`ci-reproducible.yml`).
5. QEMU BIOS + UEFI smoke tests must pass.
```

## File 2 — `config/packages.chroot/README.md`

```markdown
# config/packages.chroot/

PROTECTED — in-house `.deb` files. Every change here applies the `touches-packages` label per `policies/sensitive-change-labels.yml`, requiring:
- Two distinct approvals (`@shikshan/security` + `@shikshan/platform`)
- A signed (gpg-signed-tag) commit
- A matching ADR

## Why this exists (and why it's nearly empty in v1)

Most of what Shikshan Mantra OS needs is already in Debian. We only resort to a custom `.deb` when:
1. The upstream is not in Debian
2. The package needs a school-safe patch that Debian wouldn't carry
3. We need to bundle Shikshan-specific assets that don't fit `includes.chroot/`

## Build process for an in-house deb

1. Maintain the source in a sibling repo (e.g., `shikshan-mantra-os/<package>`).
2. Build the deb in CI with reproducible-build flags.
3. Sign with cosign keyless.
4. Open a `touches-packages` PR placing the `.deb` here with checksum + signature attached.

## v1 contents

(empty — populated when the first in-house package lands; SMO-0080 follow-up task tracks the policy launcher package)
```

## File 3 — `config/includes.chroot/etc/firefox/policies/policies.json`

This is the school-safe Firefox enterprise policy. Mozilla's [policy templates](https://mozilla.github.io/policy-templates/) document each field.

```json
{
  "policies": {
    "BlockAboutConfig": true,
    "BlockAboutProfiles": true,
    "DisableTelemetry": true,
    "DisableFirefoxStudies": true,
    "DisablePocket": true,
    "DisableFirefoxAccounts": true,
    "DisableMasterPasswordCreation": false,
    "DontCheckDefaultBrowser": true,
    "DNSOverHTTPS": {
      "Enabled": false,
      "Locked": true
    },
    "EnableTrackingProtection": {
      "Value": true,
      "Locked": true
    },
    "FirefoxHome": {
      "Search": true,
      "TopSites": false,
      "SponsoredTopSites": false,
      "Highlights": false,
      "Pocket": false,
      "SponsoredPocket": false,
      "Locked": true
    },
    "HardwareAcceleration": true,
    "Homepage": {
      "URL": "http://localhost:8080/launcher/",
      "Locked": false,
      "StartPage": "homepage"
    },
    "PasswordManagerEnabled": false,
    "PopupBlocking": {
      "Default": "block-all",
      "Locked": true
    },
    "Preferences": {
      "browser.safebrowsing.malware.enabled": { "Value": true, "Status": "locked" },
      "browser.safebrowsing.phishing.enabled": { "Value": true, "Status": "locked" },
      "browser.safebrowsing.blockedURIs.enabled": { "Value": true, "Status": "locked" }
    },
    "URLBlocklist": []
  }
}
```

`DNSOverHTTPS` is locked to disabled so the local dnsmasq school-safe DNS (1.1.1.3 / 1.0.0.3 from `config/hooks/live/0040-dnsmasq-school-safe.hook.chroot`) is honored. `URLBlocklist` is populated at runtime from `/etc/shikshan/policy.yml#blocked_domains`.

## Commit

```bash
mkdir -p config/bootloaders config/packages.chroot config/includes.chroot/etc/firefox/policies
# Create each file from the blocks above.
git add config/bootloaders/README.md config/packages.chroot/README.md \
        config/includes.chroot/etc/firefox/policies/policies.json
git commit -S -m "build(config): bootstrap protected config readmes + firefox enterprise policy"
```

The Firefox policy commit will auto-apply the `touches-safety-defaults` label and require two-team review (security + safety + platform) per `policies/sensitive-change-labels.yml`.
