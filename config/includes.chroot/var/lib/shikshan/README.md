# /var/lib/shikshan/

Per-system state for Shikshan Mantra OS.

| Path | Purpose | Created by |
|---|---|---|
| `progress.db` | Local SQLite progress store (see [docs/architecture/progress-store.md](../../../../../../docs/architecture/progress-store.md)) | Launcher on first run; ships as an empty schema in the image |
| `catalogs/` | Local cache of fetched catalogs (signed) | Launcher on demand |
| `modules/` | Local cache of fetched module content | Launcher on demand |
| `keys/` | Public verification keys (root catalog key) | Shipped in the image; rotated only via signed OS update |

The directory ships in the image with `keys/` populated and an empty `progress.db` schema. Runtime state is created when the launcher first runs.
