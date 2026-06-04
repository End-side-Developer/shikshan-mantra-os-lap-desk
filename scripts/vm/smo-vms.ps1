#requires -Version 5.1
<#
.SYNOPSIS
    Create-or-reuse the two Shikshan Mantra OS VirtualBox VMs and boot the latest ISO.

.DESCRIPTION
    Idempotent VM lifecycle automation for the topology locked by ADR-0017:

        smo-os-vm   192.168.56.10   live-boots the latest releases/*.iso (ephemeral)
        smo-be-vm   192.168.56.20   persistent Debian content backend (FastAPI /health)

    Both VMs are kept SEPARATE and share one host-only adapter (192.168.56.0/24).
    The in-guest static IPs (.10 / .20) are configured inside each guest per the
    runbooks; this script only manages the VM shells, NICs, and media.

    "up" (default) ensures each VM exists, attaches the newest ISO to the OS VM,
    and starts them (OS = GUI so you can use the desktop app; backend = headless).
    Re-run after every build-iso.sh to refresh the OS VM with the latest image.

.PARAMETER Target
    os | backend | both (default: both)

.PARAMETER Action
    up | status | stop (default: up)

.PARAMETER Iso
    Explicit ISO path for the OS VM. Default: newest releases/shikshan-mantra-os-*.iso.

.PARAMETER NoStart
    Prepare/attach only; do not start the VM(s).

.EXAMPLE
    .\scripts\vm\smo-vms.ps1                 # ensure both, attach latest ISO, boot
    .\scripts\vm\smo-vms.ps1 -Target os      # only the OS VM
    .\scripts\vm\smo-vms.ps1 -Action status  # show VM + network state
    .\scripts\vm\smo-vms.ps1 -Target os -NoStart   # set latest ISO without booting
#>
[CmdletBinding()]
param(
    [ValidateSet('os', 'backend', 'both')] [string]$Target = 'both',
    [ValidateSet('up', 'status', 'stop')]  [string]$Action = 'up',
    [string]$Iso,
    [switch]$NoStart,
    [int]$OsMemoryMB = 2048,
    [int]$BackendMemoryMB = 2048
)

$ErrorActionPreference = 'Stop'

# ---- ADR-0017 topology constants --------------------------------------------
$OS_VM        = 'smo-os-vm'
$BE_VM        = 'smo-be-vm'
$HOST_ONLY_IP = '192.168.56.1'
$NETMASK      = '255.255.255.0'
$NETINST_ISO  = 'C:\ISOs\debian-13-netinst-amd64.iso'   # backend installer (manual)

# ---- VBoxManage discovery ---------------------------------------------------
function Resolve-VBoxManage {
    $cands = @()
    if ($env:VBOX_MSI_INSTALL_PATH) { $cands += (Join-Path $env:VBOX_MSI_INSTALL_PATH 'VBoxManage.exe') }
    $cands += 'D:\Oracle\VirtualBox\VBoxManage.exe'
    $cands += 'C:\Program Files\Oracle\VirtualBox\VBoxManage.exe'
    foreach ($c in $cands) { if ($c -and (Test-Path $c)) { return $c } }
    $cmd = Get-Command VBoxManage -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }
    throw 'VBoxManage.exe not found. Install VirtualBox or set $env:VBOX_MSI_INSTALL_PATH.'
}

$script:Vbox = Resolve-VBoxManage
$script:RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path

# ---- helpers ----------------------------------------------------------------
function VBox { & $script:Vbox @args }

function Test-VmExists  { param($Name) [bool]((VBox list vms)        -match ('"' + [regex]::Escape($Name) + '"')) }
function Test-VmRunning { param($Name) [bool]((VBox list runningvms) -match ('"' + [regex]::Escape($Name) + '"')) }

function Get-VmState {
    param($Name)
    if (-not (Test-VmExists $Name)) { return 'absent' }
    $m = VBox showvminfo $Name --machinereadable | Select-String '^VMState='
    if ($m) { return ((($m | Select-Object -First 1) -split '=')[1].Trim('"')) }
    return 'unknown'
}

# Force a VM to powered-off so modifyvm / storageattach can run. Used for the
# ephemeral OS VM only; the backend's saved state is never discarded implicitly.
function Ensure-PoweredOff {
    param($Name)
    $state = Get-VmState $Name
    if ($state -eq 'running' -or $state -eq 'paused') {
        Write-Host "[$Name] powering off (was $state)"
        try { VBox controlvm $Name poweroff } catch { }
        Start-Sleep -Seconds 2
    }
    elseif ($state -eq 'saved' -or $state -eq 'aborted-saved') {
        Write-Host "[$Name] discarding saved state (was $state)"
        try { VBox discardstate $Name } catch { }
    }
}

function Get-LatestIso {
    $rel = Join-Path $script:RepoRoot 'releases'
    $found = Get-ChildItem -Path $rel -Filter 'shikshan-mantra-os-*.iso' -ErrorAction SilentlyContinue |
        Sort-Object LastWriteTime -Descending | Select-Object -First 1
    if ($found) { return $found.FullName }
    return $null
}

function Get-HostOnlyAdapterName {
    $name = $null
    foreach ($l in (VBox list hostonlyifs)) {
        if     ($l -match '^Name:\s+(.+?)\s*$')      { $name = $Matches[1] }
        elseif ($l -match '^IPAddress:\s+([0-9.]+)') { if ($Matches[1] -eq $HOST_ONLY_IP) { return $name } }
    }
    return $null
}

function Ensure-HostOnlyAdapter {
    $name = Get-HostOnlyAdapterName
    if ($name) { Write-Host "[net] reuse host-only adapter '$name' ($HOST_ONLY_IP)"; return $name }
    Write-Host '[net] creating host-only adapter'
    $created = VBox hostonlyif create
    $m = $created | Select-String "Interface '(.+)' was successfully created"
    if (-not $m) { throw 'failed to create host-only adapter' }
    $name = $m.Matches[0].Groups[1].Value
    VBox hostonlyif ipconfig $name --ip $HOST_ONLY_IP --netmask $NETMASK
    try { VBox dhcpserver modify --ifname $name --disable } catch { }
    Write-Host "[net] created '$name' ($HOST_ONLY_IP), DHCP disabled"
    return $name
}

function Test-HasController { param($Name, $Ctl) [bool]((VBox showvminfo $Name --machinereadable) -match ('^storagecontrollername\d+="' + $Ctl + '"')) }

# ---- OS VM: live-boots the latest ISO (ephemeral, no disk) -------------------
function Ensure-OsVm {
    param($Adapter, $IsoPath)
    if (-not (Test-VmExists $OS_VM)) {
        Write-Host "[os] creating $OS_VM"
        VBox createvm --name $OS_VM --ostype Debian_64 --register | Out-Null
    }
    else {
        Write-Host "[os] reuse $OS_VM"
    }
    Ensure-PoweredOff $OS_VM
    VBox modifyvm $OS_VM --memory $OsMemoryMB --cpus 2 --vram 32 `
        --boot1 dvd --boot2 disk --boot3 none --boot4 none `
        --graphicscontroller vmsvga --firmware bios
    VBox modifyvm $OS_VM --nic1 nat
    VBox modifyvm $OS_VM --nic2 hostonly --hostonlyadapter2 $Adapter `
        --nicpromisc2 allow-vms --cableconnected2 on
    if (-not (Test-HasController $OS_VM 'IDE')) { VBox storagectl $OS_VM --name IDE --add ide }
    Write-Host "[os] attaching ISO: $(Split-Path $IsoPath -Leaf)"
    VBox storageattach $OS_VM --storagectl IDE --port 0 --device 0 --type dvddrive --medium $IsoPath
}

# ---- Backend VM: persistent Debian server (create shell or reuse) -----------
function Ensure-BackendVm {
    param($Adapter)
    if (-not (Test-VmExists $BE_VM)) {
        Write-Host "[be] creating $BE_VM (fresh - Debian install is manual)"
        VBox createvm --name $BE_VM --ostype Debian_64 --register | Out-Null
        VBox modifyvm $BE_VM --memory $BackendMemoryMB --cpus 2 --vram 16 `
            --boot1 dvd --boot2 disk --boot3 none --firmware bios
        $vdi = Join-Path $env:USERPROFILE "VirtualBox VMs\$BE_VM\$BE_VM.vdi"
        if (-not (Test-Path $vdi)) {
            VBox createmedium disk --filename $vdi --size 20480 --format VDI --variant Standard | Out-Null
        }
        if (-not (Test-HasController $BE_VM 'SATA')) { VBox storagectl $BE_VM --name SATA --add sata --controller IntelAhci }
        VBox storageattach $BE_VM --storagectl SATA --port 0 --device 0 --type hdd --medium $vdi
        VBox modifyvm $BE_VM --nic1 nat   # transient NAT for apt during install
        if (Test-Path $NETINST_ISO) {
            if (-not (Test-HasController $BE_VM 'IDE')) { VBox storagectl $BE_VM --name IDE --add ide }
            VBox storageattach $BE_VM --storagectl IDE --port 0 --device 0 --type dvddrive --medium $NETINST_ISO
            Write-Host '[be] Debian netinst attached - start the VM and follow backend-vm-bootstrap.md'
        }
        else {
            Write-Warning "[be] no Debian netinst at $NETINST_ISO; download it then follow docs/runbooks/backend-vm-bootstrap.md"
        }
        return
    }
    # Reuse path: the backend is provisioned. Only refresh the host-only NIC when
    # it is genuinely powered off (modifyvm fails on running/saved). Never discard
    # the saved server state and never touch nic1 (the connectivity test may have
    # disabled NAT) or the disk.
    $state = Get-VmState $BE_VM
    if ($state -eq 'poweroff') {
        Write-Host "[be] reuse $BE_VM (poweroff) - refreshing host-only NIC"
        VBox modifyvm $BE_VM --nic2 hostonly --hostonlyadapter2 $Adapter `
            --nicpromisc2 allow-vms --cableconnected2 on
    }
    else {
        Write-Host "[be] reuse $BE_VM (state=$state) - leaving config as provisioned"
    }
}

function Start-SmoVm {
    param($Name, $Type = 'gui')
    if (Test-VmRunning $Name) { Write-Host "[start] $Name already running"; return }
    Write-Host "[start] $Name ($Type)"
    VBox startvm $Name --type $Type
}

function Stop-SmoVm {
    param($Name)
    if (Test-VmRunning $Name) { Write-Host "[stop] $Name"; VBox controlvm $Name acpipowerbutton }
    else { Write-Host "[stop] $Name not running" }
}

function Show-Status {
    Write-Host '=== host-only adapter ==='
    VBox list hostonlyifs | Select-String '^Name:|IPAddress:|DHCP'
    Write-Host ''
    Write-Host '=== VMs ==='
    foreach ($n in @($OS_VM, $BE_VM)) {
        if (Test-VmExists $n) {
            $state = ((VBox showvminfo $n --machinereadable | Select-String '^VMState=') -split '=')[1].Trim('"')
            $dvd = (VBox showvminfo $n --machinereadable | Select-String '\.iso"$' | Select-Object -First 1)
            Write-Host ("  {0,-10} state={1}" -f $n, $state)
            if ($dvd) { Write-Host "             $dvd" }
        }
        else {
            Write-Host ("  {0,-10} (absent)" -f $n)
        }
    }
    $iso = Get-LatestIso
    Write-Host ''
    if ($iso) { Write-Host "latest ISO: $(Split-Path $iso -Leaf)" } else { Write-Host 'latest ISO: (none in releases/)' }
}

# ---- main -------------------------------------------------------------------
Write-Host "VBoxManage: $script:Vbox"
Write-Host "repo root : $script:RepoRoot"
Write-Host ''

switch ($Action) {
    'status' { Show-Status; return }
    'stop' {
        if ($Target -in @('os', 'both'))      { Stop-SmoVm $OS_VM }
        if ($Target -in @('backend', 'both')) { Stop-SmoVm $BE_VM }
        return
    }
    'up' {
        $adapter = Ensure-HostOnlyAdapter
        if ($Target -in @('os', 'both')) {
            if (-not $Iso) { $Iso = Get-LatestIso }
            if (-not $Iso) { throw 'no ISO in releases/ - run scripts/build/build-iso.sh first' }
            Ensure-OsVm -Adapter $adapter -IsoPath $Iso
            if (-not $NoStart) { Start-SmoVm -Name $OS_VM -Type 'gui' }
        }
        if ($Target -in @('backend', 'both')) {
            Ensure-BackendVm -Adapter $adapter
            if (-not $NoStart) { Start-SmoVm -Name $BE_VM -Type 'headless' }
        }
        Write-Host ''
        Write-Host '[done] use -Action status to inspect, -Action stop to power off.'
    }
}
