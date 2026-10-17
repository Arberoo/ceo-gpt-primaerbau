---
name: buchhaltung
description: Monatlicher Buchhaltungs-Workflow für PrimärBau GmbH (Bank meine Volksbank Raiffeisenbank, 2 Konten). Ordnet jede Kontobewegung ihrem Beleg zu, holt fehlende Rechnungen, erfasst Privatauslagen und Cash, erzeugt die Buchungsliste für den Steuerberater und sagt, was als vollständig gilt. Use when working on Buchhaltung, Monatsabschluss, Belege/Rechnungen/Kontoauszug zuordnen, "was fehlt noch für den Steuerberater", Privatauslagen, VAT/Umsatzsteuer-Unterlagen, oder wenn ein neuer Beleg im Buchhaltungs-Ordner auftaucht.
---

# Buchhaltung PrimärBau GmbH (monatlicher Ablauf)

Ziel: jede Kontobewegung hat ihren Beleg, jeder Monatsordner ist vollständig, und der Steuerberater **Fabian Schmitz, Kanzlei Dornbach (Fabian.Schmitz@dornbach-muc.de)** bekommt die Unterlagen **vor dem 10. des Folgemonats**.

Die konkreten Werte (Firma, Bank, Steuerberater, Frist, Ordnerpfad, Sprache, Kategorien) stehen in **`buchhaltung.config.json`** im Skill-Ordner. Engine und Reminder lesen daraus. Wenn sich etwas ändert (neue Kategorie, zweites Konto, andere Frist), wird die Config angepasst, nicht der Code.

## Was der Steuerberater braucht (4 Kategorien pro Monat)
Ausgangsrechnungen, Eingangsrechnungen, Belege/Ausgaben, Kontoauszug. Dazu, falls vorhanden, **Privatauslagen und Cash** (siehe unten). Übergabe über den vereinbarten Weg (geteilter Ordner oder E-Mail-Entwurf, steht in der Config unter `accountant.handover`).

## PrimärBau: so läuft es hier (Windows, Stand 17.10.2026)

- **Buchungen kommen automatisch** aus der Bankanbindung (`data/data.db`, Tabelle `banking_transactions`, beide Volksbank-Konten, täglich 06:30). Kein Kontoauszug-Export nötig. Ablauf je Monat:
  1. Monat als CSV ablegen: `.venv/Scripts/python.exe -X utf8 .claude/skills/buchhaltung/scripts/bank_export.py 2026-09` (oder `--alle`)
  2. Engine: `.venv/Scripts/python.exe -X utf8 .claude/skills/buchhaltung/scripts/buchungsliste.py "data/buchhaltung/abschluss/2026/09 September/4 Kontoauszug/Kontoauszug_Volksbank_2026-09.csv"`
  Die Engine schreibt `Buchungsliste_2026.csv` für die Monate der übergebenen CSV (überschreibt die vorige Liste).
- **Scan-Eingang:** Luljeta scannt Papierbelege (Kassenbons, Tankbelege, Verträge) nach `C:\PrimaerBau-Belege\Scan-Eingang` (Verknüpfung „PrimaerBau Scan-Eingang“ auf dem Desktop; nicht ins MUBA-OneDrive). Der Mitarbeiter liest die Scans (Bild-PDFs selbst ansehen, die Engine erkennt keinen Text darin), ordnet sie der Bankbuchung zu, kopiert sie mit sprechendem Namen in den Monatsordner (`2 Eingangsrechnungen` oder `3 Ausgaben`) und schiebt das Original nach `Scan-Eingang\erledigt`.
- **Hochladen in DATEV (nur mit Ja je Vorgang):** über **Claude in Chrome** (der eingebaute Browser kann keine Dateien hochladen). Luljeta meldet sich in Chrome per SmartLogin-QR-Code an. Seite `https://upload-online.apps.datev.de/de/461874-45050`, oben die Kategorie wählen (Rechnungseingang / Rechnungsausgang, per Klick auf `.mdc-tab`), Dateien mit `file_upload` auf „Dateien auswählen“, dann „N Dateien übertragen“ klicken. Danach in der Belegübersicht (Posteingang) prüfen, dass sie angekommen sind. Erstmals am 17.10.2026 (4 Belege September).
- **Gescannte Bons zuordnen:** Bilder-PDFs (Scanner ohne Text) seitenweise als PNG rendern und lesen (bei vielen Seiten parallel mit Helfern), je Bon eine TSV-Zeile (bild, haendler, ort, datum, uhrzeit, betrag_brutto, zahlart, karte_endziffern, terminal_id, notiz). Dann `bons_abgleich.py <tsv>`: Betrag + Kaufdatum + Uhrzeit aus dem Verwendungszweck (Treffer meist auf die Minute). Fortsetzungsseiten und EC-Beleg + Kassenbon derselben Zahlung nur einmal zählen bzw. zu einer Datei zusammenfügen. Vor dem Hochladen sprechende Dateinamen (Datum_Geschäft-Ort_Betrag).
- **Kontoauszug abhaken:** `datev_abgleich.py 2026-09 2026-10 <belegliste.tsv>` (Monate **gemeinsam**, damit Monatsrechnungen gleichen Betrags nicht doppelt zählen), dann `kontoauszug_abhaken.py <ziel.xlsx> 2026-09 2026-10 --nachgereicht <hochgeladen.csv> <korrekturen.csv>` → Excel je Monat (grün ✓ in DATEV, grau belegfrei, rot fehlt). Von Hand geprüfte Fälle in `data/buchhaltung/abschluss/2026/korrekturen_abhaken.csv` (Spalten bank_buchung, bank_betrag, datei, status=fehlt).
- **DATEV-Abgleich (nicht mehr blind):** Luljeta meldet sich in DATEV Unternehmen Online im eingebauten Browser an (SmartLogin, sie tippt selbst). Dann Belegübersicht öffnen, den Rahmen `duo-belegebank.apps.datev.de` direkt aufrufen (sonst ist die Liste nicht lesbar), links „Belegablage“ und „Posteingang“ wählen, die Tabelle (SlickGrid, `.slick-viewport`) in 200-px-Schritten durchblättern und Zeilen einsammeln. Ab dem Vormonat als TSV nach `data/buchhaltung/datev/belegliste_JJJJ-MM-TT.tsv` (Spalten Eingangsdatum, Dateiname, Belegdatum, Geschaeftspartner, Betrag, Ablage, Belegtyp). Dann:
  `.venv/Scripts/python.exe -X utf8 .claude/skills/buchhaltung/scripts/datev_abgleich.py 2026-09 data/buchhaltung/datev/belegliste_2026-10-17.tsv`
  Ergebnis `DATEV-Abgleich_JJJJ-MM.csv` im Monatsordner. **Nur lesen, nie hochladen oder löschen.** Treffer stichprobenartig prüfen, besonders gleiche Monatsbeträge (WEG-Rechnungen).
- **Ordnernamen deutsch:** `1 Ausgangsrechnungen`, `2 Eingangsrechnungen`, `3 Ausgaben`, `4 Kontoauszug`, `5 Privat & Bar`. Alles unter `data/` (nie GitHub).
- **Abgabe:** Die Kanzlei Dornbach bucht in DATEV. Belege lädt **Luljeta** in DATEV Unternehmen Online hoch (CEO-GPT lädt nichts hoch). „FEHLT“ in der Buchungsliste heißt „liegt nicht lokal vor“. Was wirklich der Kanzlei fehlt, zeigt erst der DATEV-Abgleich (unten). Abgleich mit der Arbeitsliste `data/buchhaltung/2026-09-fehlende-belege/ARBEITSLISTE.md` und der Fehlliste der Kanzlei.
- **WEG-Dauerrechnungen** (Luljeta 17.10.2026, mit Dornbach geklärt): Hausmeister-Daueraufträge („HSM-Vergütung“) und Raten auf Januar-Jahresrechnungen (xx-01-25/26) brauchen keinen Einzelbeleg, die Jahresrechnung hat die Kanzlei. **Ausnahme:** monatliche Rechnungen „Objektbegehung“ der WEG Schäfflerbachstr. (68, 73, 77 …) brauchen den Beleg.
- **Belegfrei** (Config): Löhne/Gehälter/Vorschüsse (Lohnbuchhaltung), Finanzamt/Finanzkasse/Hauptzollamt/Bundeskasse, AOK, SOKA-BAU (Urlaubs- und Lohnausgleichskasse), Bankentgelte, interne Umbuchungen.

## Schritt 0: Woher kommen die Buchungen?
Dieses Setup beschafft keine Buchungen selbst. Zuerst prüfen, ob eine Quelle angebunden ist:

```
.venv/bin/python .claude/skills/buchhaltung/scripts/check_buchungsquelle.py
```

- **Quelle gefunden** (Collector oder Transaktions-Tabelle): direkt ziehen.
- **Keine Anbindung**: den Nutzer um den Kontoauszug bitten, als **CSV und PDF**, voller Kalendermonat. Die Bankanbindung selbst ist Sache eines separaten Moduls, nicht dieses hier. **Nie selbst ins Banking einloggen.**

## Ordnerstruktur
Wurzel steht in der Config (`folder_root`). Monat zuerst, weil die Abgabe monatsweise läuft:

```
data/buchhaltung/abschluss/{Jahr}/
├── 00 Vertraege & Unterlagen/ (Verträge, Stammdaten, einmalig)
└── {MM Monat}/                (z.B. "05 Mai" oder "05 May", je nach Sprache)
    ├── 1 Ausgangsrechnungen/  (Ausgangsrechnungen + Einnahmen-Belege)
    ├── 2 Eingangsrechnungen/  (Lieferanten-Rechnungen)
    ├── 3 Ausgaben/            (Quittungen ohne formelle Rechnung)
    ├── 4 Kontoauszug/         (Monats-CSV aus der Bankanbindung, PDF optional)
    └── 5 Privat & Bar/        (privat verauslagt / bar bezahlt, ohne Bankzeile)
```

Ein Beleg wird nach dem **Monat seiner Bankbuchung** abgelegt, nicht nach Rechnungsdatum (Grenzfälle nach Buchungsdatum sortieren).

## Inputs holen (Beleg-Beschaffung)
Wo und wie genau steht in **[references/beleg-beschaffung.md](references/beleg-beschaffung.md)**. Kurz:
- **Kontoauszug:** pro Monat CSV UND PDF, jeweils voller Kalendermonat. CSV via `scripts/buchungsliste.py --split` pro Monat in `4 Bank Statements`, PDF daneben als `Kontoauszug_{Bank}_{Jahr}-MM.pdf`.
- **Ausgangsrechnungen + Einnahmen-Belege:** in `1 Sales Invoices`.
- **Eingangsrechnungen:** E-Mail-Suche (falls ein Mail-MCP angebunden ist) und Vendor-Dashboards. **Stripe-gehostete Rechnungen sind in der Browser-Extension oft gesperrt, dann navigiere ich nur hin und der Nutzer lädt selbst.**
- **Logins gibt IMMER der Nutzer ein.** Zugangsdaten/Codes nie im Klartext, nur per sicheren Share-Link.

## Abgleich: jede Bankzeile zu einem Beleg
Das **Bank-CSV ist das Hauptbuch.** Engine: `scripts/buchungsliste.py` (liest Bank-CSV + Beleg-PDFs via PyMuPDF, matcht, schreibt Buchungsliste + Audit). Mit dem Projekt-venv laufen: `.venv/bin/python`.

**Match-Priorität (so vermeidest du Fehltreffer):**
1. **Referenz** zuerst: Rechnungsnummer aus dem Bank-Verwendungszweck im Beleg.
2. **Betrag** (in Kontowährung ODER Originalwährung, wegen Fremdwährungs-Kartenzahlungen).
3. **Firmenname** zuletzt, NUR markante Firmennamen aus `company_keywords`. **Keine Personennamen** allein (sonst Fehltreffer). Eins-zu-eins.

**Bekannte Fallen:**
- **Währungs-Mismatch:** Rechnung in Fremdwährung vs. Buchung in Kontowährung, kein Betrags-Match, über Name/Referenz lösen.
- **Einnahmen ohne Rechnungsbezug:** über das Zahldatum zuordnen.
- **Merchant-Payouts** (z.B. Revolut "From Euro"): eine per Karte bezahlte Rechnung minus Gebühr. Brutto = Ausgangsrechnung, Gebühr = separate Gebühren-Rechnung. NICHT als neue Einnahme zählen.

**Kein Beleg nötig** (steuerbar über `no_receipt_rules` in der Config): eigene Einlagen/Erstattungen, Bankgebühren, Behörden-/Versicherungs-Abbuchungen (dafür gibt es oft keine Rechnung).

## Privatauslagen und Cash
Geschäftliches, das **privat oder bar bezahlt** wurde, taucht **nie im Kontoauszug auf**, gehört aber in die Buchhaltung als **erstattungsfähige Auslage** (der Nutzer legt aus, die Firma schuldet es ihm; der Steuerberater bucht das als Gesellschafterverrechnung).

- Solche Belege kommen in `5 Private & Cash` des jeweiligen Monats.
- Die Engine führt sie in einer **separaten Auslagenliste** (`Auslagen_privat_{Jahr}.csv`), **nicht** gegen die Bank gematcht.
- **Am Monatsende aktiv nachfragen:** "Diesen Monat etwas privat ausgelegt oder bar bezahlt, das geschäftlich ist?" Auch wenn die Antwort oft "nichts" ist. So fällt nichts durch, was nie über die Bank lief.

## Was als vollständig gilt
Ein Monat ist vollständig, wenn:
- **jede Bankzeile** einen Beleg hat ODER belegfrei ist,
- alle vier Kategorien stehen, **inklusive Kontoauszug als CSV UND PDF** (voller Monat) in `4 Bank Statements`,
- Privatauslagen/Cash erfasst (oder bewusst als "keine" bestätigt),
- **keine Rechnung im Ordner liegt, die KEINE Bankbuchung hat** (Ausnahme: bewusst über eine andere Quelle bezahlt, dann zur richtigen Quelle oder zu Privatauslagen).

Buchhaltung ist **nicht eingefroren.** Bei jedem neuen Beleg neu matchen und die Buchungsliste neu ziehen, statt "fertig" zu melden.

## Deliverable: Buchungsliste für den Steuerberater
`scripts/buchungsliste.py` schreibt `Buchungsliste_{Jahr}.csv`: jede Bankzeile mit Datum, Quelle, Gegenpartei, Betrag, **Kategorie-Vorschlag**, **Beleg-Status**, **Beleg-Dateiname** und Notiz. Das nimmt dem Steuerberater die Zuordnung ab.
- Kategorien sind **Vorschläge.** Finale Kontierung und VAT setzt der Steuerberater. Nicht als Steuerberater auftreten, keine verbindliche Steuerberatung geben.
- Um mehr abzunehmen: nach dem **Kontenplan** des Steuerberaters fragen und die Kategorien in der Config darauf ausrichten.

## Kommunikation mit dem Steuerberater
Sprache laut Config (`accountant.language`), knapp, klare Anrede, Signatur. E-Mail-Entwürfe über ein angebundenes Mail-MCP (Entwurf, nicht senden). Zugangsdaten nur per sicheren Share-Link, nie im Klartext, nie im Chat.
