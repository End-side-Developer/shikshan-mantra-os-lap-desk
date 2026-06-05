# Vidyarthi Python coding module — smoke test

> Locks: [ADR-0019](../adr/0019-code-engine-runtime.md). Covers the desktop Python
> coding practice app end-to-end: catalog → exercise → Python editor → grade →
> score + feedback → xAPI. The Python MVP is **local-only** — no backend is
> contacted.

This runbook walks the four test layers, fastest first. Layers **L1/L2 run on the
Windows dev box**; **L3/L4 run in the OS VM** (`smo-os-vm`, `192.168.56.10`) where
GTK4 and bubblewrap are available.

## Layout

| Path | Role |
|---|---|
| `…/vidyarthi/src/{catalog,engine_client,session,xapi}.py` | GTK-free core (no `gi`) |
| `…/vidyarthi/src/runner.py` | headless CLI driver |
| `…/vidyarthi/src/{main,window}.py` | GTK frontend (thin view over the core) |
| `…/vidyarthi/engines/code/main.py` | Python engine (JSON-RPC, subprocess grader) |
| `…/vidyarthi/engines/code/sandbox.bwrap` | namespace isolation profile |
| `…/vidyarthi/engines/code/seccomp.json` | seccomp allowlist (no network syscalls) |
| `modules/core/python-basics/` | exercises: hello-world, even-or-odd, sum-to-n |
| `/usr/share/applications/in.shikshan.Vidyarthi.desktop` | menu entry (installed) |
| `/etc/skel/Desktop/in.shikshan.Vidyarthi.desktop` | desktop icon for new users |
| `/usr/local/bin/vidyarthi` | GUI launcher wrapper |

---

## L1 — Unit tests (Windows dev box)

Pure `python3 + PyYAML`; drives the real engine subprocess, no GTK.

```powershell
$env:PATH = "/c/Users/ASUS/bin;$env:PATH"   # python3 shim (repo quirk)
python3 -m pytest tests/engines/test_code_engine.py -v
```

Expect: `11 passed`. Covers init handshake, load_exercise, correct/wrong/syntax-error
grading, bilingual feedback keys, timeout (-32003), unsupported `run` method (-32601),
and shutdown.

## L2 — Headless runner (Windows dev box)

The GUI-equivalent path with no GTK. Use an isolated data dir:

```powershell
$env:PATH = "/c/Users/ASUS/bin;$env:PATH"
$env:XDG_DATA_HOME = "$env:TEMP\vidyarthi-python-smoke"
$R = "config/includes.chroot/usr/share/shikshan/vidyarthi/src/runner.py"

python3 $R --list                                                # python-basics listed
python3 $R python-basics 01-hello --code 'print("Hello, World!")' --submit
```

Expected tail:

```text
score=1 success=true
  All test cases passed. Well done!
  xAPI statement recorded: <uuid>
```

Exit status is `0` for a perfect score, `1` otherwise.

Try the other exercises to confirm the full module:

```powershell
python3 $R python-basics 02-conditionals --code "n = int(input()); print('even' if n%2==0 else 'odd')" --submit
python3 $R python-basics 03-loops      --code "n = int(input()); print(n*(n+1)//2)" --submit
```

Verify xAPI rows landed:

```powershell
sqlite3 "$env:TEMP\vidyarthi-python-smoke\shikshan\learner.db" `
  "SELECT verb_id, object_id FROM statements;"
```

Expected rows (one per `--submit` call):

```text
http://adlnet.gov/expapi/verbs/scored|vidyarthi://python-basics/hello-world
http://adlnet.gov/expapi/verbs/scored|vidyarthi://python-basics/even-or-odd
http://adlnet.gov/expapi/verbs/scored|vidyarthi://python-basics/sum-to-n
```

---

## L3 — GUI smoke (OS VM `smo-os-vm`)

Run the actual GTK app under LXQt. Prereqs on the VM:
`python3-gi gir1.2-gtk-4.0 gir1.2-adw-1 gir1.2-gtksource-5 libadwaita-1-0
blueprint-compiler python3-yaml bubblewrap python3` (all in
[vidyarthi.list.chroot](../../config/package-lists/vidyarthi.list.chroot)).

1. Boot the VM:

   ```powershell
   pwsh scripts/vm/smo-vms.ps1 -Boot smo-os-vm
   ```

2. Log in as `student` (default password `student`).

3. Compile the Blueprint UI once (the live ISO does this automatically at build):

   ```bash
   cd config/includes.chroot/usr/share/shikshan/vidyarthi
   blueprint-compiler compile data/ui/window.blp --output data/ui/window.ui
   ```

4. Launch the app:

   ```bash
   python3 config/includes.chroot/usr/share/shikshan/vidyarthi/src/main.py
   # or, once installed on the ISO: vidyarthi
   ```

5. In the **Modules** sidebar, click **Python Basics**. Confirm the exercise list
   populates with three entries: Hello, World! / Even or Odd / Sum to N.

6. Click **Hello, World!**. Confirm: the prompt renders in the content pane, the
   editor is seeded with `print("")` and highlights Python syntax (green keywords,
   strings in a different colour).

7. Replace the starter code with:

   ```python
   print("Hello, World!")
   ```

8. Press **Submit**. Confirm: green "Correct!" banner appears with "All test cases
   passed. Well done!" and a "Progress recorded." note.

Verify telemetry:

```bash
sqlite3 ~/.local/share/shikshan/learner.db \
  'SELECT verb_id, object_id FROM statements;'
# -> http://adlnet.gov/expapi/verbs/scored|vidyarthi://python-basics/hello-world
```

---

## L4 — Full ISO end-to-end (OS VM)

Build, boot, and click the desktop icon.

```bash
bash scripts/build/build-iso.sh                       # syncs content + builds ISO
VIDYARTHI_SKIP_E2E=0 bash tests/e2e/test_vidyarthi_python_mvp.sh
```

> The ISO build compiles `window.blp` → `window.ui` automatically via
> `config/hooks/live/0060-vidyarthi-blueprint.hook.chroot` (live-build does not
> run meson). The manual L3 compile step is only needed for a dev checkout.

On a booted ISO: log in as `student`, confirm the **Vidyarthi — Practice** icon is
present on the desktop and in the Education menu, launch it, and solve **Hello,
World!**. The E2E gate additionally asserts the `.desktop` entry validates, the
launcher wrapper is present, the catalog registers `python-basics`, and the direct
engine grade round-trip scores 1.

> LXQt note: a `.desktop` file on the desktop may need to be marked trusted on first
> login. The kiosk image ships it pre-placed via `/etc/skel`.

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `No modules installed.` in the sidebar | catalog not staged / empty | confirm `modules/catalogs/official.catalog.yml` lists `python-basics`; run `sync-ui-to-iso.sh` |
| `ModuleNotFoundError: yaml` | `python3-yaml` missing | install it (it is in the package list for the ISO) |
| editor has no Python highlighting | GtkSourceView python3 lang-spec absent | ensure `gir1.2-gtksource-5` (+ common data) installed |
| `engine exited before answering` | engine path wrong or bwrap denied | run with `VIDYARTHI_SANDBOX=0` to bypass bwrap and isolate the cause |
| `unsupported sub_engine 'code'` | old `engine_client.py` without SMO-0805 changes | pull latest `main` and re-sync |
| window fails to load (`window.ui` missing) | Blueprint not compiled | run the `blueprint-compiler compile` step (L3 step 3) |
| grading returns `-32003` (timeout) | infinite loop or `max_execution_ms` too low | check submission code; default is 10 s, minimum schema-enforced is 100 ms |
| no xAPI row after Submit | `learner.db` path mismatch | check `XDG_DATA_HOME`; default is `~/.local/share/shikshan/learner.db` |

## What "pass" means

A clean L1 + L2 on the dev box plus a green L4 gate in the OS VM means the desktop
Python coding app works end-to-end: a student opens the app from an icon, solves a
Python exercise, sees graded feedback, and progress is recorded locally.
