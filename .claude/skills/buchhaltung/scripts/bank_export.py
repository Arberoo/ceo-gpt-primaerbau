#!/usr/bin/env python3
"""
Bruecke Bankanbindung -> Buchhaltungs-Engine (PrimaerBau, 17.10.2026).

Die Engine (buchungsliste.py) liest ein Bank-CSV. Die Buchungen kommen hier
aber schon automatisch aus der Bankanbindung (data/data.db, Tabelle
banking_transactions, beide Volksbank-Konten). Dieses Skript schreibt je Monat
eine CSV im Preset 'volksbank_db' in den Monatsordner '4 Kontoauszug'.

Nur gebuchte Umsaetze (status = 'BOOK'). Umbuchungen zwischen den eigenen
Konten bekommen Typ UMBUCHUNG und den Text 'Interne Umbuchung' (belegfrei),
Kontofuehrung/Abschluss bekommt Typ ENTGELT (Bankgebuehr, belegfrei).
LESE-ONLY auf der Datenbank.

    .venv\\Scripts\\python.exe -X utf8 .claude\\skills\\buchhaltung\\scripts\\bank_export.py 2026-09 [2026-10 ...]
    .venv\\Scripts\\python.exe -X utf8 .claude\\skills\\buchhaltung\\scripts\\bank_export.py --alle
"""
import csv
import json
import os
import sqlite3
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
DB = os.path.join(ROOT, "data", "data.db")
CFG = os.path.join(os.path.dirname(HERE), "buchhaltung.config.json")

MONATE = {"01": "01 Januar", "02": "02 Februar", "03": "03 Maerz", "04": "04 April",
          "05": "05 Mai", "06": "06 Juni", "07": "07 Juli", "08": "08 August",
          "09": "09 September", "10": "10 Oktober", "11": "11 November", "12": "12 Dezember"}
SPALTEN = ["Datum", "Konto", "Typ", "Beschreibung", "Referenz", "Betrag", "Gegen-IBAN"]


def sauber(s):
    return " ".join((s or "").split())


def typ_fuer(t, eigene):
    gegen = (t["counterparty_iban"] or "").replace(" ", "")
    zweck = (t["purpose"] or "").lower()
    if gegen in eigene or "interne umbuchung" in zweck:
        return "UMBUCHUNG"
    if not sauber(t["counterparty_name"]) and (zweck.startswith("abschluss per")
                                               or "umsatzsteuer auf eur" in zweck):
        return "ENTGELT"
    return ""


def export(monat, cfg, conn):
    jahr, mm = monat.split("-")
    eigene = {(r[0] or "").replace(" ", "") for r in
              conn.execute("SELECT COALESCE(iban_klar, iban) FROM banking_accounts")}
    rows = conn.execute(
        "SELECT * FROM banking_transactions WHERE status = 'BOOK' AND booking_date LIKE ? "
        "ORDER BY booking_date, iban, amount", (f"{monat}%",)).fetchall()
    ordner = os.path.join(cfg["folder_root"], jahr, MONATE[mm], cfg["folders"]["bank"])
    os.makedirs(ordner, exist_ok=True)
    ziel = os.path.join(ordner, f"Kontoauszug_Volksbank_{monat}.csv")
    with open(ziel, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(SPALTEN)
        for t in rows:
            typ = typ_fuer(t, eigene)
            name, zweck = sauber(t["counterparty_name"]), sauber(t["purpose"])
            beschr = "Interne Umbuchung" if typ == "UMBUCHUNG" else " | ".join(x for x in (name, zweck) if x)
            w.writerow([t["booking_date"], (t["iban"] or "")[-10:], typ, beschr, zweck,
                        f"{t['amount']:.2f}", (t["counterparty_iban"] or "").replace(" ", "")])
    return ziel, len(rows)


def main():
    cfg = json.load(open(CFG, encoding="utf-8"))
    conn = sqlite3.connect(DB, timeout=30)
    conn.row_factory = sqlite3.Row
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if "--alle" in sys.argv:
        args = [r[0] for r in conn.execute(
            "SELECT DISTINCT substr(booking_date, 1, 7) FROM banking_transactions ORDER BY 1")]
    if not args:
        sys.exit("Monat angeben, z. B. 2026-09, oder --alle")
    for m in args:
        ziel, n = export(m, cfg, conn)
        print(f"{m}: {n} Buchungen -> {ziel}")
    conn.close()


if __name__ == "__main__":
    main()
