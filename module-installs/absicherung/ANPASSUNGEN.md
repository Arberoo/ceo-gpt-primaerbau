# Anpassungen für Windows (PrimärBau, 14.10.2026)

Abweichungen von INSTALL.md, weil dieses CEO-GPT auf Windows 11 läuft. Details: `docs/absicherung-windows.md`.

| Original (Mac/Linux) | Hier auf Windows | Grund |
|---|---|---|
| CEO-GPT-Ordner beliebig | `C:\CEO-GPT-PrimaerBau` statt OneDrive der MUBA Service GmbH | Konto der insolventen MUBA kann wegfallen; OneDrive verträgt sich schlecht mit Git |
| `git config --global` | Name/E-Mail nur im Repo (`PrimärBau`, Arberoo-noreply) | Wunsch Arber; nichts Globales auf dem PC verändern |
| `gh auth login` oder classic Token mit `repo` | Fine-grained Token nur für `ceo-gpt-primaerbau`, in Windows-Anmeldeinformationsverwaltung, `credential.gitHubAuthModes=pat` | PC soll nicht an Arbers andere Repos kommen |
| LaunchAgent / systemd-Timer | Windows-Aufgabenplanung über `scripts/setup_autocommit_windows.ps1` | Kein launchd/systemd auf Windows |
| `python3 scripts/auto_commit.py` | `pythonw -X utf8 scripts/auto_commit_windows.py` | Ohne Fenster, UTF-8 für Umlaute, Log-Datei, Push-Nachholen |
| `.gitignore` aus Vorlage | ergänzt um Windows-Dateien, `.pst/.ost/.msg/.eml`, PDFs, Office, Bilder, `context/import/` | Firmen- und Verfahrensunterlagen bleiben lokal |
| OpenRouter-Key im Setup | übersprungen (optional) | Wird erst für Transkription/Bilder gebraucht |
| HISTORY.md-Vorlage mit Platzhalter | Platzhalter durch echten Eintrag ersetzt | Platzhalter störte das Einsortieren neuer Einträge |
