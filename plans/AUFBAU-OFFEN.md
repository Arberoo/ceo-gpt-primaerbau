# Aufbau: offene Punkte (nur für Arber)

> **Diese Liste ist Arbers Baustelle.** Luljeta arbeitet *mit* dem CEO-GPT, Arber baut *am* CEO-GPT.
> Der Mitarbeiter zeigt diese Liste **nur**, wenn Arber sich meldet („Hier ist Arber“) oder jemand ausdrücklich danach fragt. Luljeta wird damit nicht konfrontiert.
> Erledigtes abhaken (nicht löschen), mit Datum. Neue Bau-Themen hier eintragen, nicht in Luljetas Briefings.

Stand: 16.10.2026

## 🔴 Zuerst

- [ ] **Nacht-Sicherung 15.10. 23:45 ist nicht gelaufen** (kein Eintrag in `data/auto_commit.log`, letzter Lauf 14.10.). Vermutlich PC im Energiesparmodus (Wachhalte-Programm endete 15.10. 8 Uhr). Prüfen: Aufgabe „Reaktivierung zum Ausführen“ / „verpasste Ausführung nachholen“. Mitarbeiter hat am 16.10. morgens von Hand gesichert.

- [ ] **MUBA-Postfächer als PST sichern (Weg A).** Outlook lädt info@ und l.bajraktari@ (MUBA) seit 14.10. komplett nach (Stand 14.10. spät: info@ bis 06/2023, l.bajraktari@ bis 06/2025). Wenn fertig: Export nach `C:\MUBA-Sicherung`, dann eine Kopie auf eine externe Festplatte. Anleitung `docs/muba-postfaecher-sichern.md`. **Vor** dem Bau des Mail-Assistenten.
- [ ] **Mail an Herrn Festing senden.** Entwurf liegt in info@primaerbau.com unter „Entwürfe“ (Zugangsdaten fesel@, Salzberger, karl@). Für den Fall Kautz wichtig, Frist 23.10. Wenn die Zugangsdaten kommen: verdeckt hinterlegen und anbinden lassen (Akte `data/akten/2026-444-Bayrhof-Kautz/AKTE.md`).
- [ ] **Mail-Assistent bauen:** `/implement plans/2026-10-15-mail-assistent-posteingang.md` (nach dem PST-Export). Danach Luljeta kurz zeigen, wie sie `/posteingang` nutzt.

- [x] **Scan-Ordner** (17.10.): `C:\PrimaerBau-Belege\Scan-Eingang` (+ `erledigt`), Verknüpfung auf dem Desktop, Ablauf im Playbook Buchhaltung. **Offen:** Scanner von Luljeta auf diesen Ordner einstellen (Scanner ist der **Brother MFC-L5750DW**, MAC 10:6F:D9:24:48:D8, mDNS `BRW106FD92448D8`; am 17.10. im Büronetz 192.168.20.x/172.17.1.x nicht gefunden, früher unter 192.168.50.93 und 192.168.178.77. Weg je Standort: gleiches Netz → „Scan to Network“ auf eine Freigabe, sonst „Scan to E-Mail“ an ein Postfach, das der Mail-Abruf schon liest), Ordner in die Sicherung aufnehmen (liegt außerhalb des CEO-GPT, PDFs gehen nicht zu GitHub), Texterkennung für Bild-PDFs, automatisches Melden neuer Scans.
- [x] **/prime automatisch** (15.10.): Start-Hook in `.claude/settings.json` → `scripts/sitzung_start.py`. Prüfen in der nächsten echten Sitzung von Luljeta, ob die Begrüßung beim ersten Satz kommt (Hooks greifen erst in neuen Sitzungen).
- [x] **Alt-Postfächer fesel@, karl@, salzberger@ angebunden** (15.10.): Konten mit `nur_archiv`, aus dem Sofort-Abruf ausgenommen, MCP `mail_pb_fesel|karl|salzberger` nur lesen (Entwürfe gesperrt), eingelesen in `mail_messages`. Doku `docs/mail-imap-primaerbau.md`. Live-Werkzeuge erst nach Neustart der Sitzung.
- [ ] **Alt-Postfächer vor dem 28.02.2027 vollständig lokal sichern** (.eml samt Anhängen), danach löscht HostedOffice sie. Zugangsdaten-Mail von Festing (15.10., info@, Klartext-Passwörter) danach von Luljeta löschen lassen.
- [ ] **DATEV Upload Mail bei Dornbach angefragt** (Entwurf 15.10. in l.bajraktari@, Luljeta sendet). Entscheidung Arber 15.10.: kein Belegtransfer, keine SmartCard/mIDentity, weil der Wechsel zu Diana Rohrbach bald kommt. Danach **Agenda**: Belege im Browser hochladen (so macht Arber es schon in seinem CEO-GPT), Luljeta meldet sich an, Mitarbeiter bereitet vor.
- [x] **DATEV lesend** (17.10.): Abgleich über den eingebauten Browser, Luljeta meldet sich an, Belegliste wird gelesen, `datev_abgleich.py` gleicht ab (Playbook Buchhaltung). Feste Schnittstelle weiter nicht sinnvoll (Partnerprogramm, Kanzleiwechsel zu Agenda). Hochladen bleibt Luljetas Klick.
- [ ] **Wunsch Luljeta (15.10.): DATEV-Upload.** Ergebnis Prüfung 15.10.: Echte Schnittstelle (DATEV-API) braucht Partnerprogramm und Wochen; DATEV Belegtransfer (Ordner-Upload) braucht SmartCard/mIDentity, nicht SmartLogin. Passender Weg: **DATEV Upload Mail** (in Unternehmen online unter Belege → Einstellungen → Upload Mail; Absender l.bajraktari@ und rechnung@ registrieren). Dann legt der Mitarbeiter je Beleg einen Entwurf mit PDF an die DATEV-Adresse ab, Luljeta drückt Senden. Zieladresse in die Empfänger-Freigabeliste. Mit Dornbach klären, ob freigeschaltet/kostenpflichtig. Belege und Buchhaltung direkt zu DATEV hochladen (DATEV Unternehmen online / Belegtransfer), Verbindung zur Kanzlei. Abhängig vom geplanten Kanzleiwechsel zu Diana Rohrbach (Agenda), vorher klären, welches System gilt. Hochladen bleibt „ein Klick“: nur nach Luljetas Ja.

- [x] **MUBA-Abo Microsoft 365 Business Basic: Septemberabbuchung gesucht** (15.10.): gefunden auf Arbers Kartenabrechnung unter „Mfst“, alles bezahlt. Abo: 5 Lizenzen, 33,32 €/Monat, monatlich über Arbers private Karte (Entscheidung Arber 15.10.: bleibt so), verlängert sich am 18.01.2027. Admin Center zeigt den Zahlungsstatus nicht („N/V“), Abbuchungen nur auf der Kartenabrechnung sichtbar.
- [ ] **MUBA-Abo vor dem 18.01.2027 entscheiden:** verlängern oder kündigen (erst nach der Postfach-Sicherung). Bei Gelegenheit mit dem Insolvenzverwalter klären, ob die Kosten der MUBA erstattet werden.

## 🟠 Wochenende

- [ ] **Insolvenzverwalter fragen:** Ist der neue Zugang „CEO-GPT PrimaerBau Mail“ im MUBA-Microsoft-Konto in Ordnung? (Entfernen: `docs/mail-muba-graph.md`)
- [ ] **MUBA vollständig über Purview sichern (Weg B)**, Anleitung `docs/muba-postfaecher-sichern.md`.
- [ ] **Unterlagen aus dem MUBA-OneDrive** (`Desktop`, `Dokumente`) als Kopie nach `C:\PrimaerBau-Unterlagen\MUBA-OneDrive-Kopie\` ziehen (nur kopieren), danach `config/posteingang.json` → `dokument_ordner` umstellen. Mit Luljetas Ja.
- [ ] **CEO-GPT-Ordner abschotten:** `C:\CEO-GPT-PrimaerBau` erbt von `C:\` Schreibrechte für alle angemeldeten Benutzer (darunter die fremden lokalen Konten `CodexSandboxOffline`/`CodexSandboxOnline`). Als Administrator die Vererbung brechen und nur Luljetas Konto „Muba“, SYSTEM und Administratoren Zugriff geben. Vorher prüfen, ob die Windows-Aufgaben (Sicherung, Mail-Sofort, Mail-Abruf) danach noch laufen. Bei Gelegenheit klären, woher die Codex-Konten stammen und ob sie weg können.
- [ ] **Windows-Anmeldung absichern** (Plan `plans/2026-10-14-fernzugang-und-mailzugriff.md`, Teil 1): Welches Microsoft-Konto trägt die Anmeldung? Handynummer zur Wiederherstellung, Notfall-Admin-Konto, ggf. auf lokales Konto umstellen, BitLocker-Schlüssel sichern.
- [ ] **Alte CEO-GPT-Kopie im MUBA-OneDrive löschen:** `…\OneDrive - MUBA Service GmbH\Dokumente\CEO-GPT-PrimaerBau`. Bedingung (Nacht-Sicherung lief) ist erfüllt.

## 🟡 Danach

- [ ] **Fernzugang** für Arber (Tailscale, eigenes PrimärBau-Konto, PC teilen) und Edona (Büronetz, feste IP am Router). Plan Teil 4, Skript `module-installs/remote-windows/scripts/weg-n-einrichten.ps1`.
- [ ] **PC als Haupt-PC:** Dauerbetrieb (ist im Weg-N-Skript), BIOS „Power On after AC loss“.
- [ ] **Ablage-Modul** (`/install module-installs/ablage`): Ordnersystem für Unterlagen, Scans, Mail-Anhänge; PDF-Volltextsuche.
- [ ] **Buchhaltung** mit Edona (`module-installs/buchhaltung`), TEAM3-Weg mit dem IT-Dienstleister klären. Stand 15.10.: Steuerberater für die laufende FiBu ist **Dornbach** (Fabian Schmitz), Belege gehen nach DATEV Unternehmen Online, Bank ist die VR Bank (vb-rb.de). Für den Abgleich fehlt ein Kontoauszug-Export (CSV) je Monat. Fehlende Belege September: `data/buchhaltung/2026-09-fehlende-belege/ARBEITSLISTE.md` (Anhänge per Behelfsskript nur lesend geholt).
- [x] **Bankanbindung Volksbank (FinTS, nur lesen)** (17.10.): mit Luljeta eingerichtet, ein Zugang (BLZ 71160000) mit zwei Konten …0000 6970 79 und …0100 6970 79. Erster Abruf ohne TAN (Bank: 3076, SCA nicht nötig), Umsätze ab 20.07.2026. Tagesaufgabe „CEO-GPT PrimaerBau Daten-Abruf“ 06:30. Doku `docs/bank-anbindung.md`.
- [x] **Buchhaltungs-Modul auf Bankdaten umgestellt** (17.10.): Fähigkeit `buchhaltung`, `bank_export.py`, Engine-Zuordnung umgebaut (`module-installs/buchhaltung/ANPASSUNGEN.md`), September abgeglichen.
- [ ] **Texterkennung für Scans** in der Buchhaltung (Vodafone 18.09. ist ein Bild-PDF und wird nicht zugeordnet). Passt zum Scan-Ordner-Wunsch und zu „Anhänge lesen“.
- [x] **Hochladen in DATEV durch den Mitarbeiter** (17.10.): klappt über Claude in Chrome (`file_upload`), Luljeta meldet sich per SmartLogin-QR an, Ja je Vorgang. 4 September-Belege hochgeladen und im Posteingang geprüft. Ablauf im Playbook Buchhaltung.
- [ ] **Beim Wechsel zu Agenda (Diana Rohrbach)** von Anfang an einen lesenden Weg auf die Belegliste klären (Export oder Zugang), damit der Abgleich ohne Browser-Auslesen läuft.
- [ ] **Belege aus Mails automatisch holen**: Am 17.10. per Behelfsskript (nur lesend, readonly) 13 Rechnungen für September geholt. Sauberes Werkzeug bauen: je offener Bankzeile Rechnungs-Mail suchen, PDF nach `abschluss/…/2 Eingangsrechnungen`. Ältere Umsätze als ~90 Tage gibt die Bank nur mit TAN heraus, bei Bedarf einmalig mit Luljeta nachholen.
- [ ] **Edonas Kontext** ergänzen (`/install module-installs/kontext`, nur ihr Teil).
- [ ] **Automatischer Morgen-Lauf** von `/posteingang` (v2): `claude setup-token`, Aufgabenplanung.
- [ ] Optional: `CLAUDE_CODE_OAUTH_TOKEN` für schönere Texte der nächtlichen Sicherung.
- [ ] **Empfänger-Freigabeliste `mail_pb_*`** (15.10.): Entwurf an info@eichner-elektro.de wurde abgelehnt („recipient policy denied“), Entwurf ging ohne Empfänger. Liste lockern (z. B. alle Adressen, mit denen schon Mails gewechselt wurden), sonst muss Luljeta jedes Mal die Adresse selbst eintragen.
- [x] **MUBA-Entwürfe wegräumen/ändern** (erledigt 17.10.: `update-mail-message`/`delete-mail-message` freigeschaltet, Server prüft vorher isDraft; nach Sitzungsneustart live testen) (15.10., Luljeta wünscht das ausdrücklich und hat Dauerfreigabe für das Wegräumen alter Fassungen gegeben; heute liegen im MUBA-Postfach l.bajraktari@ je 3–4 Fassungen der Mails an von Gleichenstein und Löffler): `mail_muba` kann Entwürfe nur anlegen, nicht ändern oder löschen. Bei Korrekturen entstehen Doppel, Luljeta muss den alten selbst löschen. Analog zu `entwurf_loeschen.py` einen engen Weg über Graph (nur Entwürfe-Ordner, nur isDraft, verschieben nach Gelöschte Elemente) prüfen; Anhänge-Download (`download-bytes`) fehlt im Starter ebenfalls (Workaround: list-mail-attachments ohne $select liefert contentBytes).
- [ ] **Sofort-Benachrichtigung bei wichtigen Absendern** (Wunsch Luljeta 15.10.): Heute prüfen zwei geplante Aufgaben alle 30 Min. (UTA, RAin Löffler), das ist ihr zu langsam. Besser ein leichter Dauerläufer ohne Claude-Lauf: PrimärBau über den vorhandenen IDLE-Abruf (`data.db`), MUBA per Graph-Abfrage alle 1–2 Min. (oder Graph-Änderungsbenachrichtigung), bei Treffer auf einer Beobachtungsliste (z. B. lexmuc.com, uta.com, gleichenstein-breitling.de, telekom.de) eine Windows-Benachrichtigung zeigen. Danach die beiden Aufgaben `uta-antwort-melden` und `loeffler-antwort-melden` abschalten.
- [ ] **MUBA-Mails in die lokale Suche** (15.10.): Die PrimärBau-Postfächer liegen mit Volltext in `data/data.db`, die MUBA-Postfächer (Graph) nicht. Dadurch übersieht der Mitarbeiter leichter, was schon verschickt wurde (Fall Lindenstraße: Anhänge an RAin Löffler vom 27.07. nicht gesehen). Vorschlag: Graph-Abgleich der MUBA-Postfächer (Posteingang, Gesendet, Unterordner) in `mail_messages` inkl. Anhang-Namen, analog `collect_imap.py`; zusätzlich Spalte `attachment_names` für alle Postfächer.
- [ ] **Anhänge lesen:** `get_attachment_content` ist aus (`enable_attachment_content=false`). Am 15.10. per Behelfsskript nur lesend über `imap_common` geholt. Sauberen Weg einbauen (Anhang nach `data/`, PDF-Text, Scans per OCR); `pdftoppm`/`pypdf` fehlen.

## Erledigt

- [x] 14.10. Absicherung (Git, GitHub privat mit fine-grained Token, nächtliche Sicherung)
- [x] 14.10. Kontext-Gespräch mit Luljeta
- [x] 15.10. HTML-Entwürfe mit Signatur (Foto + Logo): `scripts/intel/entwurf_html.py`, nur APPEND in Entwürfe. Bitte bei Gelegenheit gegenlesen; ggf. später als MCP-Werkzeug.
- [x] 15.10. Entwürfe wegräumen: `scripts/intel/entwurf_loeschen.py` (nur Entwürfe, verschiebt in den Papierkorb), freigegeben von Arber, getestet
- [x] 14./15.10. Alle fünf Postfächer angebunden (IMAP + Graph), Sofort-Abruf per IDLE abgenommen
- [x] 15.10. Plan Mail-Assistent (zweimal geprüft)
