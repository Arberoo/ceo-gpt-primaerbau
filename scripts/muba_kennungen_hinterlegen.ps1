# Hinterlegt die zwei (nicht geheimen) Kennungen der MUBA-Entra-App in der .env.
# Aufruf im CEO-GPT-Ordner:  powershell -ExecutionPolicy Bypass -File scripts\muba_kennungen_hinterlegen.ps1

Set-Location (Split-Path -Parent $PSScriptRoot)
$py = ".venv\Scripts\python.exe"
Write-Host ""
Write-Host "=== 1 von 2: Anwendungs-ID (Client) ===" -ForegroundColor Cyan
Write-Host "Steht in Entra auf der Uebersichtsseite der App 'CEO-GPT PrimaerBau Mail'. Kopieren, hier einfuegen (Rechtsklick), Enter."
& $py -X utf8 scripts\set_secret.py MS365_MCP_CLIENT_ID --show
Write-Host ""
Write-Host "=== 2 von 2: Verzeichnis-ID (Mandant) ===" -ForegroundColor Cyan
Write-Host "Steht direkt darunter. Kopieren, einfuegen, Enter."
& $py -X utf8 scripts\set_secret.py MS365_MCP_TENANT_ID --show
Write-Host ""
Write-Host "Fertig. Sag dem Mitarbeiter im Chat Bescheid." -ForegroundColor Green
