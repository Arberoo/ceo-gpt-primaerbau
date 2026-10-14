# Richtet den Mail-Sofort-Abruf (IMAP IDLE) in der Windows-Aufgabenplanung ein
# und stellt den bisherigen 15-Minuten-Abruf auf einen stuendlichen Sicherheitsabgleich um.
# Aufruf:   powershell -ExecutionPolicy Bypass -File scripts\intel\setup_imap_idle_windows.ps1
# Entfernen: ... -File scripts\intel\setup_imap_idle_windows.ps1 -Entfernen   (Abruf geht zurueck auf 15 Min.)

param([switch]$Entfernen)

$Name   = "CEO-GPT PrimaerBau Mail-Sofort"
$Abruf  = "CEO-GPT PrimaerBau Mail-Abruf"
$Repo   = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$pyw    = Join-Path $Repo ".venv\Scripts\pythonw.exe"

function Set-Abruf([int]$Minuten, [string]$Text) {
    $t = Get-ScheduledTask -TaskName $Abruf -ErrorAction SilentlyContinue
    if (-not $t) { Write-Host "Aufgabe '$Abruf' nicht gefunden, uebersprungen." -ForegroundColor Yellow; return }
    $trigger = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(2) -RepetitionInterval (New-TimeSpan -Minutes $Minuten)
    Set-ScheduledTask -TaskName $Abruf -Trigger $trigger | Out-Null
    $t = Get-ScheduledTask -TaskName $Abruf
    $t.Description = $Text
    $t | Set-ScheduledTask | Out-Null
}

if ($Entfernen) {
    Stop-ScheduledTask -TaskName $Name -ErrorAction SilentlyContinue
    Unregister-ScheduledTask -TaskName $Name -Confirm:$false -ErrorAction SilentlyContinue
    Set-Abruf 15 "Holt neue Mails der PrimaerBau-Postfaecher (HostedOffice, IMAP) alle 15 Min. in data/data.db."
    Write-Host "Mail-Sofort-Abruf entfernt, Mail-Abruf wieder alle 15 Minuten."
    exit 0
}

if (-not (Test-Path $pyw)) { Write-Host "pythonw.exe in .venv nicht gefunden." -ForegroundColor Yellow; exit 1 }

$action   = New-ScheduledTaskAction -Execute $pyw -Argument "-X utf8 `"$Repo\scripts\intel\idle_imap.py`"" -WorkingDirectory $Repo
$trigger  = New-ScheduledTaskTrigger -AtLogOn -User "$env:USERDOMAIN\$env:USERNAME"
# Dauerlaeufer: kein Zeitlimit, bei Absturz jede Minute neu starten, nie doppelt
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
            -ExecutionTimeLimit (New-TimeSpan -Seconds 0) -RestartCount 999 -RestartInterval (New-TimeSpan -Minutes 1) `
            -MultipleInstances IgnoreNew
$principal = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" -LogonType Interactive -RunLevel Limited

Register-ScheduledTask -TaskName $Name -Action $action -Trigger $trigger -Settings $settings -Principal $principal `
    -Description "Wartet per IMAP IDLE auf neue Mails der drei PrimaerBau-Postfaecher und speichert sie sofort in data/data.db. Status: data/mail_sofort_status.json" -Force | Out-Null
Start-ScheduledTask -TaskName $Name

Set-Abruf 60 "Stuendlicher Sicherheitsabgleich aller Ordner der PrimaerBau-Postfaecher (collect_imap.py). Neue Mails kommen sofort ueber 'CEO-GPT PrimaerBau Mail-Sofort'; startet diesen neu, falls er steht."

Write-Host "Mail-Sofort-Abruf laeuft und startet kuenftig bei jeder Anmeldung." -ForegroundColor Green
Write-Host "Mail-Abruf ist jetzt der stuendliche Sicherheitsabgleich."
