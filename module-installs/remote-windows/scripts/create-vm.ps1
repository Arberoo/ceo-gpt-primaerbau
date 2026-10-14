<#
.SYNOPSIS
  CEO-GPT Remote-Windows: Hyper-V-Ubuntu-VM anlegen (immer-an).
.DESCRIPTION
  Legt eine Generation-2-VM an, setzt das Linux-Secure-Boot-Template, haengt die Ubuntu-ISO ein
  und stellt Auto-Start beim Boot plus sauberes Herunterfahren ein. Statischer RAM (stabiler Server),
  dynamische Festplatte. Unterstuetzt -WhatIf.
.NOTES
  Als Administrator ausfuehren. Hyper-V muss aktiviert sein
  (Enable-WindowsOptionalFeature -Online -FeatureName Microsoft-Hyper-V-All -All, dann Neustart).
  Aufruf: powershell -ExecutionPolicy Bypass -File .\create-vm.ps1 -VMName "CEO-GPT" -IsoPath "C:\pfad\ubuntu.iso"
#>

[CmdletBinding(SupportsShouldProcess = $true)]
param(
  [string]$VMName = "CEO-GPT",
  [int]$MemoryGB = 2,
  [int]$CpuCount = 2,
  [int]$DiskGB = 40,
  [string]$IsoPath,
  [string]$SwitchName = "Default Switch",
  [string]$VMPath
)

if (-not (Get-Command Get-VM -ErrorAction SilentlyContinue)) {
  Write-Error "Hyper-V-Cmdlets nicht gefunden. Hyper-V aktiviert und neu gestartet?"
  return
}
if (Get-VM -Name $VMName -ErrorAction SilentlyContinue) {
  Write-Error "Es gibt schon eine VM namens '$VMName'. Anderen Namen waehlen oder die alte entfernen."
  return
}
if (-not (Get-VMSwitch -Name $SwitchName -ErrorAction SilentlyContinue)) {
  Write-Warning "Switch '$SwitchName' nicht gefunden. Vorhandene Switches:"
  Get-VMSwitch | Select-Object Name, SwitchType | Format-Table | Out-Host
  Write-Warning "Mit -SwitchName einen vorhandenen Switch angeben (oft 'Default Switch')."
  return
}
if ($IsoPath -and -not (Test-Path $IsoPath)) {
  Write-Error "ISO nicht gefunden: $IsoPath"
  return
}

if (-not $VMPath) {
  $root = (Get-VMHost).VirtualMachinePath
  if (-not $root) { $root = "C:\Hyper-V" }
  $VMPath = Join-Path $root $VMName
}
$vhdDir  = Join-Path $VMPath "Virtual Hard Disks"
$vhdPath = Join-Path $vhdDir "$VMName.vhdx"
$mem  = $MemoryGB * 1GB
$disk = $DiskGB * 1GB

Write-Host "Plan:" -ForegroundColor Cyan
Write-Host "  Name   : $VMName"
Write-Host "  RAM    : $MemoryGB GB (statisch) | CPU: $CpuCount | Platte: $DiskGB GB (dynamisch)"
Write-Host "  Pfad   : $VMPath"
Write-Host "  Switch : $SwitchName"
Write-Host "  ISO    : $(if ($IsoPath) { $IsoPath } else { '(keine, spaeter einhaengen)' })"

if ($PSCmdlet.ShouldProcess($VMName, "Hyper-V-VM anlegen und auf immer-an stellen")) {
  New-Item -ItemType Directory -Path $vhdDir -Force | Out-Null
  New-VHD -Path $vhdPath -SizeBytes $disk -Dynamic | Out-Null
  New-VM -Name $VMName -MemoryStartupBytes $mem -Generation 2 -VHDPath $vhdPath -SwitchName $SwitchName -Path $VMPath | Out-Null
  Set-VMProcessor -VMName $VMName -Count $CpuCount
  Set-VMMemory -VMName $VMName -DynamicMemoryEnabled $false -StartupBytes $mem
  # Linux-Secure-Boot-Template, sonst bootet Ubuntu nicht
  Set-VMFirmware -VMName $VMName -SecureBootTemplate MicrosoftUEFICertificateAuthority
  # immer-an: beim Host-Boot automatisch starten (mit kleiner Verzoegerung), beim Host-Stopp sauber herunterfahren
  Set-VM -Name $VMName -AutomaticStartAction Start -AutomaticStartDelay 10 -AutomaticStopAction ShutDown
  if ($IsoPath) {
    Add-VMDvdDrive -VMName $VMName -Path $IsoPath
    $dvd = Get-VMDvdDrive -VMName $VMName
    Set-VMFirmware -VMName $VMName -FirstBootDevice $dvd
  }
  Write-Host "`nVM '$VMName' angelegt und auf immer-an gestellt." -ForegroundColor Green
  Write-Host "Naechste Schritte:"
  Write-Host "  1. Hyper-V-Manager oeffnen, VM '$VMName' starten und verbinden (Doppelklick)."
  Write-Host "  2. Ubuntu installieren. WICHTIG: OpenSSH-Server mit anhaken."
  Write-Host "  3. Nach der Installation die ISO aushaengen:"
  Write-Host "       Get-VMDvdDrive -VMName '$VMName' | Set-VMDvdDrive -Path `$null"
  Write-Host "  4. Weiter mit INSTALL Teil 3 (Tailscale in der VM)."
}
