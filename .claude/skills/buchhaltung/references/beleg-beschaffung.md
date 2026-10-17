# Beleg-Beschaffung (wo und wie)

Wie die Belege für jeden Monat zusammenkommen. Reihenfolge: erst das automatisch/lokal Vorhandene matchen, dann gezielt die Lücken holen.

## Kontoauszug (Bank movement)
Der Steuerberater braucht pro Monat **beide Formate**, jeweils voller Kalendermonat (1. bis letzter Tag, erster Monat ab Kontoeröffnung):
- **CSV** (Hauptbuch zum Matchen): im Online-Banking den Transaktions-Export als CSV ziehen. `scripts/buchungsliste.py --split` teilt es per Buchungsmonat in die `4 Bank Statements`-Ordner. Das Spalten-Mapping pro Bank steht in der Config (`bank_sources`).
- **PDF** (offizieller Beleg): den Monats-PDF-Auszug exportieren und als `Kontoauszug_{Bank}_{Jahr}-MM.pdf` in denselben `4 Bank Statements`-Ordner legen.

Beide Exporte macht der Nutzer selbst, **nie ins Banking einloggen.** Der Audit von `buchungsliste.py` meldet CSV und PDF getrennt, ein fehlendes PDF fällt sofort auf. Ist eine Bankanbindung vorhanden (separates Modul), kann das CEO-GPT die CSV direkt ziehen, das PDF bleibt manuell.

## Ausgangsrechnungen + Einnahmen
- **Eigene Rechnungen:** der Nutzer stellt sie aus (Rechnungstool oder Bank-Invoicing), als PDF exportieren in `1 Sales Invoices`. Dateiname trägt am besten die Rechnungsnummer.
- **Plattform-Einnahmen** (z.B. Community, Affiliate, Marktplatz): die Payout-/Auszahlungs-Belege der jeweiligen Plattform, ebenfalls in `1 Sales Invoices`. Achtung auf Brutto/Netto und Fremdwährung.

## Eingangsrechnungen über E-Mail
Falls ein Mail-MCP angebunden ist: gezielt nach Vendor + (receipt/invoice/Rechnung/Beleg) suchen. Belege liegen oft über mehrere Adressen verstreut (Haupt-, Team-, Plus-Adressen). **Viele Quittungen stehen im Mailtext ohne PDF-Anhang**, dann die Mail als PDF sichern statt einen Anhang zu suchen.

## Eingangsrechnungen über Vendor-Dashboards (Browser)
Pro Anbieter im Billing-/Rechnungsbereich die Rechnung öffnen und als PDF herunterladen.

WICHTIG: **Stripe-gehostete Rechnungen (`invoice.stripe.com`, `billing.stripe.com`) sind in der Browser-Extension häufig gesperrt**, und per curl kommt nur die JS-Hülle. Dann gilt: **ich navigiere zur Rechnung, der Nutzer klickt Download.** Logins gibt immer der Nutzer ein. Welche Anbieter über Stripe laufen und wo genau der Download sitzt, hält man sich am besten pro Setup als kurze Liste fest (wächst mit der Zeit).

Nach dem Download: PDF prüfen (Betrag/Datum), sauber benennen, in `{Monat}/{Kategorie}` einsortieren, `buchungsliste.py` neu laufen lassen.

## Privatauslagen und Cash
Geschäftliches, das **privat oder bar** bezahlt wurde, hat keine Bankzeile, gehört aber rein:
- Beleg (Quittung, Rechnung, Kassenbon als Foto/PDF) in `5 Private & Cash` des jeweiligen Monats.
- Die Engine listet sie separat in `Auslagen_privat_{Jahr}.csv`, nicht gegen die Bank gematcht.
- Am Monatsende aktiv abfragen, ob es solche Posten gab.

## Zugangsdaten / Codes
Nie im Klartext, nie im Chat. Der Nutzer teilt sie über einen sicheren Share-Link mit Ablauf, der in einen Entwurf eingesetzt wird. Nie selbst Logins oder Codes eingeben.
