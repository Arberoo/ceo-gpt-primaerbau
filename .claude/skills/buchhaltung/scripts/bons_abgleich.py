#!/usr/bin/env python3
"""
Gescannte Kassen-/Tankbons gegen Kartenzahlungen im Konto abgleichen (PrimaerBau, 17.10.2026).

Eingabe: eine oder mehrere TSV-Dateien mit den abgelesenen Bons
(Spalten: bild, haendler, ort, datum TT.MM.JJJJ, uhrzeit, betrag_brutto, zahlart,
karte_endziffern, terminal_id, notiz) und die Bankumsaetze aus data/data.db.

Zuordnung (eins zu eins):
  sicher        Betrag exakt + Kaufdatum gleich (aus dem Verwendungszweck) + Uhrzeit +-10 Min
  sicher        Betrag exakt + Kaufdatum gleich (keine Uhrzeit im Zweck)
  wahrscheinlich Betrag exakt + Kaufdatum +-2 Tage
Gutschriften (Rueckgaben) sind im Konto positiv, auf dem Bon negativ.

Ausgabe: CSV neben der ersten TSV (bons_abgleich.csv) + Zusammenfassung.
Nur lesen (Datenbank), schreibt nur die Ergebnisdatei.

    .venv/Scripts/python.exe -X utf8 .claude/skills/buchhaltung/scripts/bons_abgleich.py <tsv> [<tsv> ...]
"""
import csv
import os
import re
import sqlite3
import sys
from datetime import date, datetime

HERE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.abspath(os.path.join(HERE, "..", "..", "..", "..", "data", "data.db"))


def betrag(s):
    s = (s or "").strip().replace("€", "").replace(" ", "")
    if not s or s == "?":
        return None
    neg = s.startswith("-")
    s = s.lstrip("-+")
    if "," in s:
        s = s.replace(".", "").replace(",", ".")
    try:
        v = float(s)
    except ValueError:
        return None
    return -v if neg else v


def tag(s):
    try:
        return datetime.strptime((s or "").strip(), "%d.%m.%Y").date()
    except ValueError:
        return None


def minuten(s):
    m = re.match(r"(\d{1,2})[:.](\d{2})", (s or "").strip())
    return int(m.group(1)) * 60 + int(m.group(2)) if m else None


def kauf_aus_zweck(zweck, buchung):
    """Kaufdatum und -uhrzeit aus dem Verwendungszweck der Kartenzahlung."""
    z = zweck or ""
    m = re.search(r"(\d{2})\.(\d{2})\.(\d{4})\s*(?:um|/)\s*(\d{2}):(\d{2})", z)
    if m:
        return date(int(m[3]), int(m[2]), int(m[1])), int(m[4]) * 60 + int(m[5])
    m = re.search(r"(\d{2})\.(\d{2})\.(\d{4})", z)
    if m:
        return date(int(m[3]), int(m[2]), int(m[1])), None
    m = re.search(r"ELV\d+\s+(\d{2})\.(\d{2})\s+(\d{2})[.:](\d{2})", z)
    if m:
        b = datetime.strptime(buchung, "%Y-%m-%d").date()
        return date(b.year, int(m[2]), int(m[1])), int(m[3]) * 60 + int(m[4])
    return None, None


def main():
    bons = []
    for f in sys.argv[1:]:
        bons += list(csv.DictReader(open(f, encoding="utf-8"), delimiter="\t"))
    con = sqlite3.connect(DB)
    bank = []
    for d, a, n, p in con.execute(
            "SELECT booking_date, amount, counterparty_name, purpose FROM banking_transactions "
            "WHERE status='BOOK' AND booking_date >= '2026-07-01'"):
        kd, km = kauf_aus_zweck(p, d)
        bank.append({"buchung": d, "betrag": a, "name": n or "", "zweck": p or "", "kauf": kd, "uhr": km})
    benutzt = set()
    for b in bons:
        b["_betrag"], b["_tag"], b["_uhr"] = betrag(b.get("betrag_brutto")), tag(b.get("datum")), minuten(b.get("uhrzeit"))
        b["bank_buchung"] = b["bank_betrag"] = b["bank_text"] = ""
        b["status"] = "kein Treffer"

    def versuch(stufe):
        for b in bons:
            if b["status"] != "kein Treffer" or b["_betrag"] is None:
                continue
            for i, k in enumerate(bank):
                if i in benutzt or abs(abs(k["betrag"]) - abs(b["_betrag"])) > 0.005:
                    continue
                if (k["betrag"] > 0) != (b["_betrag"] < 0):  # Gutschrift <-> Rueckgabe
                    continue
                kd = k["kauf"] or datetime.strptime(k["buchung"], "%Y-%m-%d").date()
                if b["_tag"] is None:
                    continue
                diff = abs((kd - b["_tag"]).days)
                if stufe == 1 and not (diff == 0 and k["uhr"] is not None and b["_uhr"] is not None
                                       and abs(k["uhr"] - b["_uhr"]) <= 10):
                    continue
                if stufe == 2 and not (diff == 0 and (k["uhr"] is None or b["_uhr"] is None)):
                    continue
                if stufe == 3 and not diff <= 2:
                    continue
                benutzt.add(i)
                b["status"] = "sicher" if stufe < 3 else "wahrscheinlich"
                b["bank_buchung"], b["bank_betrag"] = k["buchung"], f"{k['betrag']:.2f}"
                b["bank_text"] = (k["name"] + " | " + k["zweck"])[:90]
                break

    for s in (1, 2, 3):
        versuch(s)
    ziel = os.path.join(os.path.dirname(os.path.abspath(sys.argv[1])), "bons_abgleich.csv")
    felder = [k for k in bons[0].keys() if not k.startswith("_")]
    with open(ziel, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=felder, extrasaction="ignore")
        w.writeheader()
        w.writerows(bons)
    from collections import Counter
    print(ziel)
    print(Counter(b["status"] for b in bons))


if __name__ == "__main__":
    main()
