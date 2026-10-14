# Absicherung (Windows): Git, GitHub-Backup, nächtliche Sicherung

> Wie das CEO-GPT PrimärBau auf Luljetas PC gesichert wird und was zu tun ist, wenn etwas hakt.

## Überblick

- **Ort:** `C:\CEO-GPT-PrimaerBau` (bewusst nicht im OneDrive der MUBA Service GmbH)
- **Backup:** privates Repo `https://github.com/Arberoo/ceo-gpt-primaerbau`, Branch `main`
- **Speicherpunkt-Name:** `PrimärBau <Arberoo@users.noreply.github.com>` (nur in diesem Repo gesetzt)
- **Nächtlich:** Windows-Aufgabe „CEO-GPT PrimaerBau Sicherung“, täglich 23:45, holt verpasste Läufe nach dem Einschalten nach

## Zugang zu GitHub

- Nur ein **fine-grained Token** von Arber: Zugriff ausschließlich auf `ceo-gpt-primaerbau`, Recht „Contents: Read and write“, **läuft nie ab** (angelegt 14.10.2026, Name „PrimaerBau-PC Luljeta“).
- Liegt in der **Windows-Anmeldeinformationsverwaltung** (Eintrag `git:https://github.com`), nicht in `.env`, nicht in einer Datei.
- Git ist so eingestellt, dass es bei GitHub nur Tokens annimmt (`credential.gitHubAuthModes = pat`). Ein Browser-Login mit Vollzugriff wird nicht angeboten. GitHub CLI ist bewusst nicht angemeldet, bitte kein `gh auth login` auf diesem PC.
- **Token ersetzen** (verloren, widerrufen, PC kompromittiert): Arber legt auf github.com/settings/personal-access-tokens einen neuen an (gleiche Einstellungen), widerruft den alten, dann im CEO-GPT-Ordner:
  `powershell -ExecutionPolicy Bypass -File scripts\github_token_hinterlegen.ps1`

## Dateien

| Datei | Zweck |
|---|---|
| `scripts/auto_commit.py` | Speichern, Logbuch fortschreiben, hochladen (aus dem Modul, unverändert) |
| `scripts/auto_commit_windows.py` | Windows-Starter: unsichtbar, Protokoll nach `data/auto_commit.log`, schiebt liegengebliebene Uploads nach |
| `scripts/setup_autocommit_windows.ps1` | Legt die Windows-Aufgabe an (`-Entfernen` zum Löschen) |
| `scripts/github_token_hinterlegen.ps1` | Token verdeckt in die Windows-Anmeldeinformationsverwaltung |
| `.gitignore` | Was nie zu GitHub darf (`.env`, `data/`, Postfach-Exporte, PDFs, Office, Bilder, `context/import/`) |

## Prüfen und Fehlerbehebung

- Letzte Läufe: `data/auto_commit.log` (wird bei `/prime` geprüft)
- Aufgabe von Hand starten: `Start-ScheduledTask -TaskName "CEO-GPT PrimaerBau Sicherung"`
- „Push scheiterte“: meist Internet weg (wird nachgeholt) oder Token ungültig (siehe „Token ersetzen“)
- Commit-Texte sind schlicht („Auto-Sicherung DATUM“), solange kein `CLAUDE_CODE_OAUTH_TOKEN` hinterlegt ist. Optional später.

## History

| Datum | Änderung |
|---|---|
| 2026-10-14 | Eingerichtet (Arber, Luljeta) |
