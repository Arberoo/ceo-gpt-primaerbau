"""
DataOS - Banking Collector (read-only, zwei Wege)

Liest Salden + Umsaetze der eingerichteten Bankkonten und schreibt sie ins
data.db-Warehouse. Wird vom Orchestrator (collect.py) automatisch entdeckt
(collect_*.py).

ZWEI WEGE, EINE TABELLENFAMILIE (seit 2026-08-31):
  * FinTS/HBCI  ueber python-fints, fuer deutsche Banken.
  * PSD2        ueber Enable Banking, fuer Neobanken, EU-Ausland, PayPal und
                deutsche Banken ohne FinTS.
Beide Wege fuellen DIESELBEN vier Listen und landen in DENSELBEN Tabellen.
Wer die Zahlen liest, muss nicht wissen, wie sie hereingekommen sind -- die
Spalte 'weg' sagt es trotzdem, damit ein Fehler zuzuordnen bleibt.

EIN GESCHEITERTER WEG KIPPT DEN ANDEREN NICHT. Faellt eine Bank aus oder fehlt
eine Bibliothek, landet das in sync_state und der Lauf geht weiter. Sonst
nimmt eine kaputte Bank alle anderen mit.

HEADLESS: blockiert nie auf Eingaben. Erst-Setup, TAN und PSD2-Freigabe laufen
ueber scripts/banking/setup.py. Verlangt eine Bank eine neue SCA/TAN (z.B. nach
~180 Tagen), wird das als needs_tan gemeldet, ohne die Pipeline zu brechen.

KEIN POLLING. Banken drosseln den PSD2-Weg auf ~4 Abrufe pro Tag, wenn niemand
aktiv dabei ist. Dieser Sammler laeuft EINMAL taeglich im DataOS-Lauf mit. Wer
ihn oefter anstoesst, verbrennt das Tagesbudget und bekommt HTTP 429.

Tabellen: banking_accounts, banking_balances, banking_transactions, banking_sync_state
Setup:    python scripts/banking/setup.py assistent
Re-Auth:  python scripts/banking/setup.py reauth <BLZ>        (FinTS)
          python scripts/banking/setup.py psd2-reauth <NAME>  (PSD2)
"""
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from banking import config_store


def _leer():
    return [], [], [], []


# ---- Weg 1: FinTS ---------------------------------------------------
def _sammle_fints(banks):
    """Unveraendert gegenueber der Fassung vor dem zweiten Weg."""
    if not banks:
        return _leer()

    from banking import session as session_store
    from banking import client as bank_client
    from banking import tan  # nur login_tan_pending(): fragt nichts, prompt-frei

    accounts_out, balances_out, txns_out, sync_state = [], [], [], []

    for bank in banks:
        blz = bank.get("blz")
        label = bank.get("label", blz)
        blob = session_store.load(bank.get("session_file", ""))
        if not blob:
            sync_state.append(
                {"blz": blz, "weg": "fints", "needs_tan": 1,
                 "message": f"Keine Session. setup.py reauth {blz} ausfuehren."}
            )
            continue

        try:
            c = bank_client.build_client(bank, from_data=blob)
            tan_needed = False
            with c:
                # Manche Banken verlangen schon fuers ANMELDEN eine TAN. Die
                # legt python-fints als init_tan_response ab, nicht als
                # Rueckgabe von get_sepa_accounts(). Wer nur letzteres prueft,
                # laeuft in einen abgebrochenen Dialog mit unklarem Fehler.
                # Headless kann niemand eine TAN eingeben, also sauber melden.
                if tan.login_tan_pending(c):
                    sync_state.append(
                        {"blz": blz, "weg": "fints", "needs_tan": 1,
                         "message": f"Bank verlangt eine TAN schon fuers Anmelden. "
                                    f"setup.py reauth {blz}"}
                    )
                    continue
                accs = bank_client.fetch_accounts(c)
                if accs is None:
                    sync_state.append(
                        {"blz": blz, "weg": "fints", "needs_tan": 1,
                         "message": f"Bank verlangt neue TAN (SCA). setup.py reauth {blz}"}
                    )
                    tan_needed = True
                else:
                    for a in accs:
                        iban = a["iban"]
                        accounts_out.append(
                            {"iban": iban, "bank_label": label, "blz": blz,
                             "bic": a.get("bic", ""), "currency": "EUR",
                             "weg": "fints", "institut": label, "land": "DE",
                             "konto_name": None, "iban_klar": iban}
                        )
                        bal = bank_client.fetch_balance(c, a["_obj"])
                        if bal is None:
                            sync_state.append(
                                {"blz": blz, "weg": "fints", "needs_tan": 1,
                                 "message": f"TAN fuer Saldo noetig. setup.py reauth {blz}"}
                            )
                            tan_needed = True
                            break
                        balances_out.append(
                            {"iban": iban, "balance": bal["amount"],
                             "currency": bal["currency"], "art": "FINTS"}
                        )
                        txns = bank_client.fetch_transactions(
                            c, a["_obj"], days=bank.get("fetch_days", 90)
                        )
                        if txns is None:
                            sync_state.append(
                                {"blz": blz, "weg": "fints", "needs_tan": 1,
                                 "message": f"TAN fuer Umsaetze noetig. setup.py reauth {blz}"}
                            )
                            tan_needed = True
                            break
                        for t in txns:
                            t["iban"] = iban
                            # FinTS liefert ausschliesslich gebuchte Umsaetze.
                            t.setdefault("status", "BOOK")
                            t.setdefault("weg", "fints")
                            txns_out.append(t)

            # Aktualisierte Session zuruecksichern (nur wenn keine TAN offen)
            if not tan_needed:
                try:
                    session_store.save(
                        bank["session_file"], c.deconstruct(including_private=True)
                    )
                except Exception:
                    pass
                sync_state.append({"blz": blz, "weg": "fints", "needs_tan": 0,
                                   "message": ""})

        except Exception as e:
            sync_state.append(
                {"blz": blz, "weg": "fints", "needs_tan": 0,
                 "message": f"Fehler: {type(e).__name__}: {e}"}
            )

    return accounts_out, balances_out, txns_out, sync_state


# ---- Weg 2: PSD2 ----------------------------------------------------
def _sammle_psd2(verbindungen, heute=None):
    if not verbindungen:
        return _leer()

    try:
        from banking import psd2
    except ImportError as e:
        return [], [], [], [
            {"blz": config_store.bank_key(v), "weg": "psd2", "needs_tan": 0,
             "message": f"PSD2-Weg nicht ladbar: {e}"} for v in verbindungen
        ]

    accounts_out, balances_out, txns_out, sync_state = [], [], [], []
    heute = heute or date.today()

    for v in verbindungen:
        key = config_store.bank_key(v)
        label = v.get("label") or key
        s = psd2.session(key)
        if not s:
            sync_state.append(
                {"blz": key, "weg": "psd2", "needs_tan": 1,
                 "message": f"Keine Freigabe. setup.py psd2-reauth {key}"}
            )
            continue

        rest = psd2.rest_tage(s.get("gueltig_bis"))
        if rest is not None and rest < 0:
            sync_state.append(
                {"blz": key, "weg": "psd2", "needs_tan": 1,
                 "gueltig_bis": s.get("gueltig_bis"), "rest_tage": rest,
                 "message": f"Freigabe abgelaufen. setup.py psd2-reauth {key}"}
            )
            continue

        konten = s.get("konten") or []
        if not konten:
            sync_state.append(
                {"blz": key, "weg": "psd2", "needs_tan": 1,
                 "gueltig_bis": s.get("gueltig_bis"), "rest_tage": rest,
                 "message": "Freigabe steht, aber die Bank gibt kein Konto heraus. "
                            "Meist fehlt 'Link accounts' im Control Panel."}
            )
            continue

        try:
            schluessel = psd2.schluessel_vergeben(
                key, konten, melden=lambda t: print(f"  HINWEIS: {t}"))
            tage = int(v.get("fetch_days", 90) or 90)
            von = (heute - timedelta(days=tage)).isoformat()

            for k, sk in zip(konten, schluessel):
                accounts_out.append({
                    "iban": sk,
                    "bank_label": label,
                    "blz": "",  # PSD2-Banken haben keine BLZ
                    "bic": v.get("bic", ""),
                    "currency": k.get("currency") or "EUR",
                    "weg": "psd2",
                    "institut": v.get("institut") or label,
                    "land": v.get("land"),
                    "konto_name": k.get("name"),
                    "iban_klar": k.get("iban"),
                })

                bal = psd2.massgeblicher_saldo(psd2.balances(k["uid"]))
                if bal:
                    balances_out.append({
                        "iban": sk, "balance": bal["betrag"],
                        "currency": bal["currency"], "art": bal["art"],
                    })

                roh = psd2.transactions(k["uid"], date_from=von)
                for t in roh:
                    if not psd2.im_fenster(t, von):
                        continue
                    txns_out.append(psd2.umsatz_flach(sk, t))

            sync_state.append({
                "blz": key, "weg": "psd2", "needs_tan": 0, "message": "",
                "gueltig_bis": s.get("gueltig_bis"), "rest_tage": rest,
            })
            if rest is not None and rest < 14:
                sync_state[-1]["message"] = (
                    f"Freigabe laeuft in {rest} Tagen ab. "
                    f"setup.py psd2-reauth {key}")

        except Exception as e:
            sync_state.append(
                {"blz": key, "weg": "psd2", "needs_tan": 0,
                 "gueltig_bis": s.get("gueltig_bis"), "rest_tage": rest,
                 "message": f"Fehler: {type(e).__name__}: {e}"}
            )

    return accounts_out, balances_out, txns_out, sync_state


# ---- Zusammenfuehren ------------------------------------------------
def collect():
    alle = config_store.load().get("banks", [])
    if not alle:
        return {
            "source": "banking",
            "status": "skipped",
            "reason": "Keine Bank eingerichtet (python scripts/banking/setup.py assistent)",
        }

    fints = [b for b in alle if config_store.bank_weg(b) == config_store.WEG_FINTS]
    psd2_ = [b for b in alle if config_store.bank_weg(b) == config_store.WEG_PSD2]

    a1, b1, t1, s1 = _sammle_fints(fints)
    a2, b2, t2, s2 = _sammle_psd2(psd2_)

    # IMMER ein status-Feld zurueckgeben. Fehlt es, wertet der Orchestrator den
    # Lauf als Fehler MIT LEEREM GRUND -- eine Meldung jeden Morgen, an der man
    # nichts erkennen kann (Befund 31.08.2026 an einem anderen Sammler).
    return {
        "source": "banking",
        "status": "success",
        "data": {
            "accounts": a1 + a2,
            "balances": b1 + b2,
            "transactions": t1 + t2,
            "sync_state": s1 + s2,
        },
    }


# ---- Schreiben ------------------------------------------------------
def _spalten_nachziehen(conn, tabelle, spalten):
    """CREATE TABLE IF NOT EXISTS aendert eine BESTEHENDE Tabelle nicht. Neue
    Spalten deshalb additiv ergaenzen, damit ein Update nicht verlangt, die
    Historie wegzuwerfen."""
    vorhanden = {r[1] for r in conn.execute(f"PRAGMA table_info({tabelle})")}
    for name, typ in spalten:
        if name not in vorhanden:
            conn.execute(f"ALTER TABLE {tabelle} ADD COLUMN {name} {typ}")


def write(conn, result, date):
    conn.execute(
        """CREATE TABLE IF NOT EXISTS banking_accounts (
            iban TEXT PRIMARY KEY, bank_label TEXT, blz TEXT, bic TEXT,
            currency TEXT, last_synced TEXT)"""
    )
    conn.execute(
        """CREATE TABLE IF NOT EXISTS banking_balances (
            date TEXT, iban TEXT, balance REAL, currency TEXT, collected_at TEXT,
            PRIMARY KEY (date, iban))"""
    )
    conn.execute(
        """CREATE TABLE IF NOT EXISTS banking_transactions (
            txn_id TEXT PRIMARY KEY, iban TEXT, booking_date TEXT, value_date TEXT,
            amount REAL, currency TEXT, direction TEXT, counterparty_name TEXT,
            counterparty_iban TEXT, purpose TEXT, posting_text TEXT, synced_at TEXT)"""
    )
    conn.execute(
        """CREATE TABLE IF NOT EXISTS banking_sync_state (
            blz TEXT PRIMARY KEY, last_success TEXT, needs_tan INTEGER, message TEXT)"""
    )

    # Seit dem zweiten Weg (2026-08-31). Alles additiv, damit eine bestehende
    # FinTS-Installation den Umbau ohne Migration uebersteht.
    #
    # Zur Spalte 'iban': sie ist der Primaerschluessel und traegt den
    # KONTOSCHLUESSEL, nicht immer die blanke IBAN. Fuer FinTS sind beide
    # identisch. Der PSD2-Weg braucht die Unterscheidung, weil PayPal gar keine
    # IBAN hat und ein Sparkonto dieselbe IBAN tragen kann wie das Girokonto
    # daneben -- dort stuende sonst ein Konto weniger in der Summe, ohne dass
    # irgendwo ein Fehler erscheint. Die echte IBAN steht in 'iban_klar'.
    # Den Primaerschluessel sauber umzubenennen hiesse in SQLite: Tabelle neu
    # bauen und Daten kopieren. Das waere ein Eingriff in bestehende Daten, und
    # der ist hier bewusst ausgeschlossen.
    _spalten_nachziehen(conn, "banking_accounts", [
        ("weg", "TEXT"), ("institut", "TEXT"), ("land", "TEXT"),
        ("konto_name", "TEXT"), ("iban_klar", "TEXT"),
    ])
    _spalten_nachziehen(conn, "banking_balances", [("art", "TEXT")])
    _spalten_nachziehen(conn, "banking_transactions", [
        ("status", "TEXT"), ("weg", "TEXT"),
    ])
    _spalten_nachziehen(conn, "banking_sync_state", [
        ("weg", "TEXT"), ("gueltig_bis", "TEXT"), ("rest_tage", "INTEGER"),
    ])

    if result.get("status") != "success":
        conn.commit()
        return 0

    d = result["data"]
    now = datetime.now(timezone.utc).isoformat()
    records = 0

    for a in d["accounts"]:
        conn.execute(
            "INSERT OR REPLACE INTO banking_accounts "
            "(iban, bank_label, blz, bic, currency, last_synced, weg, institut, "
            "land, konto_name, iban_klar) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (a["iban"], a["bank_label"], a["blz"], a.get("bic", ""),
             a.get("currency", "EUR"), now, a.get("weg", "fints"),
             a.get("institut"), a.get("land"), a.get("konto_name"),
             a.get("iban_klar") or a["iban"]),
        )
        records += 1

    for b in d["balances"]:
        conn.execute(
            "INSERT OR REPLACE INTO banking_balances "
            "(date, iban, balance, currency, collected_at, art) VALUES (?,?,?,?,?,?)",
            (date, b["iban"], b["balance"], b["currency"], now, b.get("art")),
        )
        records += 1

    for t in d["transactions"]:
        # PSD2-Umsaetze bringen ihre stabile ID schon mit (sie haengt an der
        # entry_reference der Bank). FinTS-Umsaetze bekommen sie hier.
        tid = t.get("txn_id")
        if not tid:
            from banking import client as bank_client
            tid = bank_client.txn_hash(t["iban"], t)
        conn.execute(
            "INSERT OR REPLACE INTO banking_transactions "
            "(txn_id, iban, booking_date, value_date, amount, currency, direction, "
            "counterparty_name, counterparty_iban, purpose, posting_text, synced_at, "
            "status, weg) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (tid, t["iban"], t["booking_date"], t["value_date"], t["amount"],
             t["currency"], t["direction"], t["counterparty_name"],
             t["counterparty_iban"], t["purpose"], t["posting_text"], now,
             (t.get("status") or "BOOK").upper(), t.get("weg", "fints")),
        )
        records += 1

    for s in d["sync_state"]:
        conn.execute(
            "INSERT OR REPLACE INTO banking_sync_state "
            "(blz, last_success, needs_tan, message, weg, gueltig_bis, rest_tage) "
            "VALUES (?,?,?,?,?,?,?)",
            (s["blz"], now if not s["needs_tan"] else None, s["needs_tan"],
             s["message"], s.get("weg", "fints"), s.get("gueltig_bis"),
             s.get("rest_tage")),
        )
        records += 1

    conn.commit()
    return records


if __name__ == "__main__":
    r = collect()
    print(f"banking: {r['status']} {r.get('reason', '')}")
    if r["status"] == "success":
        d = r["data"]
        vorgemerkt = sum(1 for t in d["transactions"]
                         if (t.get("status") or "BOOK").upper() == "PDNG")
        print(f"  accounts: {len(d['accounts'])}  balances: {len(d['balances'])}  "
              f"transactions: {len(d['transactions'])}"
              + (f" (davon {vorgemerkt} vorgemerkt)" if vorgemerkt else ""))
        for s in d["sync_state"]:
            flag = "TAN/Freigabe noetig" if s["needs_tan"] else "ok"
            print(f"  [{s.get('weg', 'fints')}] {s['blz']}: {flag} {s['message']}")
