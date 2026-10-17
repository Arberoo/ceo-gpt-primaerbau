#!/usr/bin/env python3
"""
Abgleich Bank-Monat gegen die DATEV-Belegliste (PrimaerBau, 17.10.2026).

CEO-GPT hat keinen festen DATEV-Zugang. Die Belegliste wird bei Bedarf aus
DATEV Unternehmen Online gelesen (Luljeta meldet sich im Browser an, der
Mitarbeiter liest nur) und als TSV unter data/buchhaltung/datev/ abgelegt:
Spalten Eingangsdatum, Dateiname, Belegdatum, Geschaeftspartner, Betrag, Ablage, Belegtyp.

Zuordnung je Bankzeile (eins zu eins, nur lesen):
  1. Nummer aus dem Verwendungszweck steht im DATEV-Dateinamen      -> sicher
  2. Betrag exakt + Belegdatum passt (bis 60 Tage vor der Buchung)  -> sicher
  3. Betrag innerhalb 3,5 % (Skonto) + Name passt + Datum passt       -> wahrscheinlich

    .venv\\Scripts\\python.exe -X utf8 .claude\\skills\\buchhaltung\\scripts\\datev_abgleich.py 2026-09 data\\buchhaltung\\datev\\belegliste_2026-10-17.tsv
Schreibt die Buchungsliste um eine Spalte DATEV ergaenzt nach
abschluss/JJJJ/MM Monat/DATEV-Abgleich_JJJJ-MM.csv und gibt eine Zusammenfassung aus.
"""
import csv
import json
import os
import re
import sys
from datetime import date, datetime

HERE = os.path.dirname(os.path.abspath(__file__))
CFG = json.load(open(os.path.join(os.path.dirname(HERE), "buchhaltung.config.json"), encoding="utf-8"))
MONATE = {"07": "07 Juli", "08": "08 August", "09": "09 September", "10": "10 Oktober",
          "11": "11 November", "12": "12 Dezember", "01": "01 Januar", "02": "02 Februar",
          "03": "03 Maerz", "04": "04 April", "05": "05 Mai", "06": "06 Juni"}
RNR_ROH = re.compile(r"(?<!\d)(\d{1,3})-(\d{2})-(?:20)?(\d{2})(?!\d)")  # Ausgangsrechnungen: 73-09-26 oder RG_70-08-2026


class _Rnr:
    """Rechnungsnummern einheitlich: 70-08-2026 und 70-08-26 sind dieselbe."""
    def findall(self, text):
        return ["-".join(m) for m in RNR_ROH.findall(text or "")]


RNR = _Rnr()
STOPP = {"gmbh", "co", "kg", "ag", "und", "der", "die", "das", "deutschland", "firma", "fa", "e.k.", "ek", "mbh"}
# Kassen-/Tankbons haben bei DATEV oft einen anderen Namen als in der Bank
ALIAS = {"tbg tankstellen": ["aral", "esso", "shell", "jet", "tankstelle", "classic", "schuster"],
         "geb": ["recyclinghof"], "hotel schweizer hof": ["booking"], "strelnik": ["strelink"]}


def d(s):
    s = (s or "").strip()
    for f in ("%d.%m.%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(s, f).date()
        except ValueError:
            pass
    return None


def betrag(s):
    s = (s or "").strip().replace(".", "").replace(",", ".")
    try:
        return abs(float(s))
    except ValueError:
        return None


def woerter(s):
    return {w for w in re.findall(r"[a-zäöüß]{3,}", (s or "").lower()) if w not in STOPP}


def name_passt(bank_text, partner):
    p = (partner or "").lower()
    b = bank_text.lower()
    for k, alias in ALIAS.items():
        if k in p and any(a in b for a in alias):
            return True
    return bool(woerter(partner) & woerter(bank_text))


def main():
    # mehrere Monate gemeinsam: jeder DATEV-Beleg zaehlt nur einmal (Monatsrechnungen gleichen Betrags)
    monate, tsv = sys.argv[1:-1], sys.argv[-1]
    bank = []
    for monat in monate:
        jahr, mm = monat.split("-")
        liste = os.path.join(CFG["folder_root"], jahr, f"Buchungsliste_{jahr}-{mm}.csv")
        if not os.path.exists(liste):
            liste = os.path.join(CFG["folder_root"], jahr, f"Buchungsliste_{jahr}.csv")
        bank += [r for r in csv.DictReader(open(liste, encoding="utf-8")) if r["Datum"].startswith(monat)]
    bank.sort(key=lambda x: x["Datum"])
    datev = list(csv.DictReader(open(tsv, encoding="utf-8"), delimiter="\t"))
    for e in datev:
        e["_betrag"], e["_datum"] = betrag(e["Betrag"]), d(e["Belegdatum"])
        e["_name"] = re.sub(r"[^a-z0-9]", "", e["Dateiname"].lower())
    benutzt = set()

    def merkmale(r):
        bd = d(r["Datum"])
        amt = abs(float(r["Betrag"]))
        text = r["Gegenpartei"]
        # Kundennummern stehen auf jeder Rechnung eines Lieferanten: nie als Treffer
        ohne_kd = re.sub(r"(?i)(kd\.?-?nr\.?|k-nr\.?|kundennr\.?|kundenkonto|kd)\s*:?\s*[A-Za-z0-9/-]+", " ", text)
        roh = re.findall(r"[A-Za-z0-9][A-Za-z0-9/_-]{4,}", ohne_kd)
        teile = [n for t in roh for n in re.split(r"[/-]", t)] + [t.replace("/", "") for t in roh]
        nummern = [re.sub(r"[^a-z0-9]", "", n.lower()) for n in teile]
        nummern = [n for n in nummern if len(n) >= 5 and sum(c.isdigit() for c in n) >= 5]
        eigen = [re.sub(r"[^a-z0-9]", "", i.lower()) for i in CFG.get("own_ibans", [])]
        nummern = [n for n in nummern if not any(n in e for e in eigen) and n != "71160000"]
        rnr = set(RNR.findall(text))
        return bd, amt, text, nummern, rnr

    def datum_ok(bd, e, tage=31):
        # Beleg liegt vor der Buchung (bis 'tage' Tage) oder hoechstens 10 Tage danach
        return e["_datum"] is None or (-10 <= (bd - e["_datum"]).days <= tage)

    def stufe(r, art):
        bd, amt, text, nummern, rnr = merkmale(r)
        for i, e in enumerate(datev):
            if i in benutzt:
                continue
            # Bank nennt Rechnung 73-09-26, der DATEV-Beleg heisst 68-07-26: anderer Monat, anderer Beleg
            e_rnr = set(RNR.findall(e["Dateiname"]))
            if rnr and e_rnr and not (rnr & e_rnr):
                continue
            if art == 1 and rnr and (rnr & e_rnr):
                return i, "sicher (Rechnungsnummer)"
            if art == 1 and nummern and any(n in e["_name"] for n in nummern) and datum_ok(bd, e, 120):
                return i, "sicher (Nummer)"
            if art == 2 and e["_betrag"] and abs(e["_betrag"] - amt) < 0.005 and e["_datum"]                     and datum_ok(bd, e) and (name_passt(text, e["Geschaeftspartner"]) or amt >= 100):
                return i, "sicher (Betrag+Datum)"
            tank = any(k in (e["Geschaeftspartner"] or "").lower() for k in ("tbg", "tankstelle"))
            if art == 3 and not tank and e["_betrag"] and abs(e["_betrag"] - amt) <= 0.035 * amt and datum_ok(bd, e)                     and name_passt(text, e["Geschaeftspartner"]):
                return i, "wahrscheinlich (Skonto/Rundung)"
        return None, ""

    for r in bank:
        r["DATEV"], r["DATEV_Datei"] = ("-" if r["Beleg_Status"] == "kein Beleg noetig" else "NICHT IN DATEV"), ""
    # erst alle sicheren Treffer vergeben, dann die ungefaehren
    for art in (1, 2, 3):
        for r in bank:
            if r["DATEV"] != "NICHT IN DATEV":
                continue
            i, wie = stufe(r, art)
            if i is not None:
                benutzt.add(i)
                e = datev[i]
                r["DATEV"] = f"{e['Ablage']}: {wie}"
                r["DATEV_Datei"] = f"{e['Dateiname']} ({e['Eingangsdatum']})"
    for monat in monate:
        jahr, mm = monat.split("-")
        aus = [r for r in bank if r["Datum"].startswith(monat)]
        ziel = os.path.join(CFG["folder_root"], jahr, MONATE[mm], f"DATEV-Abgleich_{monat}.csv")
        with open(ziel, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(aus[0].keys()))
            w.writeheader()
            w.writerows(aus)
        zaehl = {}
        for r in aus:
            k = r["DATEV"].split(":")[0] if r["DATEV"] not in ("-", "NICHT IN DATEV") else r["DATEV"]
            zaehl[k] = zaehl.get(k, 0) + 1
        print(ziel)
        print(zaehl)


if __name__ == "__main__":
    main()
