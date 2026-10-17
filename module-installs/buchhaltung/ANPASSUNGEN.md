# Anpassungen PrimärBau – Buchhaltung v1

Stand 17.10.2026 (Arber). Installiert nach `.claude/skills/buchhaltung/`. Hier steht jede Abweichung vom Modul, damit ein Update sauber nachgezogen werden kann.

## Einrichtung

| Punkt | PrimärBau |
|---|---|
| Quelle (`SOURCE_MODE`) | **auto**: Bankanbindung (`module-installs/bank-anbindung`), Tabelle `banking_transactions`, beide Volksbank-Konten |
| Ordner | `data/buchhaltung/abschluss/{Jahr}/{MM Monat}/` (lokal, nie GitHub), deutsche Unterordner `1 Ausgangsrechnungen` … `5 Privat & Bar` |
| Steuerberater | Fabian Schmitz, Kanzlei Dornbach; Abgabe über DATEV Unternehmen Online (Luljeta lädt hoch), Frist 10. des übernächsten Monats laut Kanzlei (September → 10.11.) |
| Reminder | aus (keine Stimme installiert); launchd-Vorlage nicht genutzt |
| PyMuPDF | war schon installiert; Import als `pymupdf` statt `fitz` (Warnung) |

## Neu

- `scripts/bank_export.py`: schreibt je Monat `4 Kontoauszug/Kontoauszug_Volksbank_JJJJ-MM.csv` aus `data.db` (nur `status='BOOK'`). Umbuchungen zwischen eigenen Konten → Typ `UMBUCHUNG` / Text „Interne Umbuchung“, Kontoabschluss → Typ `ENTGELT`.
- Preset `volksbank_db` in `bank-presets.json` (Spalten Datum, Typ, Beschreibung, Referenz, Betrag).
- Eigene IBANs liest die Engine aus `banking_accounts` in `data/data.db` (nicht in der Config, damit keine Kontonummern ins Repo gehen) und schliesst sie von der Zuordnung aus.

## Engine `buchungsliste.py`: Zuordnung umgebaut

Das Original nahm jede Ziffernfolge ab 4 Zeichen als Referenz (sofort 100 Punkte, eins zu eins in absteigender Reihenfolge). Mit deutschen Verwendungszwecken ergab das im ersten Lauf **18 Fehlzuordnungen von 20** („2026“, „09/2026“, Lieferanten-IBAN, Kundennummern, eigene BLZ/Kontonummer, „obi“ in „Mobilfunk“). Jetzt Punkte, Zuordnung erst ab 80:

| Merkmal | Punkte |
|---|---|
| Nummer aus dem Zweck (≥ 5 Zeichen, keine IBAN, kein Monat/Jahr, nicht Teil einer eigenen IBAN) | 70, +10 je weitere Nummer, +20 wenn im Dateinamen |
| Lieferanten-IBAN im Beleg | 40 |
| Betrag exakt (auch „4165,00“ und „4.000,-“) | 50 |
| Firmenstichwort als ganzes Wort | 30 |
| Bank nennt Rechnungsnummer („Rechnungsnr“, „RG“, „ReNr“, „Rg-Nr“), Beleg enthält sie nicht | Beleg ausgeschlossen |

Weitere Änderungen: Nummern am Schrägstrich getrennt („RG 16269149012711/07.09.2026“), interne Umbuchung heißt „Umbuchung eigene Konten“ statt Eigeneinlage/Rückzahlung.

Ergebnis September: 18 Zuordnungen, alle von Hand geprüft und richtig. Grenze: Scans ohne Text (z. B. Vodafone 18.09.) werden nicht erkannt, Texterkennung fehlt noch.

## Bei einem Modul-Update

`match()`, `reftokens()`, `AMT`/`AMT_GLATT`, `RE_NR`, `EIGENE` und den Umbuchungs-Zweig in `categorize()` übernehmen (markiert mit „PrimaerBau-Anpassung“), danach September neu laufen lassen und die Treffer gegen `data/buchhaltung/abschluss/2026/09 September/ABGLEICH-SEPTEMBER.md` prüfen.
