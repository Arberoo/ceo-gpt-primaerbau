"""Misst, wie schnell echte neue Mails in data/data.db ankommen.

Vergleicht je Postfach (INBOX) fuer die Mails der letzten Stunden die Ankunft beim
Server (INTERNALDATE, per frischer Anmeldung und UID FETCH) mit dem Zeitpunkt, an dem
sie in mail_messages gespeichert wurden (collected_at). Nur lesen, nichts aendern.

Usage:
    python scripts/intel/check_mail_latency.py              # letzte 24 Stunden
    python scripts/intel/check_mail_latency.py --hours 6
    python scripts/intel/check_mail_latency.py --since "2026-10-15 07:00"

Exit 0 = alle Mails binnen --limit Sekunden (Default 60) gespeichert, 2 = langsam oder fehlend.
"""

import re
import sys
import argparse
from pathlib import Path
from datetime import datetime, timedelta, timezone

sys.path.insert(0, str(Path(__file__).resolve().parent))
import imap_common as C  # noqa: E402


def server_arrivals(account: dict, since: datetime) -> list:
    mb = C.connect(account)
    try:
        mb.folder.set("INBOX", readonly=True)
        typ, data = mb.client.uid("FETCH", "1:*", "(UID INTERNALDATE)")
        out = []
        for item in data or []:
            raw = (item[0] if isinstance(item, tuple) else item or b"").decode(errors="ignore")
            u = re.search(r"UID (\d+)", raw)
            d = re.search(r'INTERNALDATE "([^"]+)"', raw)
            if not (u and d):
                continue
            when = datetime.strptime(d.group(1), "%d-%b-%Y %H:%M:%S %z")
            if when >= since:
                out.append((int(u.group(1)), when))
        return out
    finally:
        try:
            mb.logout()
        except Exception:
            pass


def main() -> int:
    ap = argparse.ArgumentParser(description="Ankunftszeit echter Mails in data.db messen")
    ap.add_argument("--hours", type=float, default=24)
    ap.add_argument("--since", default=None, help='Ortszeit, z. B. "2026-10-15 07:00"')
    ap.add_argument("--limit", type=int, default=60, help="erlaubte Sekunden bis zur Speicherung")
    args = ap.parse_args()
    since = (datetime.strptime(args.since, "%Y-%m-%d %H:%M").astimezone() if args.since
             else datetime.now().astimezone() - timedelta(hours=args.hours))

    conn = C.db_connect()
    ok = True
    total = 0
    for account in C.load_accounts():
        label = account["label"]
        for uid, arrived in server_arrivals(account, since):
            total += 1
            row = conn.execute("SELECT collected_at, subject FROM mail_messages WHERE label=? AND folder='INBOX' AND uid=?",
                               (label, uid)).fetchone()
            t = arrived.astimezone().strftime("%d.%m. %H:%M:%S")
            if not row:
                ok = False
                print(f"  FEHLT   {label:<12} {t}  UID {uid} (noch nicht in der Datenbank)")
                continue
            delay = (datetime.fromisoformat(row[0]) - arrived.astimezone(timezone.utc)).total_seconds()
            mark = "ok     " if delay <= args.limit else "LANGSAM"
            if delay > args.limit:
                ok = False
            print(f"  {mark} {label:<12} {t}  nach {delay:6.0f} s gespeichert  {(row[1] or '')[:50]}")
    conn.close()
    if not total:
        print(f"Seit {since:%d.%m. %H:%M} keine neuen Mails im Posteingang.")
        return 0
    print("ERGEBNIS: alle Mails rechtzeitig gespeichert." if ok
          else f"ERGEBNIS: mindestens eine Mail fehlt oder brauchte laenger als {args.limit} s.")
    return 0 if ok else 2


if __name__ == "__main__":
    sys.exit(main())
