# Richtet die naechtliche Sicherung in der Windows-Aufgabenplanung ein (Windows-Gegenstueck zu setup_autocommit.py).
# Aufruf:  powershell -ExecutionPolicy Bypass -File scripts\setup_autocommit_windows.ps1
# Entfernen: ... -File scripts\setup_autocommit_windows.ps1 -Entfernen

param([switch]$Entfernen)

$Name = "CEO-GPT PrimaerBau Sicherung"
$Repo = Split-Path -Parent $PSScriptRoot

if ($Entfernen) {
    Unregister-ScheduledTask -TaskName $Name -Confirm:$false -ErrorAction SilentlyContinue
    Write-Host "Naechtliche Sicherung entfernt."
    exit 0
}

$pyw = (Get-Command pythonw.exe -ErrorAction SilentlyContinue).Source
if (-not $pyw) { $pyw = Join-Path $env:LOCALAPPDATA "Programs\Python\Python312\pythonw.exe" }
if (-not (Test-Path $pyw)) { Write-Host "pythonw.exe nicht gefunden. Python installieren." -ForegroundColor Yellow; exit 1 }

$action   = New-ScheduledTaskAction -Execute $pyw -Argument "-X utf8 `"$Repo\scripts\auto_commit_windows.py`"" -WorkingDirectory $Repo
$trigger  = New-ScheduledTaskTrigger -Daily -At "23:45"
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
            -RunOnlyIfNetworkAvailable -ExecutionTimeLimit (New-TimeSpan -Minutes 30) -MultipleInstances IgnoreNew
$principal = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" -LogonType Interactive -RunLevel Limited

Register-ScheduledTask -TaskName $Name -Action $action -Trigger $trigger -Settings $settings -Principal $principal `
    -Description "Speichert das CEO-GPT PrimaerBau jede Nacht, laedt es zu GitHub hoch und schreibt HISTORY.md fort." -Force | Out-Null

$t = Get-ScheduledTask -TaskName $Name
Write-Host "Naechtliche Sicherung eingerichtet. Naechster Lauf: $((Get-ScheduledTaskInfo -TaskName $Name).NextRunTime)" -ForegroundColor Green
