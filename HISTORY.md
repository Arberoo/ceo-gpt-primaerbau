# CEO-GPT Historie

> Zeitliches Logbuch aller Arbeiten in diesem CEO-GPT. Wird jede Session aktualisiert.
> Neueste Einträge oben. Jeder Eintrag hat Datum, Titel und Bullet Points.
>
> **So läuft's:** Wenn du `/commit` nach einer sinnvollen Arbeit ausführst, trägt dein
> Mitarbeiter hier automatisch ein. Du musst diese Datei nicht selbst schreiben.

---

## 2026-10-14

### Auto-Sicherung 2026-10-14
- 3 Datei(en) automatisch gesichert und gepusht
- (aus dem Diff erfasst, keine Gesprächsdetails verfügbar)

### Absicherung eingerichtet (Arber und Luljeta)
- CEO-GPT aus dem MUBA-OneDrive nach `C:\CEO-GPT-PrimaerBau` kopiert (unabhängig vom MUBA-Microsoft-Konto); alte Kopie liegt noch im OneDrive
- Python 3.12 und GitHub CLI installiert (winget); GitHub CLI ist bewusst NICHT angemeldet
- Git eingerichtet, Speicherpunkte unter dem Namen „PrimärBau“
- Privates Repo `Arberoo/ceo-gpt-primaerbau`; Zugriff nur über fine-grained Token (nur dieses Repo, Contents: Read and write, läuft nie ab), hinterlegt in der Windows-Anmeldeinformationsverwaltung via `scripts/github_token_hinterlegen.ps1`
- Schutzliste (.gitignore) erweitert: .pst/.msg/.eml, PDFs, Office-Dateien, Bilder, `context/import/` bleiben lokal
- Nächtliche Sicherung 23:45 über die Windows-Aufgabenplanung („CEO-GPT PrimaerBau Sicherung“), Probelauf erfolgreich
- HISTORY.md, docs/-System und `/commit` Befehl angelegt, `/prime` liest Logbuch und Doku-Index

### Kontext, Mails, erster Fall (Luljeta und Arber)
- Kontext-Interview: Firma (Arber) und Luljetas Rolle, Ziele, Fristen; CLAUDE.md personalisiert (Leitregel „ein Klick“, PrimärBau/MUBA trennen)
- Mail-Zugriff über das klassische Outlook am PC erprobt (`docs/mail-zugriff-outlook.md`)
- Erster Fall: Bayrhof ./. PrimärBau (RA Dr. Kautz, Frist 23.10.2026), Akte lokal in `data/akten/`
- MUBA-Postfächer: Outlook bei info@ und l.bajraktari@ auf „Alle“ gestellt, lädt nach; Export folgt; Anleitung Purview für Arber (`docs/muba-postfaecher-sichern.md`)
- `/prime` legt offene Briefings aus `outputs/briefings/` zuerst vor (erstes Briefing für Luljeta am 15.10.)

### Speicher-Erlaubnis, Plan, PrimärBau-Mails per IMAP (Arber)
- Erlaubnisregeln in `.claude/settings.local.json`: git add/commit/push erlaubt, force/reset/clean verboten
- Plan `plans/2026-10-14-fernzugang-und-mailzugriff.md`: Mails beim Anbieter, eigenes Tailscale-Konto PrimärBau mit Teilen an Arber, Edona übers Büronetz, Windows-Anmeldung absichern (Wochenende)
- Windows-Anmeldung geprüft: kein Entra-Join, keine MUBA-Fernverwaltung, nur lose Arbeitskonto-Verknüpfung
- `intelligenz-imap` auf Windows: drei PrimärBau-Postfächer bei HostedOffice (IMAP, IDLE-fähig), Live-MCP je Postfach **nur Entwürfe**, Backfill in data.db, Abruf alle 15 Min. per Aufgabenplanung; Abweichungen in `module-installs/intelligenz-imap/ANPASSUNGEN.md`

### Mails kommen sofort an (IMAP IDLE)
- Neuer Dauerläufer `scripts/intel/idle_imap.py`: hält je PrimärBau-Postfach eine Leitung zu INBOX und „Gesendete Elemente“ offen, neue Mails sind spätestens nach ~30 Sekunden in `data/data.db`
- Windows-Aufgabe „CEO-GPT PrimaerBau Mail-Sofort“ startet ihn bei jeder Anmeldung, Neustart nach Absturz; Einrichtung `scripts/intel/setup_imap_idle_windows.ps1`
- Bisheriger 15-Minuten-Abruf ist jetzt der stündliche Sicherheitsabgleich aller Ordner und startet den Sofort-Abruf neu, falls er steht
- HostedOffice-Eigenheiten gefunden und umgangen: keine verlässliche IDLE-Meldung (darum Nachschauen alle 30 s), eingefrorener Ordnerstand, verzögerter Suchindex (darum Abruf per UID FETCH, auch im stündlichen Abgleich)
- Zustand jederzeit: `idle_imap.py --status`; Nachholen nach Neustart mit zwei echten Test-Mails von Arber geprüft

## 2026-10-15

### MUBA-Postfächer über Microsoft Graph (Arber, nachts)
- Entra-App „CEO-GPT PrimaerBau Mail“ im MUBA-Mandanten (nur dieser Mandant, Rechte User.Read, offline_access, Mail.ReadWrite, **kein Mail.Send**, Admin-Zustimmung erteilt)
- Softeria ms-365-mcp v0.113.0 lokal gebaut (Node 24, `npm run generate`), offline_access-Patch, Starter `scripts/intel/ms365_mcp_run.py` nur mit Lese- und Entwurfswerkzeugen, MCP `mail_muba`
- l.bajraktari@ und info@muba-service-gmbh.de angemeldet (beides eigene Konten), Lesen getestet
- Luljetas MUBA-Konto ist Globaler Administrator; Abklärung mit Insolvenzverwalter offen
