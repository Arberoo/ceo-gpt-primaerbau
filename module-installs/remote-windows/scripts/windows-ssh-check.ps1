<#
.SYNOPSIS
  CEO-GPT Remote-Windows (Weg N): prueft, ob dieser Windows-PC als SSH-Ziel
  fuer die Claude-Desktop-App taugt.

.DESCRIPTION
  Liest NUR, aendert nichts. Am WINDOWS-PC in PowerShell als Administrator ausfuehren.
  Prueft die Punkte, die die Claude-Desktop-App fuer eine SSH-Sitzung auf einem
  Windows-Rechner braucht:
    - OpenSSH-Server (sshd) laeuft und startet automatisch
    - SFTP-Subsystem ist eingeschaltet
    - MaxSessions ist nicht 1
    - Passwort-Anmeldung ist nicht abgeschaltet (oder es gibt Schluessel)
    - Standard-Shell ist cmd.exe oder PowerShell (nicht WSL-bash/Git Bash)
    - git ist vorhanden
    - genug freier Platz (> 1 GB) auf dem Laufwerk der Benutzerprofile
    - Tailscale ist installiert und verbunden

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File .\windows-ssh-check.ps1
#>

$ok = $true
function Gut($t)    { Write-Host "  [OK]   $t" -ForegroundColor Green }
function Warn($t)   { Write-Host "  [!]    $t" -ForegroundColor Yellow }
function Fehler($t) { Write-Host "  [FEHLT] $t" -ForegroundColor Red; $script:ok = $false }

Write-Host ""
Write-Host "CEO-GPT Remote-Windows: SSH-Ziel fuer Claude Desktop pruefen (liest nur)" -ForegroundColor Cyan
Write-Host ""

# Windows-Version
$os = Get-CimInstance Win32_OperatingSystem
Write-Host "Windows: $($os.Caption), Build $($os.BuildNumber)"
Write-Host ""

# 1. OpenSSH-Server
Write-Host "1. OpenSSH-Server"
$svc = Get-Service sshd -ErrorAction SilentlyContinue
if (-not $svc) {
    Fehler "sshd ist nicht installiert. Einstellungen > System > Optionale Features > OpenSSH-Server hinzufuegen."
} else {
    if ($svc.Status -eq 'Running') { Gut "sshd laeuft" } else { Fehler "sshd laeuft nicht (Start-Service sshd)" }
    if ($svc.StartType -eq 'Automatic') { Gut "sshd startet automatisch" } else { Fehler "sshd startet nicht automatisch (Set-Service sshd -StartupType Automatic)" }
}

# 2.-4. sshd_config
Write-Host "2. sshd_config"
$cfg = "$env:ProgramData\ssh\sshd_config"
if (Test-Path $cfg) {
    $zeilen = Get-Content $cfg | Where-Object { $_ -notmatch '^\s*#' -and $_.Trim() -ne '' }
    if ($zeilen | Where-Object { $_ -match '^\s*Subsystem\s+sftp' }) { Gut "SFTP-Subsystem ist an" }
    else { Fehler "SFTP-Subsystem fehlt. Zeile 'Subsystem sftp sftp-server.exe' ergaenzen, dann Restart-Service sshd" }

    $ms = $zeilen | Where-Object { $_ -match '^\s*MaxSessions\s+(\d+)' } | Select-Object -First 1
    if ($ms -and [int]($ms -replace '\D','') -le 1) { Fehler "MaxSessions steht auf 1. Die App braucht mehrere Sitzungen (Standard 10)." }
    else { Gut "MaxSessions ok (gesetzt: $(if ($ms) { $ms.Trim() } else { 'Standard 10' }))" }

    $pa = $zeilen | Where-Object { $_ -match '^\s*PasswordAuthentication\s+no' }
    if ($pa) { Warn "Passwort-Anmeldung ist aus. Dann braucht jedes Geraet einen Schluessel OHNE Passphrase (die App ueberspringt Schluessel mit Passphrase)." }
    else { Gut "Passwort-Anmeldung erlaubt (die App fragt selbst nach dem Passwort)" }
} else {
    Fehler "sshd_config nicht gefunden ($cfg)"
}

# 5. Standard-Shell
Write-Host "3. Standard-Shell"
$shell = (Get-ItemProperty HKLM:\SOFTWARE\OpenSSH -Name DefaultShell -ErrorAction SilentlyContinue).DefaultShell
if (-not $shell) { Gut "keine eigene Standard-Shell gesetzt, es gilt cmd.exe" }
elseif ($shell -match 'cmd\.exe|powershell\.exe|pwsh\.exe') { Gut "Standard-Shell: $shell" }
else { Fehler "Standard-Shell ist '$shell'. Fuer die Claude-App cmd.exe oder PowerShell nehmen (Eintrag entfernen oder auf PowerShell setzen)." }

# 6. git
Write-Host "4. git"
$git = Get-Command git -ErrorAction SilentlyContinue
if ($git) { Gut "git gefunden: $($git.Source)" } else { Fehler "git fehlt. Git for Windows systemweit installieren." }

# 7. Speicher
Write-Host "5. Speicherplatz"
$lw = ($env:SystemDrive).TrimEnd(':')
$frei = (Get-PSDrive $lw).Free
if ($frei -gt 1GB) { Gut ("{0:N1} GB frei auf {1}:" -f ($frei/1GB), $lw) } else { Fehler ("nur {0:N2} GB frei auf {1}: (gebraucht ca. 1 GB)" -f ($frei/1GB), $lw) }

# 8. Tailscale
Write-Host "6. Tailscale"
$ts = Get-Command tailscale -ErrorAction SilentlyContinue
if (-not $ts) { $ts = Get-Item "$env:ProgramFiles\Tailscale\tailscale.exe" -ErrorAction SilentlyContinue }
if ($ts) {
    $pfad = if ($ts.Source) { $ts.Source } else { $ts.FullName }
    $ip = & $pfad ip -4 2>$null
    if ($ip) { Gut "Tailscale verbunden, Adresse $ip" } else { Warn "Tailscale installiert, aber nicht verbunden (tailscale up / in der App anmelden)" }
} else {
    Warn "Tailscale nicht gefunden. Ohne Tailscale nur aus dem lokalen Netz erreichbar."
}

# Hinweis Admin-Konten
Write-Host ""
Write-Host "Hinweis: Ist das Anmeldekonto lokaler Administrator, liest Windows-OpenSSH Schluessel"
Write-Host "NICHT aus dem Benutzerordner, sondern aus $env:ProgramData\ssh\administrators_authorized_keys."
Write-Host ""

if ($ok) { Write-Host "Ergebnis: Dieser PC taugt als SSH-Ziel fuer die Claude-Desktop-App." -ForegroundColor Green }
else { Write-Host "Ergebnis: Erst die rot markierten Punkte beheben, dann erneut pruefen." -ForegroundColor Red }
