# Architecture Overview

> **Scope:** what's in the box, how the pieces fit, what's intentionally out of scope.
> **Canonical product spec:** [PLAN.md](../../PLAN.md). This doc is the architectural lens on that spec.

## Context (C4 Level 1)

```
                       ┌──────────────────────────┐
                       │  School / Community ops  │
                       └────────────┬─────────────┘
                                    │
                                    ▼
   ┌────────────────────────────────────────────────────────────┐
   │             Shikshan Mantra OS (this repo)                 │
   │                                                            │
   │   live USB / install-to-disk on 2 GB-RAM 64-bit device     │
   └─────────┬──────────────────────┬─────────────┬────────────┘
             │                      │             │
       (optional)              (optional)     (optional)
             ▼                      ▼             ▼
     ┌──────────────┐       ┌──────────────┐  ┌──────────────┐
     │ School sync  │       │ Community    │  │ AI provider  │
     │ server       │       │ catalog srv  │  │ (local/cloud)│
     └──────────────┘       └──────────────┘  └──────────────┘
```

Everything inside the OS must work fully offline; the three external systems are optional integrations.

## Containers (C4 Level 2)

```
┌─────────────────────────────────────────────────────────────────────────┐
│ Shikshan Mantra OS image                                                │
│                                                                         │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐       │
│  │ Live boot stack  │  │ Desktop session  │  │ Installer        │       │
│  │ (live-build)     │  │ (LXQt / IceWM)   │  │ (Calamares)      │       │
│  └────────┬─────────┘  └────────┬─────────┘  └─────────┬────────┘       │
│           │                     │                      │                │
│           ▼                     ▼                      ▼                │
│  ┌──────────────────────────────────────────────────────────────┐       │
│  │ Module launcher (custom)  +  Kolibri (offline learning)      │       │
│  └────────┬─────────────────────────────────┬───────────────────┘       │
│           │                                 │                           │
│           ▼                                 ▼                           │
│  ┌──────────────────┐               ┌──────────────────┐                │
│  │ Catalog + module │               │ Local SQLite     │                │
│  │ verifier (sig)   │               │ progress store   │                │
│  └──────────────────┘               └──────────────────┘                │
│                                                                         │
│  ┌──────────────────────────────────────────────────────────────┐       │
│  │ Web-safety stack: DNS filter + Firefox/Chromium policies +   │       │
│  │ optional E2Guardian proxy + admin override                   │       │
│  └──────────────────────────────────────────────────────────────┘       │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

See [module-system.md](module-system.md), [progress-store.md](progress-store.md), and [threat-model.md](threat-model.md) for component drill-downs.

## Public interfaces (canonical schemas)

All public interface schemas live in:
- [modules/catalogs/schemas/module.schema.json](../../modules/catalogs/schemas/module.schema.json)
- [modules/catalogs/schemas/catalog.schema.json](../../modules/catalogs/schemas/catalog.schema.json)
- [tasks/schema/task.schema.yml](../../tasks/schema/task.schema.yml)
- (admin policy schema lives at `config/includes.chroot/etc/shikshan/policy.schema.json` once Phase 7 builds it)

The schemas are the contract. PLAN.md describes them in prose; the JSON Schemas in this repo are authoritative.

## Build pipeline (declarative — no manual remastering)

```
auto/config  →  live-build resolves config/      ↓
                                                 ↓ bootstrap
config/archives/    (pinned snapshot.debian.org) ↓
config/package-lists/  → debootstrap +           ↓
config/hooks/live/     → apt install + chroot    ↓
config/includes.chroot/  → copy files            ↓
config/hooks/normal/   → image-build hooks       ↓
config/bootloaders/   (PROTECTED)                ↓
                                                 ↓
                              artifacts/shikshan.iso
                                  │
                                  ▼
                 SBOM (Syft → CycloneDX), Lintian, SHA-256
                                  │
                                  ▼
                 Tag → SLSA L2+ provenance → Cosign keyless sign
                                  │
                                  ▼
                          GitHub Release
```

## Out of scope (v1)

- Full local LLM ("AI assistant" tier supports browser/WebGPU experiments only; server/cloud assistant is optional)
- Per-user homedir encryption (per-volume persistence encryption is in scope)
- Mesh networking between devices
- Mobile/ARM builds (Phase 2 candidate)
- Real-time multiplayer collaboration tools
