# Runbook — VM automation (`scripts/vm/smo-vms.ps1`)

One idempotent PowerShell script that **creates-or-reuses** the two VirtualBox VMs
and boots the latest ISO. Run it after every `build-iso.sh` to refresh the OS VM.

**ADR:** [ADR-0017](../adr/0017-content-backend-architecture.md) (topology).
**Related:** [virtualbox-host-only-network.md](virtualbox-host-only-network.md),
[backend-vm-bootstrap.md](backend-vm-bootstrap.md),
[vidyarthi-sql-desktop-smoke.md](vidyarthi-sql-desktop-smoke.md).

## What it manages (two SEPARATE VMs)

| VM | IP (in-guest) | Role | Script behaviour |
|---|---|---|---|
| `smo-os-vm` | `192.168.56.10` | live-boots the latest `releases/*.iso` (ephemeral, no disk) | create-or-reuse, **attach newest ISO**, boot GUI |
| `smo-be-vm` | `192.168.56.20` | persistent Debian content backend (FastAPI `/health`) | reuse if present (never disturbs saved state/disk); create shell + attach Debian netinst if absent |

Both share the host-only adapter at `192.168.56.0/24` (the script reuses the
adapter that already owns `192.168.56.1`, or creates one with DHCP disabled). The
static in-guest IPs (`.10` / `.20`) are still set **inside** each guest per the
runbooks above — `VBoxManage` only attaches the adapter.

## Usage (PowerShell, from the repo root)

```powershell
# Ensure both VMs, attach the newest ISO to the OS VM, boot (OS=GUI, backend=headless)
.\scripts\vm\smo-vms.ps1

# Just the OS VM (the SQL app is local-only, so this alone tests it)
.\scripts\vm\smo-vms.ps1 -Target os

# Set the latest ISO without booting
.\scripts\vm\smo-vms.ps1 -Target os -NoStart

# Inspect / power off
.\scripts\vm\smo-vms.ps1 -Action status
.\scripts\vm\smo-vms.ps1 -Action stop -Target both

# Override the ISO explicitly
.\scripts\vm\smo-vms.ps1 -Target os -Iso .\releases\shikshan-mantra-os-<ver>-amd64.iso
```

`VBoxManage.exe` is found at `D:\Oracle\VirtualBox\` (or `$env:VBOX_MSI_INSTALL_PATH`,
or on `PATH`). The OS VM gets 2 GB RAM (the device target) and boots the live ISO
from an IDE DVD; re-running powers it off, swaps in the newest ISO, and reboots.

## Typical loop after a code change

```powershell
bash scripts/build/build-iso.sh          # produces releases/...-<newhash>.iso
.\scripts\vm\smo-vms.ps1 -Target os      # OS VM picks up the newest ISO and boots
```

Then in the booted OS: log in as `student`, open **Vidyarthi - Practice** from the
desktop/menu, and grade an exercise (see
[vidyarthi-sql-desktop-smoke.md](vidyarthi-sql-desktop-smoke.md)).

## Notes & guardrails

- **OS VM is ephemeral.** No virtual disk is attached, so every boot is a clean live
  session of the latest ISO — ideal for testing. (Add a disk later if you want to test
  the install-to-disk / "claim" flow.)
- **Backend VM is never disturbed on reuse.** The script only refreshes its host-only
  NIC when it is fully powered off; a `saved`/`running` backend is left exactly as
  provisioned, and its disk/NAT are never touched.
- **Starting a GUI VM needs an interactive desktop session.** Run the script from your
  own PowerShell window, not a service/SSH-only context.
- **Fresh backend creation is shell-only.** If `smo-be-vm` is absent the script creates
  the VM, disk, NICs, and attaches `C:\ISOs\debian-13-netinst-amd64.iso` if present —
  the Debian install + backend setup remain manual per
  [backend-vm-bootstrap.md](backend-vm-bootstrap.md).
