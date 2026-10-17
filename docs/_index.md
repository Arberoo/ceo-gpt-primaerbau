# Doku-Index

> Dein Mitarbeiter scannt diese Datei, um die passende Doku zu finden, bevor er an einem System arbeitet.
> Lad nur die Dokus, die zu deiner aktuellen Aufgabe passen.
>
> **Update-Regel:** Wenn du ein dokumentiertes System änderst, aktualisier seine Doku.
> Wenn du ein neues System baust, leg eine Doku an und trag sie hier ein.
>
> **Doku-Vorlagen:** Siehe `docs/_templates/` für System- und Integrations-Vorlagen.

---

## Systeme

| Bedingung | Doku | Zusammenfassung |
|---|---|---|
| Arbeit an Git, GitHub-Backup, Token, nächtlicher Sicherung | `docs/absicherung-windows.md` | Ort, Zugang (fine-grained Token), Windows-Aufgabe 23:45, Fehlerbehebung |
| PrimärBau-Mails lesen, suchen, Entwürfe anlegen (Hauptweg) | `docs/mail-imap-primaerbau.md` | IMAP bei HostedOffice, MCP `mail_pb_*`, nur Entwürfe, Sofort-Abruf per IDLE in data.db (+ stündlicher Abgleich) |
| MUBA-Mails lesen, Entwürfe anlegen (Hauptweg) | `docs/mail-muba-graph.md` | Microsoft Graph, Entra-App „CEO-GPT PrimaerBau Mail“, MCP `mail_muba`, kein Senden |
| Mails über Outlook am PC (Rückfall, z. B. andere MUBA-Postfächer) | `docs/mail-zugriff-outlook.md` | Klassisches Outlook (COM), nur am PC selbst |
| MUBA-Postfächer sichern (.pst, Purview) | `docs/muba-postfaecher-sichern.md` | Bestand, Weg A Outlook, Weg B Purview, offene Frage MUBA Bau/Holding |

## Integrationen

| Bedingung | Doku | Zusammenfassung |
|---|---|---|
| Buchhaltung, Monatsabschluss, Belege zuordnen, Buchungsliste für Dornbach | `.claude/skills/buchhaltung/SKILL.md` | Bankdaten → `bank_export.py` → `buchungsliste.py`, Ordner `data/buchhaltung/abschluss/`, Anpassungen `module-installs/buchhaltung/ANPASSUNGEN.md` |
| Scanner, Scannen in den Scan-Eingang, Brother | `docs/scanner-brother.md` | Brother MFC-J5740DW, Scan to Network (SMB) auf `\MUBA-PC2\Scan-Eingang`, Konto `scanner`, Einrichtungsskript |
| Kontostand, Umsätze, Volksbank, Bank-Abruf, TAN-Erneuerung | `docs/bank-anbindung.md` | FinTS nur lesend, Login/PIN in Windows-Anmeldeinformationen, täglicher Abruf 06:30 in data.db, Übersicht `data/kennzahlen/key-metrics.md` |
