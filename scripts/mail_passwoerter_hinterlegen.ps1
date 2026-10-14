# Hinterlegt die Passwoerter der PrimaerBau-Postfaecher (HostedOffice) verdeckt in der .env.
# Nichts erscheint auf dem Schirm. Ein Postfach ueberspringen: einfach zweimal Enter druecken.
# Aufruf im CEO-GPT-Ordner:  powershell -ExecutionPolicy Bypass -File scripts\mail_passwoerter_hinterlegen.ps1

Set-Location (Split-Path -Parent $PSScriptRoot)
$py = ".venv\Scripts\python.exe"
$konten = @(
  @{ Key = "IMAP_PW_PB_LULJETA";  Adresse = "l.bajraktari@primaerbau.com" },
  @{ Key = "IMAP_PW_PB_INFO";     Adresse = "info@primaerbau.com" },
  @{ Key = "IMAP_PW_PB_RECHNUNG"; Adresse = "rechnung@primaerbau.com" }
)
$i = 0
foreach ($k in $konten) {
  $i++
  Write-Host ""
  Write-Host "=== $i von 3: Passwort fuer $($k.Adresse) ===" -ForegroundColor Cyan
  Write-Host "Passwort tippen (es erscheint nichts), Enter, dann zur Kontrolle nochmal tippen, Enter."
  Write-Host "Nicht bekannt? Zweimal einfach Enter druecken, dann wird es uebersprungen."
  & $py -X utf8 scripts\set_secret.py $k.Key
}
Write-Host ""
Write-Host "Fertig. Sag dem Mitarbeiter im Chat Bescheid." -ForegroundColor Green
