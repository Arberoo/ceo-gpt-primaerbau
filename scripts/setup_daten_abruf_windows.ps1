# Richtet den taeglichen Daten-Abruf (DataOS, derzeit Bankanbindung) in der Windows-Aufgabenplanung ein.
# Windows-Gegenstueck zu den launchd-Vorlagen com.ceogpt.daten-collect / com.ceogpt.bank-collect.
# Aufruf:  powershell -ExecutionPolicy Bypass -File scripts\setup_daten_abruf_windows.ps1
# Entfernen: ... -File scripts\setup_daten_abruf_windows.ps1 -Entfernen
#
# Laeuft als angemeldetes Konto (Interactive), weil Login und PIN der Bank in dessen
# Windows-Anmeldeinformationsverwaltung liegen. Genau EIN Lauf pro Tag.

param([switch]$Entfernen, [string]$Uhrzeit = "06:30")

$Name = "CEO-GPT PrimaerBau Daten-Abruf"
$Repo = Split-Path -Parent $PSScriptRoot

if ($Entfernen) {
    Unregister-ScheduledTask -TaskName $Name -Confirm:$false -ErrorAction SilentlyContinue
    Write-Host "Taeglicher Daten-Abruf entfernt."
    exit 0
}

$pyw = Join-Path $Repo ".venv\Scripts\pythonw.exe"
if (-not (Test-Path $pyw)) { Write-Host ".venv\Scripts\pythonw.exe nicht gefunden." -ForegroundColor Yellow; exit 1 }

$action   = New-ScheduledTaskAction -Execute $pyw -Argument "-X utf8 `"$Repo\scripts\daten_abruf_windows.py`"" -WorkingDirectory $Repo
$trigger  = New-ScheduledTaskTrigger -Daily -At $Uhrzeit
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
            -RunOnlyIfNetworkAvailable -ExecutionTimeLimit (New-TimeSpan -Minutes 15) -MultipleInstances IgnoreNew
$principal = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" -LogonType Interactive -RunLevel Limited

Register-ScheduledTask -TaskName $Name -Action $action -Trigger $trigger -Settings $settings -Principal $principal `
    -Description "Holt einmal taeglich Kontostand und Umsaetze (nur lesen) und erneuert die Kennzahlen." -Force | Out-Null

Write-Host "Taeglicher Daten-Abruf eingerichtet. Naechster Lauf: $((Get-ScheduledTaskInfo -TaskName $Name).NextRunTime)" -ForegroundColor Green
