# Meldet ein MUBA-Postfach (Microsoft 365) fuer den Mitarbeiter an. Einmal je Postfach ausfuehren.
# Fragt beim ersten Mal die zwei (nicht geheimen) App-Kennungen ab.
# Aufruf im CEO-GPT-Ordner:  powershell -ExecutionPolicy Bypass -File scripts\muba_postfach_anmelden.ps1

Set-Location (Split-Path -Parent $PSScriptRoot)
$py = ".venv\Scripts\python.exe"
$envText = if (Test-Path .env) { [IO.File]::ReadAllText((Resolve-Path .env)) } else { "" }

if ($envText -notmatch '(?m)^MS365_MCP_CLIENT_ID=\S') {
  Write-Host "`n=== Anwendungs-ID (Client) eintragen ===" -ForegroundColor Cyan
  Write-Host "Einfuegen (Rechtsklick) und Enter:  fd0a6d4e-5c52-413e-a839-2e1b5e4e7965"
  & $py -X utf8 scripts\set_secret.py MS365_MCP_CLIENT_ID --show
}
if ($envText -notmatch '(?m)^MS365_MCP_TENANT_ID=\S') {
  Write-Host "`n=== Verzeichnis-ID (Mandant) eintragen ===" -ForegroundColor Cyan
  Write-Host "Einfuegen (Rechtsklick) und Enter:  db85f637-1f68-4796-aaae-199db56428d4"
  & $py -X utf8 scripts\set_secret.py MS365_MCP_TENANT_ID --show
}
Remove-Variable envText

Write-Host "`n=== Postfach bei Microsoft anmelden ===" -ForegroundColor Cyan
Write-Host "Gleich erscheint ein Code. Im Browser microsoft.com/devicelogin oeffnen, Code eingeben,"
Write-Host "mit dem gewuenschten MUBA-Postfach anmelden und den Zugriff bestaetigen."
& $py -X utf8 scripts\intel\ms365_mcp_run.py --login
Write-Host "`n=== Angemeldete Postfaecher ===" -ForegroundColor Cyan
& $py -X utf8 scripts\intel\ms365_mcp_run.py --list-accounts
Write-Host "`nFertig. Sag dem Mitarbeiter im Chat Bescheid." -ForegroundColor Green
