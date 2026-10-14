---
name: buchhaltung
description: Monatlicher Buchhaltungs-Workflow für {{FIRMA}} (Bank {{BANK}}). Ordnet jede Kontobewegung ihrem Beleg zu, holt fehlende Rechnungen, erfasst Privatauslagen und Cash, erzeugt die Buchungsliste für den Steuerberater und sagt, was als vollständig gilt. Use when working on Buchhaltung, Monatsabschluss, Belege/Rechnungen/Kontoauszug zuordnen, "was fehlt noch für den Steuerberater", Privatauslagen, VAT/Umsatzsteuer-Unterlagen, oder wenn ein neuer Beleg im Buchhaltungs-Ordner auftaucht.
---

# Buchhaltung {{FIRMA}} (monatlicher Ablauf)

Ziel: jede Kontobewegung hat ihren Beleg, jeder Monatsordner ist vollständig, und der Steuerberater **{{STEUERBERATER}} ({{STB_EMAIL}})** bekommt die Unterlagen **vor dem {{FRIST_TAG}}. des Folgemonats**.

Die konkreten Werte (Firma, Bank, Steuerberater, Frist, Ordnerpfad, Sprache, Kategorien) stehen in **`buchhaltung.config.json`** im Skill-Ordner. Engine und Reminder lesen daraus. Wenn sich etwas ändert (neue Kategorie, zweites Konto, andere Frist), wird die Config angepasst, nicht der Code.

## Was der Steuerberater braucht (4 Kategorien pro Monat)
Ausgangsrechnungen, Eingangsrechnungen, Belege/Ausgaben, Kontoauszug. Dazu, falls vorhanden, **Privatauslagen und Cash** (siehe unten). Übergabe über den vereinbarten Weg (geteilter Ordner oder E-Mail-Entwurf, steht in der Config unter `accountant.handover`).

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
{{ORDNER_ROOT}}/{Jahr}/
├── 00 Contracts & Records/    (Verträge, Stammdaten, einmalig)
└── {MM Monat}/                (z.B. "05 Mai" oder "05 May", je nach Sprache)
    ├── 1 Sales Invoices/      (Ausgangsrechnungen + Einnahmen-Belege)
    ├── 2 Purchase Invoices/   (Lieferanten-Rechnungen)
    ├── 3 Expenses/            (Quittungen ohne formelle Rechnung)
    ├── 4 Bank Statements/     (Monats-Kontoauszug: CSV + PDF, voller Monat)
    └── 5 Private & Cash/      (privat verauslagt / bar bezahlt, ohne Bankzeile)
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
