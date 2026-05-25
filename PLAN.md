# Shikshan Mantra OS v1 Plan

## Summary
Build a Debian 13.5 “trixie” based education OS using `live-build`, targeting 64-bit low-end devices with 2GB RAM. v1 will boot from a live USB, support VM testing, and include an install-to-disk path.

The OS will ship an open-source core with optional extra installers, English plus Hindi as the default language set, school-safe web protection with admin override, free built-in learning modules, moderated community catalogs, local progress with optional sync, and AI as a learning assistant plus AI curriculum rather than heavy local model training.

## Key Changes
- Base OS: Debian 13.5 stable + `live-build`; no manual ISO/squashfs remastering for production.
- Desktop: lightweight LXQt default, IceWM rescue/ultra-low mode, avoid GNOME/KDE in v1.
- Installer: include a Calamares-based install path from the live session.
- Learning platform: Kolibri for offline learning, plus a custom module launcher for coding, AR, AI, cyber safety, guidebooks, and practical labs.
- Module ecosystem: signed module catalogs with official core modules and approved community/institution catalogs.
- Progress system: local SQLite progress store on persistence/install storage, optional sync to a school/community server.
- AI system: local AI literacy lessons, prompt practice, tiny demos, optional browser/WebGPU experiments, and optional server/cloud assistant; no full local LLM requirement on 2GB devices.
- Coding: Blockly-based visual coding, TurboWarp/Scratch-style beginner path, Python/JS labs, and optional Codium/open-source editor profile.
- AR/practical labs: WebXR/Three.js/A-Frame modules with automatic desktop 3D fallback when AR hardware/browser support is unavailable.
- Web safety: DNS filtering, Firefox/Chromium enterprise policies, optional E2Guardian proxy, local logs, admin override, and age/community policy profiles.

## Public Interfaces
- Learning module manifest: `id`, `version`, `title`, `language`, `age_band`, `difficulty`, `prerequisites`, `outcomes`, `content_type`, `entrypoint`, `required_apps`, `unlock_rules`, `license`, `checksum`, `signature`.
- Catalog manifest: `catalog_id`, `publisher`, `trust_level`, `modules`, `signature`, `update_url`.
- Progress record: `student_id_local`, `module_id`, `attempts`, `score`, `completion_state`, `earned_badges`, `last_synced_at`.
- Admin policy file: safety mode, allowed catalogs, blocked categories/domains, sync endpoint, AI provider mode, persistence encryption requirement.
- Repo rules: root `AGENTS.md`, architecture decisions, package manifests, hooks, CI checks, and PR template must define what AI agents may edit and how changes are verified.

## Development Rules
- All OS changes must be declarative through `live-build` config, package lists, includes, hooks, or documented module manifests.
- No unreviewed binary blobs, unpinned download scripts, proprietary default apps, unsafe chmod/curl installer patterns, or silent network dependencies in the ISO.
- Any AI agent must read `AGENTS.md`, preserve safety defaults, add tests for changed behavior, cite source docs for OS/tooling changes, and avoid changing generated build artifacts directly.
- CI must build the ISO in a clean environment, produce hashes/SBOM, run package manifest linting, run shellcheck, boot QEMU in BIOS and UEFI modes, and smoke-test live, persistence, installer, filtering, module launch, and offline learning.

## Test Plan
- Build: clean `live-build` ISO build, artifact hash generation, package manifest export, and reproducible-build check using pinned/snapshot repositories for releases.
- Boot: QEMU BIOS, QEMU UEFI, 2GB RAM profile, no-network boot, live USB boot, persistence boot, encrypted persistence boot.
- Install: live-to-disk install in VM, first boot after install, user creation, updates, module launcher, safety policy retained.
- Learning: Kolibri opens offline, free modules appear, community catalog signature validation works, locked modules unlock after success criteria.
- AI: offline AI lessons work without internet, optional assistant clearly switches between local/server/cloud, low-RAM profile disables heavy services.
- Safety: blocked sites fail, allowed education sites work, admin override works, logs are local and privacy-aware.
- UX/accessibility: English/Hindi switching, keyboard navigation, readable fonts, low-resolution screens, and slow-device startup time.

## Assumptions And Sources
- Locked choices: Debian `live-build`, 2GB 64-bit target, live plus installer, all ages, English plus Hindi, open core with optional extras, school-safe admin override, official plus community modules, local plus optional sync, AI learning plus assistant.
- Primary sources: [Debian releases](https://www.debian.org/releases/index.en.html), [Debian 13.5 release](https://www.debian.org/News/2026/20260516), [Debian Live Manual](https://live-team.pages.debian.net/live-manual/html/live-manual.en.html), [live-build manpage](https://manpages.debian.org/bookworm/live-build/live-build.7.en.html), [Debian Live examples](https://live-team.pages.debian.net/live-manual/html/live-manual/examples.en.html), [Debian hardware requirements](https://www.debian.org/releases/trixie/arm64/ch03s04.en.html), [Kolibri](https://kolibri.readthedocs.io/en/latest/index.html), [Kolibri Studio](https://kolibri-studio.readthedocs.io/en/latest/index.html), [Blockly](https://docs.blockly.com/), [WebXR MDN](https://developer.mozilla.org/en-US/docs/Web/API/WebXR_Device_API/Fundamentals), [Three.js ARButton](https://threejs.org/docs/pages/ARButton.html), [Pi-hole](https://docs.pi-hole.net/), [Firefox policies](https://support.mozilla.org/en-US/kb/where-can-i-find-list-policies-firefox-enterprise), [Chromium URLBlocklist](https://www.chromium.org/administrators/url-blocklist-filter-format/), [E2Guardian](https://manpages.debian.org/bookworm/e2guardian/e2guardian.8.en.html), [WebLLM](https://webllm.mlc.ai/docs/user/get_started.html), [Open WebUI performance](https://docs.openwebui.com/troubleshooting/performance/).
