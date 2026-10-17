# CEO-GPT Historie

> Zeitliches Logbuch aller Arbeiten in diesem CEO-GPT. Wird jede Session aktualisiert.
> Neueste Einträge oben. Jeder Eintrag hat Datum, Titel und Bullet Points.
>
> **So läuft's:** Wenn du `/commit` nach einer sinnvollen Arbeit ausführst, trägt dein
> Mitarbeiter hier automatisch ein. Du musst diese Datei nicht selbst schreiben.

---

## 2026-10-17

### Auto-Sicherung 2026-10-17
- 2 Datei(en) automatisch gesichert und gepusht
- (aus dem Diff erfasst, keine Gesprächsdetails verfügbar)

## 2026-10-16

### Bankanbindung Volksbank vorbereitet (Arber)
- Module `bank-anbindung` (v1.3.1) und `daten` aus dem Drive-ZIP nach `module-installs/` entpackt
- DataOS fehlte: nur der Kern übernommen (`db.py`, `config.py`, `collect.py`, `generate_metrics.py`), Datenbank bleibt im Modus des Mail-Abrufs, Übersicht lokal in `data/kennzahlen/key-metrics.md` (nicht GitHub), eigener Bank-Abschnitt
- Bankanbindung auf Windows umgestellt: Login/PIN in der Windows-Anmeldeinformationsverwaltung (keyring), echte Windows-Zugriffsrechte statt chmod (`scripts/banking/rechte.py`), Tagesabruf als Windows-Aufgabe (`scripts/setup_daten_abruf_windows.ps1`, noch nicht registriert); Abweichungen in `module-installs/bank-anbindung/ANPASSUNGEN.md`
- Selbsttest 118/118 grün; Bank erkannt: meine Volksbank Raiffeisenbank (BLZ 71160000, Atruvia-Server)
- Offen: echtes Einrichten mit Luljeta (VR-NetKey, PIN, Freigabe in VR SecureGo plus), danach erster Abruf und Tagesaufgabe

## 2026-10-15

### Buchhaltung vorbereitet, Alt-Postfächer, Selbststart (Arber)
- Fehlende Belege September für die Kanzlei Dornbach gesammelt: Mappe mit Arbeitsliste in `data/buchhaltung/2026-09-fehlende-belege/` (nur lokal), dazu die Kontenlisten der Kanzlei; Lage in `context/current-data.md`
- DATEV: Weg „Upload Mail“ gewählt (kein Belegtransfer/Karte, Wechsel zu Agenda kommt); Entwurf an Dornbach in Luljetas Entwürfen; `entwurf_html.py` kann jetzt cc
- Alt-Postfächer fesel@, karl@, salzberger@ nur lesend angebunden (Abgleich und Live-Werkzeuge, Entwürfe gesperrt, kein Sofort-Abruf); Auswertung Fall Bayrhof in der Akte
- `/prime` läuft automatisch beim Sitzungsstart (Hook `scripts/sitzung_start.py`)
- Regel: Nachziehen, Speichern und Hochladen ins Sicherungs-Repo macht der Mitarbeiter selbstständig

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
- Offene Leitung sieht neue Mails erst nach frischer Anmeldung: Abruf meldet sich neu an, sobald der Server mehr Mails kennt als geholt
- Neuer Prüfer `scripts/intel/check_mail_latency.py` misst je echter Mail die Zeit bis zur Speicherung, läuft stündlich mit
- Zustand jederzeit: `idle_imap.py --status`; Nachholen nach Neustart mit drei echten Test-Mails von Arber geprüft, Abnahme bestanden: echte Test-Mail Nr. 4 nach 27 s in der Datenbank, ohne Zutun

## 2026-10-15

### Arbeitstag mit Luljeta (15.10.)
- Angebot Eichner (Elektro Theresienstr. 11) geprüft, `outputs/pruefungen/2026-10-15-angebot-eichner-theresienstr-11.md`; Rückfrage-Mail in mehreren Runden auf 4 Punkte eingekürzt (gesendet)
- Neue Fähigkeiten (Freigabe Arber): `scripts/intel/entwurf_loeschen.py` (eigene Entwürfe in den Papierkorb), `scripts/intel/entwurf_html.py` (HTML-Entwurf mit Signatur, Foto und Logo eingebettet, Calibri 11)
- Zahlungsbitte an BauUnion (Abschlagsrechnung 1-10-26) als Entwurf
- UTA-Tankkarten: Verlauf ausgewertet, Kontaktformular für Kunden im Browser ausgefüllt und mit Luljetas Ja abgeschickt; stündliche Prüfung auf Antwort (geplante Aufgabe `uta-antwort-melden`)
- Telekom: Übernahme von 4 MUBA-Nummern auf PrimärBau, Formular ausgefüllt (`outputs/telekom/`), Mails an vorl. Insolvenzverwalter und Frau Speer als Entwurf
- Erinnerungen und Prüfungen als geplante Aufgaben (Spemann/Targobank 16.10., Unterlagen 19./22.10., Antwort RAin stündlich)
- Neue Gedächtnis-Regeln: Calibri 11, Ton je Empfänger, nichts senden ohne gelesene Endfassung, alte Entwurfsfassungen wegräumen, vor „fehlt noch“ Gesendetes prüfen, Interna aus Mails heraushalten
- Bau-Liste ergänzt: Scan-Ordner, DATEV, MUBA-Entwürfe löschen, MUBA-Mails in die lokale Suche, Sofort-Benachrichtigung, Empfänger-Freigabeliste, Anhänge lesen

### MUBA-Postfächer über Microsoft Graph (Arber, nachts)
- Entra-App „CEO-GPT PrimaerBau Mail“ im MUBA-Mandanten (nur dieser Mandant, Rechte User.Read, offline_access, Mail.ReadWrite, **kein Mail.Send**, Admin-Zustimmung erteilt)
- Softeria ms-365-mcp v0.113.0 lokal gebaut (Node 24, `npm run generate`), offline_access-Patch, Starter `scripts/intel/ms365_mcp_run.py` nur mit Lese- und Entwurfswerkzeugen, MCP `mail_muba`
- l.bajraktari@ und info@muba-service-gmbh.de angemeldet (beides eigene Konten), Lesen getestet
- Luljetas MUBA-Konto ist Globaler Administrator; Abklärung mit Insolvenzverwalter offen
