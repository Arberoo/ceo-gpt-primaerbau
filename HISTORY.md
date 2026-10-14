# CEO-GPT Historie

> Zeitliches Logbuch aller Arbeiten in diesem CEO-GPT. Wird jede Session aktualisiert.
> Neueste Einträge oben. Jeder Eintrag hat Datum, Titel und Bullet Points.
>
> **So läuft's:** Wenn du `/commit` nach einer sinnvollen Arbeit ausführst, trägt dein
> Mitarbeiter hier automatisch ein. Du musst diese Datei nicht selbst schreiben.

---

## 2026-10-14

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
