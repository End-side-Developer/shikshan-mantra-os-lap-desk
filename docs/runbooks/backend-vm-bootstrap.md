# Runbook — Provision smo-be-vm (Backend VM)

Walks from "I have VirtualBox installed on Windows" to "running `smo-be-vm` with
Python 3, FastAPI, an unprivileged `smo-be` user, and a dev CA + server cert for HTTPS."

**Related:** [virtualbox-host-only-network.md](virtualbox-host-only-network.md) (set up
the `vboxnet-smo` adapter first — that runbook must be completed before step 3 here).

**ADR:** [ADR-0017](../adr/0017-content-backend-architecture.md)

---

## Prerequisites

- VirtualBox 7.x installed on the Windows host.
- `vboxnet-smo` host-only adapter created at `192.168.56.0/24`
  (see [virtualbox-host-only-network.md](virtualbox-host-only-network.md)).
- Debian 13 "trixie" netinst ISO downloaded to `C:\ISOs\debian-13-netinst-amd64.iso`
  (or adjust the path in step 2).
- ~20 GB free disk space.

---

## 1. Create the VM

Open **VirtualBox Manager → Machine → New**, or run in PowerShell:

```powershell
VBoxManage createvm --name smo-be-vm --ostype Debian_64 --register

VBoxManage modifyvm smo-be-vm `
    --memory 2048 --cpus 2 --vram 16 `
    --boot1 dvd --boot2 disk --boot3 none `
    --audio none --usb off

# 20 GB thin-provisioned disk
VBoxManage createmedium disk `
    --filename "$env:USERPROFILE\VirtualBox VMs\smo-be-vm\smo-be-vm.vdi" `
    --size 20480 --format VDI --variant Standard

VBoxManage storagectl smo-be-vm --name SATA --add sata --controller IntelAhci
VBoxManage storageattach smo-be-vm --storagectl SATA --port 0 --device 0 `
    --type hdd `
    --medium "$env:USERPROFILE\VirtualBox VMs\smo-be-vm\smo-be-vm.vdi"

# Transient NAT (for apt during provisioning — will be disabled after)
VBoxManage modifyvm smo-be-vm --nic1 nat

# Host-only adapter (permanent — used for OS ↔ backend traffic)
VBoxManage modifyvm smo-be-vm --nic2 hostonly --hostonlyadapter2 vboxnet-smo
```

---

## 2. Attach the Debian netinst ISO

```powershell
VBoxManage storagectl smo-be-vm --name IDE --add ide
VBoxManage storageattach smo-be-vm --storagectl IDE --port 0 --device 0 `
    --type dvddrive --medium "C:\ISOs\debian-13-netinst-amd64.iso"
```

---

## 3. Install Debian 13 (netinst)

Start the VM and complete a minimal Debian installation:

```powershell
VBoxManage startvm smo-be-vm
```

Installer choices (accept defaults unless listed):

| Screen | Value |
|---|---|
| Hostname | `smo-be-vm` |
| Domain | *(leave blank)* |
| Root password | Set a strong password; note it for step 5 |
| Full name / username | `smo-be` |
| User password | Set a strong password |
| Partition | Guided — use entire disk, all files in one partition |
| Software selection | Uncheck "Debian desktop"; keep **SSH server** + **standard system utilities** |
| Grub on MBR | Yes — install to `/dev/sda` |

When the installer reboots, log in as root or `smo-be`.

---

## 4. Configure network interfaces

After first boot, configure the host-only interface with a static IP. Log in as root:

```bash
# Identify the host-only interface (usually enp0s8 — verify with: ip link show)
IFACE=enp0s8

cat >> /etc/network/interfaces <<EOF

auto ${IFACE}
iface ${IFACE} inet static
    address 192.168.56.20
    netmask 255.255.255.0
EOF

ifup ${IFACE}
ip addr show ${IFACE}   # should show 192.168.56.20
```

Verify the NAT interface (`enp0s3`) is up and the VM can reach the internet:

```bash
ping -c 2 deb.debian.org
```

---

## 5. Install Python 3 and dependencies

```bash
apt update
apt install -y python3 python3-pip python3-venv openssl
```

Create the application directory owned by `smo-be`:

```bash
install -d -m 755 -o smo-be -g smo-be /opt/smo-backend
```

As `smo-be` (or via `su - smo-be`):

```bash
python3 -m venv /opt/smo-backend/.venv
/opt/smo-backend/.venv/bin/pip install --upgrade pip
/opt/smo-backend/.venv/bin/pip install fastapi uvicorn[standard]
```

---

## 6. Generate the dev CA and server certificate

Run as root. All files land in `/etc/smo-backend/pki/`.

```bash
install -d -m 700 /etc/smo-backend/pki
cd /etc/smo-backend/pki

# 1. Dev CA (valid 10 years — development only, never expose private key)
openssl genrsa -out ca.key 4096
openssl req -x509 -new -nodes -key ca.key -sha256 -days 3650 \
    -subj "/CN=SMO-Dev-CA/O=Shikshan Mantra OS Dev" \
    -out ca.crt

# 2. Server key and CSR
openssl genrsa -out server.key 2048
openssl req -new -key server.key \
    -subj "/CN=smo-be-vm/O=Shikshan Mantra OS Dev" \
    -out server.csr

# 3. Extension file — SAN must include the host-only IP
cat > server.ext <<'EXTEOF'
[SAN]
subjectAltName = IP:192.168.56.20
EXTEOF

# 4. Sign the server cert (valid ~2 years)
openssl x509 -req -in server.csr \
    -CA ca.crt -CAkey ca.key -CAcreateserial \
    -out server.crt -days 825 \
    -extfile server.ext -extensions SAN

# Verify SAN is present
openssl x509 -noout -ext subjectAltName -in server.crt

# Lock down key files
chmod 600 ca.key server.key
chown root:root ca.key server.key ca.crt server.crt
```

Expected output of the `openssl x509` verify step:

```text
X509v3 Subject Alternative Name:
    IP Address:192.168.56.20
```

---

## 7. Copy CA cert to the OS VM

The OS VM needs the CA cert at `/etc/shikshan/backend-ca.crt` (referenced in
`/etc/shikshan/backend.yml`). Transfer it from the backend VM:

```bash
# From the backend VM — print the CA cert
cat /etc/smo-backend/pki/ca.crt
```

Then on the OS VM (or on the Windows host via SCP if SSH is available):

```bash
# On the OS VM as root
scp smo-be@192.168.56.20:/etc/smo-backend/pki/ca.crt /etc/shikshan/backend-ca.crt
chmod 644 /etc/shikshan/backend-ca.crt
```

---

## 8. Disable NAT after provisioning

Once all packages are installed, disable the transient NAT adapter so the
E2E connectivity test (SMO-0705) proves the host-only path only:

```powershell
# From the Windows host (VM must be powered off or use --running to hot-remove)
VBoxManage controlvm smo-be-vm poweroff
VBoxManage modifyvm smo-be-vm --nic1 none
VBoxManage startvm smo-be-vm
```

After re-boot, confirm only the host-only interface is active:

```bash
ip route show   # should show 192.168.56.0/24 only — no default route
```

---

## 9. Smoke-check

From the OS VM (after SMO-0703 backend skeleton is installed):

```bash
curl --cacert /etc/shikshan/backend-ca.crt \
     https://192.168.56.20:8443/health
# Expected: {"status":"ok","version":"0.1.0"}
```

---

## Tear-down and rebuild from scratch

To completely remove `smo-be-vm` and start over:

```powershell
# Power off if running
VBoxManage controlvm smo-be-vm poweroff 2>$null

# Unregister and delete all VM files
VBoxManage unregistervm smo-be-vm --delete
```

Verify it is gone:

```powershell
VBoxManage list vms | Select-String smo-be-vm
# Should produce no output
```

Then repeat from step 1.

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `enp0s8` not shown after boot | Interface not brought up | `ifup enp0s8` as root |
| `ping 192.168.56.10` fails | OS VM not on host-only net yet | Complete SMO-0702 first |
| `openssl x509 -req` exits non-zero | Extension file syntax error | Re-check `server.ext` — no trailing spaces after `IP:` |
| curl returns `SSL certificate problem` | Wrong CA cert or wrong IP in SAN | Regenerate cert; confirm `subjectAltName` shows `192.168.56.20` |
| `pip install` fails (no network) | NAT disabled too early | Re-attach NAT (`VBoxManage modifyvm smo-be-vm --nic1 nat`), reboot, install |
