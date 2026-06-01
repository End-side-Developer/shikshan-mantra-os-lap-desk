# Runbook — VirtualBox Host-Only Network (vboxnet-smo)

Sets up the `vboxnet-smo` adapter (`192.168.56.0/24`) shared by both VMs so they can
reach each other without going through the internet.

**Complete this runbook before provisioning either VM.**

**ADR:** [ADR-0017](../adr/0017-content-backend-architecture.md)

---

## IP address assignments

| Host | Interface | Static IP |
|---|---|---|
| `smo-os-vm` (OS live image) | `enp0s8` (host-only) | `192.168.56.10` |
| `smo-be-vm` (backend VM) | `enp0s8` (host-only) | `192.168.56.20` |
| Windows host | VirtualBox host adapter | `192.168.56.1` (auto) |

---

## 1. Create the host-only adapter

### Option A — VirtualBox GUI

1. Open **VirtualBox Manager → File → Host Network Manager** (or **Tools → Network**).
2. Click **Create** — VirtualBox adds an adapter (e.g. `VirtualBox Host-Only Ethernet
   Adapter #2`).
3. Select the new adapter → **Properties**:
   - **Adapter tab:** IPv4 Address `192.168.56.1`, Mask `255.255.255.0`.
   - **DHCP Server tab:** uncheck **Enable Server** — all IPs must be static.
4. Click **Apply**.

### Option B — PowerShell (VBoxManage)

```powershell
# Create the adapter; VBoxManage prints the assigned name
$adapterName = (VBoxManage hostonlyif create 2>&1 |
    Select-String "Interface '(.+)' was successfully created" |
    ForEach-Object { $_.Matches[0].Groups[1].Value })

Write-Host "Created: $adapterName"

# Set static IP — no DHCP
VBoxManage hostonlyif ipconfig $adapterName `
    --ip 192.168.56.1 --netmask 255.255.255.0

# Confirm DHCP is off
VBoxManage dhcpserver modify --ifname $adapterName --disable 2>$null
```

The adapter name may differ from machine to machine. Record it:

```powershell
VBoxManage list hostonlyifs | Select-String "Name:|IPAddress:"
```

> **Note:** ADR-0017 refers to this adapter as `vboxnet-smo`. Use the actual Windows
> adapter name (e.g. `VirtualBox Host-Only Ethernet Adapter #2`) in subsequent
> `VBoxManage modifyvm` calls; only the IP subnet matters, not the name string.

---

## 2. Attach the adapter to each VM

Replace `<adapter-name>` with the name recorded above.

```powershell
# smo-be-vm (backend) — nic2 = host-only
VBoxManage modifyvm smo-be-vm --nic2 hostonly `
    --hostonlyadapter2 "<adapter-name>"

# smo-os-vm (OS live image) — nic2 = host-only
VBoxManage modifyvm smo-os-vm --nic2 hostonly `
    --hostonlyadapter2 "<adapter-name>"
```

---

## 3. Windows Defender Firewall rule for port 8443

The backend listens on `192.168.56.20:8443`. To allow the Windows host to `curl` the
backend directly (useful for debugging), add an inbound rule:

```powershell
New-NetFirewallRule `
    -DisplayName "SMO backend HTTPS (vboxnet-smo)" `
    -Direction Inbound `
    -Protocol TCP `
    -LocalPort 8443 `
    -RemoteAddress 192.168.56.0/24 `
    -Action Allow `
    -Profile Any
```

Verify the rule exists:

```powershell
Get-NetFirewallRule -DisplayName "SMO backend HTTPS (vboxnet-smo)" |
    Select-Object DisplayName, Enabled, Action
```

Test from the Windows host (requires `curl.exe`, included in Windows 10 1803+):

```powershell
curl.exe --cacert "$env:USERPROFILE\smo-ca.crt" `
         https://192.168.56.20:8443/health
```

*(Copy `ca.crt` from `smo-be-vm:/etc/smo-backend/pki/ca.crt` to the Windows host first.)*

---

## 4. Verify guest-to-guest connectivity

From `smo-os-vm`:

```bash
ping -c 2 192.168.56.20   # should succeed
curl --cacert /etc/shikshan/backend-ca.crt https://192.168.56.20:8443/health
```

From `smo-be-vm`:

```bash
ping -c 2 192.168.56.10   # should succeed
```

---

## Common pitfalls

### 1. DHCP enabled on the host-only adapter

VirtualBox enables a DHCP server on new host-only adapters by default. If DHCP is on,
VMs may receive a random IP instead of your intended static address.

**Fix:** Disable the DHCP server in Host Network Manager (Adapter Properties → DHCP
Server tab → uncheck *Enable Server*), or run:

```powershell
VBoxManage dhcpserver modify --ifname "<adapter-name>" --disable
```

### 2. Promiscuous mode not set — guest-to-guest traffic dropped

By default VirtualBox sets promiscuous mode to **Deny**, which blocks packets where the
source MAC is not the VM's own MAC. For host-only adapters shared between two VMs this
causes guest-to-guest pings to fail silently.

**Fix:** Set promiscuous mode to *Allow VMs* on the host-only adapter in each VM's
**Network → Advanced** settings, or:

```powershell
VBoxManage modifyvm smo-be-vm  --nicpromisc2 allow-vms
VBoxManage modifyvm smo-os-vm  --nicpromisc2 allow-vms
```

### 3. Adapter attached but "cable unplugged" — interface has no carrier

VirtualBox can report the adapter as attached while the virtual cable is unplugged,
giving `ip link show enp0s8` a `state DOWN` even after `ifup`.

**Fix:** In the VM's **Network → Advanced** settings ensure **Cable Connected** is
checked, or:

```powershell
VBoxManage modifyvm smo-be-vm --cableconnected2 on
VBoxManage modifyvm smo-os-vm --cableconnected2 on
```

### 4. IP address in `/etc/shikshan/backend.yml` does not match the cert SAN

The server TLS certificate has `subjectAltName=IP:192.168.56.20` (see
[backend-vm-bootstrap.md](backend-vm-bootstrap.md) step 6). If the backend VM's
host-only IP drifts (e.g. DHCP re-assigns it, or you re-create the adapter), `curl`
will reject the cert with `SSL: no alternative certificate subject name matches`.

**Fix:** Keep the static IP at `192.168.56.20` and regenerate the cert if the IP ever
changes. The `backend.url` in `/etc/shikshan/backend.yml` and the cert SAN must always
match.

---

## Tear-down

To remove the host-only adapter:

```powershell
# First detach it from both VMs
VBoxManage modifyvm smo-be-vm --nic2 none
VBoxManage modifyvm smo-os-vm --nic2 none

# Then remove the host interface
VBoxManage hostonlyif remove "<adapter-name>"
```

Also delete the Windows Defender rule:

```powershell
Remove-NetFirewallRule -DisplayName "SMO backend HTTPS (vboxnet-smo)"
```
