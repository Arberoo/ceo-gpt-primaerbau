# Changelog remote-windows

Neueste Version oben. **MAJOR** = die Einrichtung ändert sich oder etwas Bestehendes bricht, **MINOR** = neue Funktion, **PATCH** = Fix ohne Verhaltensänderung.

## 2.0.0 (2026-10-10)

- Neuer **Weg N**: CEO-GPT nativ auf Windows, bedient per SSH-Sitzung der Claude-Desktop-App von Laptop oder zweitem PC. Im Kundenbetrieb belegt (Windows → Windows, Shell cmd.exe). Ersetzt die frühere Annahme, SSH-Ziele müssten Linux sein.
- Wegwahl N/V am Anfang von INSTALL.md; der bisherige Linux-VM-Ablauf bleibt unverändert als Weg V.
- Neu `references/claude-desktop-ssh-windows.md`: Ziel-PC prüfen, Arbeitsgeräte einrichten (Mindestversion 2.31226.0, Fingerabdruck einmal im Terminal bestätigen, Formularfelder), Pflichtprüfung NAS/Branchensoftware in der SSH-Sitzung, Git-Hinweis, Remote Control als Rückfall, HTTPS übers Tailnet und eigene Domain.
- Neu `scripts/windows-ssh-check.ps1` (liest nur): sshd, SFTP, MaxSessions, Passwort-Anmeldung, Standard-Shell, git, Speicher, Tailscale.
- Troubleshooting um die typischen Fehler von Weg N ergänzt.
- `manifest.json` und dieser Changelog neu; Version vorher `v1`.

## 1.0.0 (2026-06-15)

- Erste Fassung: CEO-GPT in einer Ubuntu-VM (Hyper-V) auf einem immer-an Windows-PC, Fernzugriff über Tailscale-SSH.
