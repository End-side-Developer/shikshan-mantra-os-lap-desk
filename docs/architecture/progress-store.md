# Progress Store

Local SQLite database that records each learner's progress per module, supporting offline-first operation with optional sync to a school/community server.

## Location

- Live session (no persistence): in-memory; lost at reboot (by design — a kiosk-style profile).
- Live session (with persistence partition): `/var/lib/shikshan/progress.db` on the persistence volume.
- Installed system: `/var/lib/shikshan/progress.db` on the user's home volume.

Encryption: per the admin policy file's `persistence_encryption_required` field. When true, the persistence partition is LUKS-encrypted at install time.

## Schema (high-level)

```sql
CREATE TABLE students (
  student_id_local TEXT PRIMARY KEY,    -- UUIDv4 generated locally
  display_name     TEXT NOT NULL,
  age_band         TEXT,
  language         TEXT,
  created_at       TEXT NOT NULL
);

CREATE TABLE module_progress (
  student_id_local TEXT NOT NULL REFERENCES students(student_id_local),
  module_id        TEXT NOT NULL,
  attempts         INTEGER NOT NULL DEFAULT 0,
  score            REAL,
  completion_state TEXT NOT NULL,       -- not_started | in_progress | completed | failed
  earned_badges    TEXT,                -- JSON array
  last_synced_at   TEXT,                -- RFC3339; NULL = never synced
  updated_at       TEXT NOT NULL,
  PRIMARY KEY (student_id_local, module_id)
);

CREATE TABLE sync_state (
  endpoint        TEXT PRIMARY KEY,
  last_push_seq   INTEGER NOT NULL DEFAULT 0,
  last_pull_seq   INTEGER NOT NULL DEFAULT 0,
  last_attempt_at TEXT,
  last_error      TEXT
);
```

## Privacy defaults

- `student_id_local` is opaque, generated on-device, never derived from a name or government ID.
- No PII other than `display_name` (which can be a nickname) is stored.
- The admin policy defaults to **no sync** (`sync_endpoint: null`). Sync is opt-in per-school.

## Sync protocol (when enabled)

- Push-only by default; pull only when `pull_on_sync: true` in admin policy.
- Authentication: per-school bearer token issued out-of-band; rotated quarterly per [docs/runbooks/rotate-signing-key.md](../runbooks/rotate-signing-key.md) (same custody pattern).
- Wire format: append-only JSONL over HTTPS; server-side de-duplication by `(student_id_local, module_id, updated_at)`.
- Conflict resolution: **client-wins** (the device is the source of truth for what the learner did).

## Anti-features (intentionally NOT in scope)

- No leaderboards, no inter-student comparisons by default
- No automated content recommendations based on individual performance (recommendations are catalog-level, not personalized ML)
- No telemetry to upstream Shikshan Mantra OS project unless explicitly opted into in admin policy
