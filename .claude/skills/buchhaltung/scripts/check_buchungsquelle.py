#!/usr/bin/env python3
"""
Prueft, ob im Workspace bereits eine Buchungsquelle (Bankanbindung) existiert.

Dieses Modul baut KEINE Bankanbindung. Es schaut nur nach, ob eine da ist
(eigenes Bankanbindungs-Modul, vorhandener Collector oder eine Transaktions-
Tabelle in data/data.db) und sagt dann, ob direkt gezogen werden kann oder ob
der Kontoauszug manuell exportiert werden muss.

Exit-Code 0 = Quelle gefunden, 1 = manueller Export noetig.
"""
import os
import glob
import sqlite3
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def workspace_root():
    d = HERE
    for _ in range(8):
        if os.path.exists(os.path.join(d, "CLAUDE.md")):
            return d
        nd = os.path.dirname(d)
        if nd == d:
            break
        d = nd
    return os.getcwd()


def main():
    ws = workspace_root()
    found = []

    patterns = ["collect_*bank*.py", "collect_revolut*.py", "collect_*gocardless*.py",
                "collect_*nordigen*.py", "collect_*statement*.py"]
    for pat in patterns:
        for c in glob.glob(f"{ws}/scripts/{pat}"):
            found.append(f"Collector: {os.path.basename(c)}")

    db = f"{ws}/data/data.db"
    if os.path.exists(db):
        try:
            con = sqlite3.connect(db)
            tbls = [r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")]
            con.close()
            for t in tbls:
                if any(k in t.lower() for k in ("transaction", "bank", "revolut", "kontoauszug", "ledger", "gocardless")):
                    found.append(f"Tabelle: {t}")
        except Exception:
            pass

    if found:
        print("Buchungsquelle gefunden, das CEO-GPT kann die Buchungen direkt ziehen:")
        for f in sorted(set(found)):
            print(f"  - {f}")
        return 0

    print("Keine Bankanbindung gefunden.")
    print("Bitte den Kontoauszug manuell exportieren: CSV (zum Matchen) UND PDF (Beleg), "
          "jeweils voller Kalendermonat.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
