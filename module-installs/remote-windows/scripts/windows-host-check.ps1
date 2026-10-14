<#
.SYNOPSIS
  CEO-GPT Remote-Windows: Host-Bereitschaft pruefen (read-only).
.DESCRIPTION
  Liest Windows-Edition, RAM, CPU-Virtualisierung / Hyper-V-Faehigkeit, Hyper-V-Feature-Status,
  BitLocker-Modus und Fast-Startup-Stand. Aendert nichts. Gibt am Ende ein klares Urteil:
  Hauptweg (Hyper-V-VM) moeglich, oder Home-Fallback noetig.
.NOTES
  Als Administrator ausfuehren fuer vollstaendige Angaben (BitLocker, Hyper-V-Feature).
  Aufruf: powershell -ExecutionPolicy Bypass -File .\windows-host-check.ps1
#>

[CmdletBinding()]
param()

function Write-Head($t) { Write-Host "`n=== $t ===" -ForegroundColor Cyan }

$reasons = @()

Write-Head "Windows"
$os = Get-CimInstance Win32_OperatingSystem
$caption = $os.Caption
Write-Host "  Edition : $caption"
$isPro = $caption -match "Pro|Enterprise|Education"
if (-not $isPro) {
  $reasons += "Edition ist nicht Pro/Enterprise/Education -> Hyper-V nicht verfuegbar (Home-Fallback noetig)."
}

Write-Head "Speicher"
$cs = Get-CimInstance Win32_ComputerSystem
$ramGB = [math]::Round($cs.TotalPhysicalMemory / 1GB, 1)
Write-Host "  RAM     : $ramGB GB"
if ($ramGB -lt 6) {
  $reasons += "Wenig RAM ($ramGB GB). Fuer Host + 2-GB-VM mind. 8 GB empfohlen."
}

Write-Head "Virtualisierung / Hyper-V-Faehigkeit"
$ci = Get-ComputerInfo -Property "HyperV*" -ErrorAction SilentlyContinue
$slat   = $ci.HyperVRequirementSecondLevelAddressTranslation
$virtFw = $ci.HyperVRequirementVirtualizationFirmwareEnabled
$vmMon  = $ci.HyperVRequirementVMMonitorModeExtensions
$dep    = $ci.HyperVRequirementDataExecutionPrevention
$hvOn   = $ci.HyperVisorPresent
Write-Host "  Hypervisor laeuft bereits : $hvOn  (wenn ja, sind die Requirement-Felder leer, das ist ok)"
Write-Host "  SLAT                      : $slat"
Write-Host "  Virtualisierung im BIOS   : $virtFw"
Write-Host "  VM-Monitor-Extensions     : $vmMon"
Write-Host "  DEP                       : $dep"
if ($virtFw -eq $false) {
  $reasons += "Virtualisierung im BIOS aus. Intel VT-x / AMD-V (oft 'SVM Mode') einschalten."
}

Write-Head "Hyper-V-Feature-Status"
try {
  $feat = Get-WindowsOptionalFeature -Online -FeatureName Microsoft-Hyper-V-All -ErrorAction Stop
  Write-Host "  Microsoft-Hyper-V-All : $($feat.State)  (Disabled = noch einschalten in Teil 2)"
} catch {
  Write-Host "  (Status nicht lesbar: nicht als Administrator gestartet oder Edition ohne Hyper-V)"
}

Write-Head "BitLocker (Systemlaufwerk)"
try {
  $bl = Get-BitLockerVolume -MountPoint $env:SystemDrive -ErrorAction Stop
  Write-Host "  Schutz   : $($bl.ProtectionStatus)"
  $prot = ($bl.KeyProtector | ForEach-Object { $_.KeyProtectorType }) -join ", "
  Write-Host "  Methoden : $prot"
  if ($prot -match "Pin") {
    $reasons += "BitLocker nutzt eine PIN (TPM+PIN). Auf TPM-only stellen, sonst kommt der PC nicht unbeaufsichtigt hoch."
  }
} catch {
  Write-Host "  (BitLocker-Status nicht lesbar: nicht als Administrator, oder BitLocker nicht aktiv)"
}

Write-Head "Fast-Startup"
$hb = (Get-ItemProperty "HKLM:\SYSTEM\CurrentControlSet\Control\Session Manager\Power" -Name HiberbootEnabled -ErrorAction SilentlyContinue).HiberbootEnabled
Write-Host "  Fast-Startup aktiv : $([bool]$hb)  (sollte aus sein, erledigt windows-host-harden.ps1)"

Write-Head "Urteil"
$hyperv = $isPro -and ($virtFw -ne $false)
if ($hyperv) {
  Write-Host "  [OK]  Hauptweg moeglich: Hyper-V-VM. Weiter mit Teil 1 (Host haerten)." -ForegroundColor Green
} else {
  Write-Host "  [!!]  Hauptweg (Hyper-V) nicht direkt moeglich, siehe Punkte." -ForegroundColor Yellow
}
if ($reasons.Count -gt 0) {
  Write-Host "  Punkte zum Klaeren:"
  $reasons | ForEach-Object { Write-Host "   - $_" }
  if (-not $isPro) {
    Write-Host "   Home-Fallback: auf Pro upgraden (empfohlen), oder VirtualBox + VBoxVmService, oder WSL2 mit Babysitting."
  }
}
