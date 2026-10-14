<#
.SYNOPSIS
  CEO-GPT Remote-Windows: Windows-Host als immer-an Chassis haerten.
.DESCRIPTION
  Setzt die sicheren Always-on-Einstellungen: Schlaf / Festplatten-Schlaf / Ruhezustand aus,
  Fast-Startup aus, Hoechstleistungs-Plan, Windows-Update-Reboots zaehmen (kein Auto-Reboot bei
  angemeldetem Nutzer, weite aktive Stunden), Netzwerkkarte nicht abschalten.
  Faesst BIOS, Auto-Login und BitLocker NICHT an, das sind Handgriffe am Geraet (INSTALL Teil 1).
  Unterstuetzt -WhatIf fuer eine reine Vorschau.
.NOTES
  Als Administrator ausfuehren.
  Aufruf: powershell -ExecutionPolicy Bypass -File .\windows-host-harden.ps1 [-WhatIf]
#>

[CmdletBinding(SupportsShouldProcess = $true)]
param(
  [int]$ActiveHoursStart = 6,
  [int]$ActiveHoursEnd = 23
)

$id = [Security.Principal.WindowsIdentity]::GetCurrent()
$pr = New-Object Security.Principal.WindowsPrincipal($id)
if (-not $pr.IsInRole([Security.Principal.WindowsBuiltinRole]::Administrator)) {
  Write-Warning "Nicht als Administrator gestartet. Einige Schritte schlagen sonst fehl. Trotzdem fortfahren mit Vorsicht."
}

Write-Host "=== Schlaf / Ruhezustand / Fast-Startup ===" -ForegroundColor Cyan
if ($PSCmdlet.ShouldProcess("Energie-Einstellungen", "Schlaf/Festplatten-Schlaf/Ruhezustand am Netz aus, Fast-Startup aus")) {
  powercfg /change standby-timeout-ac 0
  powercfg /change disk-timeout-ac 0
  powercfg /change hibernate-timeout-ac 0
  powercfg /hibernate off           # deaktiviert auch Fast-Startup
  powercfg /setactive SCHEME_MIN    # Hoechstleistung
  Write-Host "  gesetzt: kein Schlaf am Strom, Ruhezustand und Fast-Startup aus, Hoechstleistung."
}

Write-Host "`n=== Netzwerkkarte wach halten ===" -ForegroundColor Cyan
if ($PSCmdlet.ShouldProcess("Netzwerkadapter", "Energiespar-Abschaltung deaktivieren")) {
  try {
    Get-NetAdapter -Physical -ErrorAction Stop | Where-Object { $_.Status -eq "Up" } | ForEach-Object {
      Set-NetAdapterPowerManagement -Name $_.Name -AllowComputerToTurnOffDevice Disabled -ErrorAction SilentlyContinue
      Write-Host "  $($_.Name): darf nicht mehr zum Energiesparen abgeschaltet werden."
    }
  } catch {
    Write-Host "  (NIC-Power nicht setzbar, im Geraete-Manager > Netzwerkadapter > Energieverwaltung manuell pruefen)"
  }
}

Write-Host "`n=== Windows-Update-Reboots zaehmen ===" -ForegroundColor Cyan
if ($PSCmdlet.ShouldProcess("Windows Update", "kein Auto-Reboot bei angemeldetem Nutzer, aktive Stunden setzen")) {
  $wu = "HKLM:\SOFTWARE\Policies\Microsoft\Windows\WindowsUpdate"
  $au = "$wu\AU"
  New-Item -Path $au -Force | Out-Null
  # mit Auto-Login ist immer ein Nutzer angemeldet -> kein unangekuendigter Reboot
  Set-ItemProperty -Path $au -Name NoAutoRebootWithLoggedOnUsers -Value 1 -Type DWord
  Set-ItemProperty -Path $wu -Name SetActiveHours -Value 1 -Type DWord
  Set-ItemProperty -Path $wu -Name ActiveHoursStart -Value $ActiveHoursStart -Type DWord
  Set-ItemProperty -Path $wu -Name ActiveHoursEnd -Value $ActiveHoursEnd -Type DWord
  Write-Host "  gesetzt: NoAutoRebootWithLoggedOnUsers=1, aktive Stunden $ActiveHoursStart-$ActiveHoursEnd Uhr."
  Write-Host "  Hinweis: Sicherheitspatches kommen weiter. Plane bei Bedarf einen eigenen Reboot (z.B. Wochenende)."
}

Write-Host "`n=== Bleibt Handarbeit am Geraet (siehe INSTALL Teil 1) ===" -ForegroundColor Yellow
Write-Host "  1. BIOS/UEFI: 'Restore on AC Power Loss' = Power On (Firmware, kein Windows-Schalter)."
Write-Host "  2. Auto-Login: Sysinternals Autologon (verschluesselt), eigenes Konto mit wenig Rechten."
Write-Host "  3. BitLocker: auf TPM-only lassen (nicht TPM+PIN), Wiederherstellungs-Schluessel extern sichern."
Write-Host "`nFertig. Mit -WhatIf laeuft alles nur als Vorschau, ohne etwas zu aendern."
