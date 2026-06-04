# Vidyarthi SQL desktop app — smoke test

> Locks: [ADR-0018](../adr/0018-vidyarthi-desktop-app.md). Covers the desktop SQL
> practice app end-to-end: catalog → exercise → SQL editor → grade → score +
> feedback → xAPI. The SQL MVP is **local-only** — no backend is contacted.

This runbook walks the four test layers, fastest first. Layers **L1/L2 run on the
Windows dev box**; **L3/L4 run in the OS VM** (`smo-os-vm`, `192.168.56.10`) where
GTK4 and bubblewrap are available.

## Layout

| Path | Role |
|---|---|
| `…/vidyarthi/src/{catalog,engine_client,session,xapi}.py` | GTK-free core (no `gi`) |
| `…/vidyarthi/src/runner.py` | headless CLI driver (`vidyarthi-run`) |
| `…/vidyarthi/src/{main,window}.py` | GTK frontend (thin view over the core) |
| `…/vidyarthi/engines/sql/main.py` | SQL engine (JSON-RPC, reused unchanged) |
| `/usr/share/applications/in.shikshan.Vidyarthi.desktop` | menu entry (installed) |
| `/etc/skel/Desktop/in.shikshan.Vidyarthi.desktop` | desktop icon for new users |
| `/usr/local/bin/vidyarthi` | GUI launcher wrapper |

---

## L1 — Unit tests (Windows dev box)

Pure `python3 + sqlite3 + PyYAML`; drives the real engine subprocess, no GTK.

```powershell
$env:PATH = "/c/Users/ASUS/bin;$env:PATH"   # python3 shim (repo quirk)
python3 -m pytest tests/unit/vidyarthi/ -q
```

Expect: `14 passed`. Covers catalog resolution, the engine client, session
orchestration, and the xAPI writer.

## L2 — Headless runner (Windows dev box)

The GUI-equivalent path with no GTK. Use an isolated data dir so you never touch a
real `learner.db`:

```powershell
$env:PATH = "/c/Users/ASUS/bin;$env:PATH"
$env:XDG_DATA_HOME = "$env:TEMP\vidyarthi-smoke"
$R = "config/includes.chroot/usr/share/shikshan/vidyarthi/src/runner.py"

python3 $R --list
python3 $R sql-basics 01-select --sql "SELECT * FROM employees;" --submit
```

Expected tail:

```text
score=100 success=true
  [PASS] Your query must run without error.
  [PASS] Expected 10 rows — one per employee.
  [PASS] Select all columns from employees.
  xAPI statement recorded: <uuid>
```

Exit status is `0` for a perfect score, `1` otherwise. Or run the bundled gate:

```bash
bash tests/integration/test_headless_runner.sh     # 3 passed
```

---

## L3 — GUI smoke (OS VM `smo-os-vm`)

Run the actual GTK app under LXQt. Prereqs on the VM:
`python3-gi gir1.2-gtk-4.0 gir1.2-adw-1 gir1.2-gtksource-5 libadwaita-1-0
blueprint-compiler python3-yaml bubblewrap` (all in
[vidyarthi.list.chroot](../../config/package-lists/vidyarthi.list.chroot)).

1. Sync the repo to the VM (e.g. `git pull` in a checkout, or `scp` the tree).
2. Compile the Blueprint UI once (the live ISO does this at build via meson):

   ```bash
   cd config/includes.chroot/usr/share/shikshan/vidyarthi
   blueprint-compiler compile data/ui/window.blp --output data/ui/window.ui
   ```

3. Stage the catalog + module where the launcher looks for them (or rely on the
   repo fallback — `catalog.py` finds `modules/core/<id>/` when the installed
   tree is absent):

   ```bash
   bash scripts/build/sync-ui-to-iso.sh     # populates the includes.chroot overlay
   ```

4. Launch the app:

   ```bash
   python3 config/includes.chroot/usr/share/shikshan/vidyarthi/src/main.py
   # or, once installed on the ISO: vidyarthi
   ```

5. Click **SQL Basics → 01-select**. Confirm: the prompt renders, the editor is
   seeded with the starter SQL and highlights syntax. Type `SELECT * FROM
   employees;` and press **Run** → the results panel shows a green "Correct!" with
   three passing assertions. Press **Submit** → "Progress recorded." appears and a
   row lands in `~/.local/share/shikshan/learner.db`.

Verify telemetry:

```bash
sqlite3 ~/.local/share/shikshan/learner.db \
  'SELECT verb_id, object_id FROM statements;'
# -> http://adlnet.gov/expapi/verbs/scored|vidyarthi://sql-basics/01-select
```

---

## L4 — Full ISO end-to-end (OS VM)

Build, boot, and click the desktop icon.

```bash
bash scripts/build/build-iso.sh            # syncs content + builds the ISO
bash tests/e2e/test_vidyarthi_sql_mvp.sh   # milestone gate (stages 1–8)
```

> The ISO build compiles `window.blp` → `window.ui` automatically via
> `config/hooks/live/0060-vidyarthi-blueprint.hook.chroot` (live-build does not
> run meson). The manual L3 compile step is only needed for a dev checkout.

On a booted ISO: log in as `student`, confirm the **Vidyarthi — Practice** icon is
present both on the desktop and in the Education menu, launch it, and grade
`01-select`. The E2E gate additionally asserts the `.desktop` entry validates, the
launcher wrapper is present, the catalog registers `sql-basics`, and the headless
runner round-trip scores 100.

> LXQt note: a `.desktop` file on the desktop may need to be marked trusted /
> executable on first login (`chmod +x ~/Desktop/in.shikshan.Vidyarthi.desktop`).
> The kiosk image ships it pre-placed via `/etc/skel`.

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `No modules installed.` in the sidebar | catalog not staged / empty | run `sync-ui-to-iso.sh`, or confirm `modules/catalogs/official.catalog.yml` registers `sql-basics` |
| `ModuleNotFoundError: yaml` | `python3-yaml` missing | install it (it is in the package list for the ISO) |
| editor has no SQL highlighting | GtkSourceView SQL lang-spec absent | ensure `gir1.2-gtksource-5` (+ its common data) installed |
| `engine exited before answering` | `python3`/engine path wrong, or bwrap denied | run with `VIDYARTHI_SANDBOX=0` to bypass bwrap and isolate the cause |
| window fails to load (`window.ui` missing) | Blueprint not compiled | run the `blueprint-compiler compile` step (L3 step 2) |
| Submit writes to the wrong home | `XDG_DATA_HOME` set unexpectedly | unset it for real use; set it only for isolated tests |

## What "pass" means

A clean L1 + L2 on the dev box plus a green L4 gate in the OS VM means the desktop
SQL app works end-to-end: a student opens the app from an icon, solves a SQL
exercise, sees graded feedback, and progress is recorded locally.
