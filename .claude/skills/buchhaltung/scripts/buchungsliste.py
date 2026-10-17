#!/usr/bin/env python3
"""
Generische Buchhaltungs-Engine.

Liest das Bank-CSV (Hauptbuch) einer Quelle, matcht jede Buchung gegen die
abgelegten Beleg-PDFs, schreibt die Buchungsliste fuer den Steuerberater, gibt
einen Audit aus und kann den Kontoauszug pro Monat splitten. Privatauslagen und
Cash werden separat gefuehrt, nicht gegen die Bank gematcht.

Alles Nutzerspezifische kommt aus buchhaltung.config.json (Spalten-Mapping pro
Bank, Kategorien, belegfreie Regeln, Sprache, Ordnernamen). Diese Datei selbst
enthaelt keine personen- oder firmenbezogenen Daten.

Mit dem Projekt-venv laufen (braucht PyMuPDF):
    .venv/bin/python buchungsliste.py [BANK_CSV] [--source NAME] [--split]

Match-Prioritaet: Referenz > Betrag (EUR oder Originalwaehrung) > markanter
Firmenname. Personennamen NICHT als alleiniges Kriterium.
LESE-ONLY ausser dem Schreiben der Buchungsliste-CSV, der Auslagenliste und der
Split-Auszuege (bei --split).
"""
import csv
import re
import glob
import os
import sys
import json

HERE = os.path.dirname(os.path.abspath(__file__))
SEARCH_BASES = [HERE, os.path.dirname(HERE), os.path.dirname(os.path.dirname(HERE)), os.getcwd()]

# PrimaerBau-Anpassung: auch "4165,00" ohne Tausenderpunkt (sonst las die Engine "165,00")
AMT = re.compile(r"\d+(?:[.,]\d{3})*[.,]\d{2}")
# PrimaerBau-Anpassung: Betraege wie "4.000,-" (ohne Cent) gibt es auf Handwerker-Rechnungen
AMT_GLATT = re.compile(r"(\d{1,3}(?:\.\d{3})*),-")
IBAN_TOKEN = re.compile(r"^[a-z]{2}\d{2}[a-z0-9]{10,30}$")
MONAT_JAHR = re.compile(r"^(0[1-9]|1[0-2])20\d\d$")
# Ausdruecklich genannte Rechnungsnummer im Verwendungszweck ("Rechnungsnr: 1225...",
# "RG 20260753", "ReNr 31-2026", "Rg-Nr.34-2026")
RE_NR = re.compile(r"(?:rechnungs?-?nr|rech(?:nung)?|re-?nr|rg-?nr|renr|rg)\b\.?\s*:?\s*([a-z0-9][a-z0-9/_-]{3,})", re.I)

MONTHS = {
    "de": {"01": "01 Januar", "02": "02 Februar", "03": "03 Maerz", "04": "04 April",
           "05": "05 Mai", "06": "06 Juni", "07": "07 Juli", "08": "08 August",
           "09": "09 September", "10": "10 Oktober", "11": "11 November", "12": "12 Dezember"},
    "en": {"01": "01 January", "02": "02 February", "03": "03 March", "04": "04 April",
           "05": "05 May", "06": "06 June", "07": "07 July", "08": "08 August",
           "09": "09 September", "10": "10 October", "11": "11 November", "12": "12 December"},
}

COLS = {
    "de": ["Datum", "Monat", "Quelle", "Typ", "Richtung", "Gegenpartei", "Referenz",
           "Betrag", "Original", "Kategorie_Vorschlag", "Beleg_Status", "Beleg_Datei", "Notiz"],
    "en": ["Date", "Month", "Source", "Type", "Direction", "Counterparty", "Reference",
           "Amount", "Original", "Category_Suggestion", "Receipt_Status", "Receipt_File", "Note"],
}

WORDS = {
    "de": {"in": "Eingang", "out": "Ausgang", "have": "Beleg vorhanden", "miss": "FEHLT",
           "none": "kein Beleg noetig", "fee": "Bankgebuehr", "deposit": "Eigeneinlage Gesellschafter",
           "repay": "Rueckzahlung Eigeneinlage", "income_check": "Umsatz (pruefen)",
           "expense_check": "Ausgabe (pruefen)", "private": "Privatauslage / Cash"},
    "en": {"in": "Inflow", "out": "Outflow", "have": "receipt present", "miss": "MISSING",
           "none": "no receipt needed", "fee": "Bank fee", "deposit": "Owner contribution",
           "repay": "Owner contribution refund", "income_check": "Income (review)",
           "expense_check": "Expense (review)", "private": "Private outlay / cash"},
}


def find_file(names):
    for base in SEARCH_BASES:
        for n in names:
            p = os.path.join(base, n)
            if os.path.exists(p):
                return p
    return None


def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def load_config():
    p = find_file(["buchhaltung.config.json"])
    if not p:
        sys.exit("Keine buchhaltung.config.json gefunden. Erst das Modul installieren "
                 "(/install module-installs/buchhaltung).")
    return load_json(p)


def load_presets():
    p = find_file(["bank-presets.json", "templates/bank-presets.json"])
    return load_json(p).get("presets", {}) if p else {}


def resolve_source(cfg, presets, name=None):
    sources = cfg.get("bank_sources") or []
    if not sources:
        sys.exit("Keine bank_sources in der Config. Bitte im Setup eine Quelle eintragen.")
    src = next((s for s in sources if s.get("name") == name), sources[0]) if name else sources[0]
    preset = presets.get(src.get("preset", "generic"), {})
    colmap = src.get("csv_column_map") or preset.get("csv_column_map", {})
    if not colmap.get("date") or not colmap.get("amount"):
        sys.exit(f"Quelle '{src.get('name')}': csv_column_map unvollstaendig (date/amount fehlen).")
    internal = list(preset.get("internal_patterns", [])) + list(src.get("internal_patterns", []))
    owner = (cfg.get("owner_name") or "").strip().lower()
    if owner and owner != "<inhaber/gesellschafter, fuer erkennung von eigeneinlagen 'from/to <name>'>":
        first = owner.split()[0]
        internal += [f"from {first}", f"to {first}", f"from {owner}", f"to {owner}"]
    legal = (cfg.get("company_legal_name") or "").strip().lower()
    if legal and not legal.startswith("<"):
        internal.append(legal)
    return {"name": src.get("name", "Bank"), "colmap": colmap, "internal": internal,
            "fee_type": src.get("fee_type") or preset.get("fee_type", "FEE")}


def norm(s):
    last = max(s.rfind("."), s.rfind(","))
    if last < 0:
        return None
    try:
        return round(float(re.sub(r"[.,]", "", s[:last]) + "." + re.sub(r"\D", "", s[last + 1:])), 2)
    except ValueError:
        return None


def squeeze(s):
    return re.sub(r"[^a-z0-9]", "", s.lower())


def reftokens(r):
    # PrimaerBau-Anpassung: am Schraegstrich trennen ("RG 16269149012711/07.09.2026",
    # "RE-NR. 73-09-26/07.09.26"), sonst klebt das Datum an der Nummer.
    toks = [t for t in re.findall(r"[A-Za-z0-9][A-Za-z0-9/_-]{3,}", r or "") if sum(c.isdigit() for c in t) >= 3]
    teile = [x for t in toks if "/" in t for x in t.split("/") if len(x) >= 4 and sum(c.isdigit() for c in x) >= 3]
    return toks + teile


def comptoken(desc, keywords):
    d = desc.lower()
    for k in keywords:
        if k and k.lower() in d:
            return k.lower()
    return None


def is_internal(desc, source):
    d = desc.lower()
    return any(p and p in d for p in source["internal"])


def folder_root(cfg):
    return os.path.expanduser(cfg.get("folder_root", ""))


def load_docs(cfg, subfolder):
    out = []
    root, year = folder_root(cfg), cfg.get("year", 2026)
    for p in glob.glob(f"{root}/{year}/*/{subfolder}/*.pdf"):
        t = ""
        try:
            import pymupdf as fitz
            with fitz.open(p) as d:
                for pg in d:
                    t += pg.get_text()
        except Exception:
            pass
        out.append({"name": os.path.basename(p),
                    "low": (os.path.basename(p) + " " + t).lower(),
                    "blob": squeeze(os.path.basename(p) + t),
                    "amts": ({a for a in (norm(m) for m in AMT.findall(t)) if a}
                             | {float(m.replace(".", "")) for m in AMT_GLATT.findall(t)})})
    return out


def parse_bank(path, source):
    cm, rows = source["colmap"], []
    with open(path, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            try:
                eur = float(r[cm["amount"]])
            except (ValueError, KeyError, TypeError):
                continue
            try:
                org = abs(float(r.get(cm.get("orig_amount", ""), "")))
            except (ValueError, KeyError, TypeError):
                org = None
            rows.append({
                "date": (r.get(cm.get("date", ""), "") or "").strip(),
                "type": (r.get(cm.get("type", ""), "") or "").strip(),
                "desc": (r.get(cm.get("description", ""), "") or "").strip(),
                "ref": (r.get(cm.get("reference", ""), "") or "").strip(),
                "eur": eur, "org": org,
                "ccy": (r.get(cm.get("orig_currency", ""), "") or "").strip(),
                "_row": r})
    return rows


EIGENE = []


def eigene_ibans_aus_bank():
    """Eigene IBANs aus der Bankanbindung (data/data.db), damit keine Kontonummern
    in der Config (und damit im Git-Repo) stehen muessen."""
    import sqlite3
    for base in SEARCH_BASES:
        db = os.path.join(base, "data", "data.db")
        if os.path.exists(db):
            try:
                con = sqlite3.connect(db)
                rows = con.execute("SELECT COALESCE(iban_klar, iban) FROM banking_accounts").fetchall()
                con.close()
                return [squeeze(r[0] or "") for r in rows if r[0]]
            except Exception:
                return []
    return []


def match(txns, idxs, pool):
    """PrimaerBau-Anpassung (17.10.2026): Punkte statt erstes Kriterium.

    Das Original nahm jede Ziffernfolge >= 4 Zeichen als Referenz (Score 100).
    In deutschen Verwendungszwecken traf damit die Jahreszahl, "09/2026" oder
    die Lieferanten-IBAN jeden Beleg. Jetzt:
      Nummer aus dem Zweck (keine IBAN, kein Monat/Jahr, >= 5)      70
        +10 je weitere passende Nummer, +20 wenn im Dateinamen
      Lieferanten-IBAN im Beleg                                     40
      Betrag exakt                                                  50
      Firmenname als ganzes Wort                                    30
    Zugeordnet wird erst ab 80 Punkten, also immer mit Bestaetigung
    (z. B. Nummer + Betrag, IBAN + Betrag, Nummer im Dateinamen). Lieber "fehlt" als eine falsche Zuordnung."""
    cands = []
    # Eigene IBANs (inkl. BLZ und Kontonummer darin) sind nie eine Rechnungsnummer:
    # sie stehen auf jedem Lastschrift-Beleg und in vielen Verwendungszwecken.
    global EIGENE
    for ti in idxs:
        t = txns[ti]
        toks = [squeeze(x) for x in reftokens(t["ref"])]
        rts = list(dict.fromkeys(r for r in toks if len(r) >= 5 and not IBAN_TOKEN.match(r)
                                 and not MONAT_JAHR.match(r)
                                 and not any(r in eigen for eigen in EIGENE)))
        genannt = [squeeze(x.split("/")[0]) for x in RE_NR.findall(t["ref"])]
        genannt = [g for g in genannt if len(g) >= 4 and sum(c.isdigit() for c in g) >= 3]
        ibans = [r for r in toks if IBAN_TOKEN.match(r)]
        camt = {round(abs(t["eur"]), 2)} | ({round(t["org"], 2)} if t["org"] else set())
        comp = t.get("_comp")
        comp_re = re.compile(r"\b" + re.escape(comp.strip()) + r"\b") if comp else None
        for di, p in enumerate(pool):
            sc = 0
            treffer = [r for r in rts if r in p["blob"]]
            if treffer:
                # mehr passende Nummern = sicherer; Nummer im Dateinamen = Bonus
                name = squeeze(p["name"])
                # Nummer allein = 70 (unter der Schwelle): Kundennummern stehen auf
                # JEDER Rechnung eines Lieferanten. Erst Betrag oder Dateiname bestaetigen.
                sc += 70 + 10 * (len(treffer) - 1) + (20 if any(r in name for r in treffer) else 0)
            if any(i in p["blob"] for i in ibans):
                sc += 40
            if p["amts"] & camt:
                sc += 50
            if comp_re and comp_re.search(p["low"]):
                sc += 30
            # Die Bank nennt eine bestimmte Rechnung, der Beleg enthaelt sie nicht:
            # dann ist es eine andere Rechnung desselben Lieferanten, Beleg ausgeschlossen.
            if genannt and not any(g in p["blob"] for g in genannt):
                continue
            if sc >= 80:
                cands.append((sc, ti, di))
    cands.sort(reverse=True)
    res, used = {}, set()
    for sc, ti, di in cands:
        if ti in res or di in used:
            continue
        res[ti] = di
        used.add(di)
    return res


def categorize(t, inc, cfg, source):
    d, w = t["desc"].lower(), WORDS[cfg.get("language", "de")]
    if is_internal(t["desc"], source):
        # PrimaerBau-Anpassung: Umbuchung zwischen eigenen Konten ist weder
        # Eigeneinlage noch Rueckzahlung ("konto " enthaelt sonst "to ").
        if "umbuchung" in d:
            return "Umbuchung eigene Konten", True
        return (w["repay"] if ("refund" in d or "to " in d) else w["deposit"]), True
    if source["fee_type"] and t["type"] == source["fee_type"]:
        return w["fee"], True
    auth = [k.lower() for k in cfg.get("no_receipt_rules", {}).get("authority_keywords", [])]
    for k in auth:
        if k and k in d:
            return k.title(), True
    rules = cfg.get("categories", {}).get("income" if inc else "expense", [])
    for rule in rules:
        mref = rule.get("match_reference")
        if mref and not mref.startswith("<") and re.search(re.escape(mref), t["ref"], re.I):
            return rule["label"], bool(rule.get("no_receipt"))
        for kw in rule.get("match_description", []):
            if kw and not kw.startswith("<") and kw.lower() in d:
                return rule["label"], bool(rule.get("no_receipt"))
    return (w["income_check"] if inc else w["expense_check"]), False


def split_statement(txns, cfg, source):
    root, year, lang = folder_root(cfg), cfg.get("year", 2026), cfg.get("language", "de")
    bankdir = cfg.get("folders", {}).get("bank", "4 Bank Statements")
    by = {}
    for t in txns:
        by.setdefault(t["date"][5:7], []).append(t)
    for mk, rs in sorted(by.items()):
        if mk not in MONTHS[lang]:
            continue
        folder = f"{root}/{year}/{MONTHS[lang][mk]}/{bankdir}"
        os.makedirs(folder, exist_ok=True)
        hdr = list(rs[0]["_row"].keys())
        safe = re.sub(r"[^A-Za-z0-9]", "_", source["name"])
        with open(f"{folder}/Kontoauszug_{safe}_{year}-{mk}.csv", "w", newline="", encoding="utf-8") as f:
            wri = csv.DictWriter(f, fieldnames=hdr)
            wri.writeheader()
            for t in sorted(rs, key=lambda x: x["date"]):
                wri.writerow(t["_row"])
        print(f"  Kontoauszug {MONTHS[lang][mk]}: {len(rs)} Buchungen geschrieben")


def write_private_list(cfg):
    """Privatauslagen / Cash separat erfassen, NICHT gegen die Bank matchen."""
    pe = cfg.get("private_expenses", {})
    if not pe.get("enabled"):
        return None
    root, year, lang = folder_root(cfg), cfg.get("year", 2026), cfg.get("language", "de")
    sub = pe.get("folder", "5 Private & Cash")
    docs = []
    for mk in sorted(MONTHS[lang]):
        folder = f"{root}/{year}/{MONTHS[lang][mk]}/{sub}"
        for p in glob.glob(f"{folder}/*"):
            if os.path.isdir(p):
                continue
            amt = ""
            if p.lower().endswith(".pdf"):
                try:
                    import pymupdf as fitz
                    t = ""
                    with fitz.open(p) as d:
                        for pg in d:
                            t += pg.get_text()
                    vals = [a for a in (norm(m) for m in AMT.findall(t)) if a]
                    amt = f"{max(vals):.2f}" if vals else ""
                except Exception:
                    pass
            docs.append({"month": MONTHS[lang][mk], "file": os.path.basename(p), "amount": amt})
    out = f"{root}/{year}/" + pe.get("list_file", "Auslagen_privat_{year}.csv").replace("{year}", str(year))
    cols = (["Monat", "Datei", "Betrag_geschaetzt", "Notiz"] if lang == "de"
            else ["Month", "File", "Amount_estimated", "Note"])
    with open(out, "w", newline="", encoding="utf-8") as f:
        wri = csv.writer(f)
        wri.writerow(cols)
        for d in docs:
            wri.writerow([d["month"], d["file"], d["amount"], ""])
    return out, len(docs)


def main():
    cfg = load_config()
    presets = load_presets()
    global EIGENE
    EIGENE = [squeeze(i) for i in cfg.get("own_ibans", [])] + eigene_ibans_aus_bank()
    lang = cfg.get("language", "de")
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    do_split = "--split" in sys.argv
    src_name = None
    if "--source" in sys.argv:
        i = sys.argv.index("--source")
        src_name = sys.argv[i + 1] if i + 1 < len(sys.argv) else None
        args = [a for a in args if a != src_name]
    source = resolve_source(cfg, presets, src_name)

    bank = args[0] if args else None
    if not bank or not os.path.exists(bank):
        sys.exit("Keine Bank-CSV gefunden. Pfad als 1. Argument angeben.")

    txns = parse_bank(bank, source)
    keywords = cfg.get("company_keywords", [])
    for t in txns:
        t["_comp"] = comptoken(t["desc"], keywords)

    if do_split:
        print("Splitte Kontoauszug pro Monat:")
        split_statement(txns, cfg, source)
        print()

    sales = load_docs(cfg, cfg.get("folders", {}).get("sales", "1 Sales Invoices"))
    costs = (load_docs(cfg, cfg.get("folders", {}).get("purchases", "2 Purchase Invoices"))
             + load_docs(cfg, cfg.get("folders", {}).get("expenses", "3 Expenses")))
    months = sorted({t["date"][5:7] for t in txns if t["date"][5:7] in MONTHS[lang]})

    inc = [i for i, t in enumerate(txns) if t["date"][5:7] in MONTHS[lang] and t["eur"] > 0 and not is_internal(t["desc"], source)]
    exp = [i for i, t in enumerate(txns) if t["date"][5:7] in MONTHS[lang] and t["eur"] < 0 and not is_internal(t["desc"], source)
           and t["type"] != source["fee_type"]]
    mi, me = match(txns, inc, sales), match(txns, exp, costs)

    w = WORDS[lang]
    rows, audit = [], {m: {"ok": 0, "nodoc": 0, "miss": []} for m in months}
    for i, t in enumerate(txns):
        mk = t["date"][5:7]
        if mk not in MONTHS[lang]:
            continue
        incf = t["eur"] > 0
        kat, nodoc = categorize(t, incf, cfg, source)
        if nodoc:
            status, beleg = w["none"], ""
            audit[mk]["nodoc"] += 1
        elif incf and i in mi:
            status, beleg = w["have"], sales[mi[i]]["name"]
            audit[mk]["ok"] += 1
        elif (not incf) and i in me:
            status, beleg = w["have"], costs[me[i]]["name"]
            audit[mk]["ok"] += 1
        else:
            status, beleg = w["miss"], ""
            audit[mk]["miss"].append(f"{t['date']} {t['eur']:.2f} {t['desc'][:32]}")
        vals = [t["date"], MONTHS[lang][mk], source["name"], t["type"], w["in"] if incf else w["out"],
                t["desc"], t["ref"], f"{t['eur']:.2f}",
                (f"{t['org']:.2f} {t['ccy']}" if t["org"] and t["ccy"] not in ("", cfg.get("currency", "EUR")) else ""),
                kat, status, beleg, ""]
        rows.append(dict(zip(COLS[lang], vals)))

    rows.sort(key=lambda r: (r[COLS[lang][1]], r[COLS[lang][0]]))
    out = f"{folder_root(cfg)}/{cfg.get('year', 2026)}/Buchungsliste_{cfg.get('year', 2026)}.csv"
    with open(out, "w", newline="", encoding="utf-8") as f:
        wri = csv.DictWriter(f, fieldnames=COLS[lang])
        wri.writeheader()
        wri.writerows(rows)
    print(f"Buchungsliste: {out}  ({len(rows)} Buchungen)\n")

    bankdir = cfg.get("folders", {}).get("bank", "4 Bank Statements")
    for mk in months:
        a = audit[mk]
        bd = f"{folder_root(cfg)}/{cfg.get('year', 2026)}/{MONTHS[lang][mk]}/{bankdir}"
        csv_da = "DA" if glob.glob(f"{bd}/*.csv") else "FEHLT"
        pdf_da = "DA" if glob.glob(f"{bd}/*.pdf") else "FEHLT"
        print(f"{MONTHS[lang][mk]}: {a['ok']} mit Beleg, {a['nodoc']} belegfrei, {len(a['miss'])} FEHLEN | "
              f"Kontoauszug CSV {csv_da}, PDF {pdf_da}")
        for m in a["miss"]:
            print(f"    !!! {m}")

    priv = write_private_list(cfg)
    if priv:
        print(f"\n{w['private']}: {priv[1]} Posten erfasst -> {os.path.basename(priv[0])} "
              f"(separat, nicht gegen die Bank gematcht)")


if __name__ == "__main__":
    main()
