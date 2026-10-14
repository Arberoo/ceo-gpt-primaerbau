<#
.SYNOPSIS
  CEO-GPT Remote-Windows, Weg N: diesen PC als Haupt-PC und SSH-Ziel einrichten (PrimaerBau, 14.10.2026).
.DESCRIPTION
  1. OpenSSH-Server installieren, automatisch starten, SFTP sicherstellen, Firewall-Regel pruefen
  2. PC fuers Dauerlaufen haerten (ruft windows-host-harden.ps1 auf: kein Schlaf am Strom,
     kein Ruhezustand/Fast-Startup, Netzwerkkarte wach, keine Auto-Neustarts durch Windows Update)
  Faesst BIOS, Auto-Login und BitLocker NICHT an.
  Mit -WhatIf nur Vorschau.
.NOTES
  Als Administrator ausfuehren:
  powershell -ExecutionPolicy Bypass -File .\weg-n-einrichten.ps1 [-WhatIf]
#>
[CmdletBinding(SupportsShouldProcess = $true)]
param()

$pr = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
if (-not $pr.IsInRole([Security.Principal.WindowsBuiltinRole]::Administrator)) {
  Write-Host "Bitte PowerShell als Administrator starten (Rechtsklick > Als Administrator ausfuehren)." -ForegroundColor Red
  exit 1
}

Write-Host "=== 1. OpenSSH-Server ===" -ForegroundColor Cyan
$cap = Get-WindowsCapability -Online -Name "OpenSSH.Server*" | Select-Object -First 1
if ($cap.State -ne "Installed") {
  if ($PSCmdlet.ShouldProcess($cap.Name, "installieren")) {
    Add-WindowsCapability -Online -Name $cap.Name | Out-Null
    Write-Host "  OpenSSH-Server installiert."
  }
} else { Write-Host "  OpenSSH-Server ist schon installiert." }

if ($PSCmdlet.ShouldProcess("sshd", "automatisch starten und jetzt starten")) {
  Set-Service sshd -StartupType Automatic
  Start-Service sshd
  Write-Host "  sshd laeuft und startet automatisch."
}

$cfg = "$env:ProgramData\ssh\sshd_config"
if (Test-Path $cfg) {
  $aktiv = Get-Content $cfg | Where-Object { $_ -notmatch '^\s*#' }
  if (-not ($aktiv | Where-Object { $_ -match '^\s*Subsystem\s+sftp' })) {
    if ($PSCmdlet.ShouldProcess($cfg, "SFTP-Subsystem ergaenzen")) {
      Add-Content $cfg "`nSubsystem sftp sftp-server.exe"
      Restart-Service sshd
      Write-Host "  SFTP ergaenzt."
    }
  } else { Write-Host "  SFTP ist an." }
}

$fw = Get-NetFirewallRule -Name "OpenSSH-Server-In-TCP" -ErrorAction SilentlyContinue
if (-not $fw) {
  if ($PSCmdlet.ShouldProcess("Firewall", "Regel fuer SSH (Port 22) anlegen")) {
    New-NetFirewallRule -Name "OpenSSH-Server-In-TCP" -DisplayName "OpenSSH Server (sshd)" -Enabled True -Direction Inbound -Protocol TCP -Action Allow -LocalPort 22 | Out-Null
    Write-Host "  Firewall-Regel angelegt."
  }
} else { Write-Host "  Firewall-Regel vorhanden (aktiv: $($fw.Enabled))." }

Write-Host "`n=== 2. PC fuers Dauerlaufen haerten ===" -ForegroundColor Cyan
$harden = Join-Path $PSScriptRoot "windows-host-harden.ps1"
if ($WhatIfPreference) { & $harden -WhatIf } else { & $harden }

Write-Host "`nFertig. Jetzt Tailscale installieren und anmelden, dann windows-ssh-check.ps1 erneut laufen lassen." -ForegroundColor Green
