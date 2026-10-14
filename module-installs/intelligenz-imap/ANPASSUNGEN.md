# Anpassungen für Windows (PrimärBau, 14.10.2026)

Abweichungen von INSTALL.md, weil dieses CEO-GPT auf Windows 11 läuft. Betrieb und Fehlerbehebung: `docs/mail-imap-primaerbau.md`.

| Original (Mac) | Hier auf Windows | Grund |
|---|---|---|
| `.venv/bin/pip`, `python3` | `.venv\Scripts\python.exe` (Python 3.12, venv im CEO-GPT-Ordner) | Windows-Pfade; `python` ist im PATH nicht verlässlich (Store-Alias) |
| `brew install uv` | `winget install astral-sh.uv`; der Starter nutzt den vollen Pfad zu `uvx.exe` | kein Homebrew |
| `imap-mcp-run.sh` + `mcp-email-server@latest` | `scripts/intel/imap_mcp_run.py <label>`, ein MCP-Server je Postfach, Version fest auf `mcp-email-server==1.13.1` | Shell-Skript läuft nicht nativ; Single-Account-Env je Postfach statt TOML mit Klartext-Passwörtern; kein ungeprüftes Update |
| Server darf alles, Senden über fehlendes SMTP abgeschaltet | `ACCOUNT_ALLOWED_MUTATIONS=draft`: nur Entwürfe. Senden, Löschen, Verschieben, Markieren sind im Server gesperrt. Zusätzlich deny-Regeln in `.claude/settings.local.json` | Leitregel „ein Klick“ |
| Server-Config unter `~/.config/zerolib/...` | `%USERPROFILE%\.ceo-gpt-primaerbau\mcp-email\<label>.toml` | Der Server verlangt unter Windows einen privaten Ordner. `C:\CEO-GPT-PrimaerBau` erbt Schreibrecht für alle Benutzer, `%LOCALAPPDATA%` teilt sich das Claude-App-Paket |
| LaunchAgent `com.ceogpt.imap-collect` | Windows-Aufgabe „CEO-GPT PrimaerBau Mail-Abruf“, **stündlich** als Sicherheitsabgleich aller Ordner, `pythonw` + `scripts/intel/collect_imap_windows.py`; startet den Sofort-Abruf neu, wenn er steht | kein launchd |
| IDLE-Dauerläufer (Standard Inhaltseingang), im Modul nicht enthalten | **ergänzt:** `scripts/intel/idle_imap.py`, Windows-Aufgabe „CEO-GPT PrimaerBau Mail-Sofort“ bei Anmeldung (kein Zeitlimit, Neustart nach Absturz), eingerichtet mit `scripts/intel/setup_imap_idle_windows.ps1`. IDLE auf INBOX + Gesendete je Postfach, Erneuerung alle 5 Min., Cursor nach dem Speichern, Wiederverbindung 5 s → 5 Min., Status `data/mail_sofort_status.json` | Standard verlangt Echtzeit; HostedOffice kann IDLE |
| Abruf neuer UIDs über UIDNEXT-Vergleich | immer `UID last+1:*` abfragen | HostedOffice meldet per STATUS im geöffneten Ordner einen veralteten UIDNEXT (getestet 14.10.2026) |
| Konten frei benannt | `pb_luljeta`, `pb_info`, `pb_rechnung` (alle `mail.de2.hostedoffice.ag:993`, Benutzername = Mailadresse) | HostedOffice Exchange, IMAP mit normalem Postfach-Passwort |
