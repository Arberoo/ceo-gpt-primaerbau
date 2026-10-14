"""IntelOS - IMAP Discovery. STUFE 1: das Postfach durchleuchten.

Verbindet sich zu jedem in config/imap-accounts.json hinterlegten Konto und zeigt,
WAS da liegt, bevor extrahiert wird:
  - Server-Capabilities
  - alle Ordner (Name dekodiert, Delimiter, Spezial-Ordner per RFC-6154-Flag)
  - pro Ordner: Anzahl, ungelesen, UIDVALIDITY/UIDNEXT
  - optional grober Zeitraum (aeltester/neuester Eintrag) pro Ordner

Markiert NICHTS als gelesen, laedt KEINE Bodies. Schreibt einen Snapshot nach
data/data.db (mail_accounts, mail_folders, mail_discovery).

Usage:
    python scripts/intel/discover_imap.py
    python scripts/intel/discover_imap.py --account info
    python scripts/intel/discover_imap.py --no-dates     # schneller, ohne Zeitraum
"""

import re
import sys
import json
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import imap_common as C  # noqa: E402

STATUS_OPTS = ("MESSAGES", "UIDNEXT", "UIDVALIDITY", "UNSEEN")


def _quote(name: str) -> str:
    return '"%s"' % name.replace('"', '\\"')


def folder_status(mb, name: str) -> dict:
    """Anzahl/UIDVALIDITY/UIDNEXT/UNSEEN, robust ueber zwei Wege."""
    try:
        st = mb.folder.status(name, STATUS_OPTS)
        return {k: int(st.get(k, 0) or 0) for k in STATUS_OPTS}
    except Exception:
        pass
    try:
        typ, data = mb.client.status(_quote(name), "(%s)" % " ".join(STATUS_OPTS))
        if typ == "OK" and data and data[0]:
            s = data[0].decode(errors="ignore")
            return {k: (int(re.search(k + r"\s+(\d+)", s).group(1)) if re.search(k + r"\s+(\d+)", s) else 0) for k in STATUS_OPTS}
    except Exception:
        pass
    return {k: 0 for k in STATUS_OPTS}


def date_span(mb, name: str):
    """Grober Zeitraum (aeltester, neuester) ohne Voll-Scan, best effort."""
    try:
        mb.folder.set(name, readonly=True)
        newest = next(iter(mb.fetch("ALL", reverse=True, limit=1, mark_seen=False, headers_only=True)), None)
        oldest = next(iter(mb.fetch("ALL", reverse=False, limit=1, mark_seen=False, headers_only=True)), None)
        return (getattr(oldest, "date_str", "") or "", getattr(newest, "date_str", "") or "")
    except Exception:
        return ("", "")


def discover_account(conn, account: dict, with_dates: bool) -> None:
    label = account.get("label", "?")
    print(f"\n=== Konto: {label}  ({account.get('imap_host')}:{account.get('imap_port', 993)}) ===")
    C.upsert_account(conn, account)
    mb = C.connect(account)
    try:
        caps = [c.decode(errors="ignore") if isinstance(c, bytes) else str(c) for c in (mb.client.capabilities or [])]
        key_caps = [c for c in caps if c.upper() in ("IDLE", "UIDPLUS", "CONDSTORE", "QRESYNC", "X-GM-EXT-1", "SPECIAL-USE", "MOVE")]
        print("Capabilities (relevant):", ", ".join(key_caps) or "(keine besonderen)")

        folders = list(mb.folder.list())
        rows = []
        total_msgs = 0
        print(f"\n{'Ordner':<34} {'Rolle':<9} {'Mails':>7} {'ungelesen':>9}  Zeitraum")
        print("-" * 86)
        for f in folders:
            name = getattr(f, "name", str(f))
            delim = getattr(f, "delim", "")
            flags = getattr(f, "flags", ())
            role = C.special_use_of(flags).replace("\\", "")
            st = folder_status(mb, name)
            total_msgs += st["MESSAGES"]
            span = ""
            if with_dates and st["MESSAGES"] > 0:
                od, nd = date_span(mb, name)
                if od or nd:
                    span = f"{od[:16]} .. {nd[:16]}"
            print(f"{name[:34]:<34} {role:<9} {st['MESSAGES']:>7} {st['UNSEEN']:>9}  {span}")
            rows.append({
                "name": name, "delimiter": delim, "special_use": role,
                "uidvalidity": st["UIDVALIDITY"], "uidnext": st["UIDNEXT"],
                "msg_count": st["MESSAGES"], "unseen": st["UNSEEN"],
            })
            # mail_folders pflegen, OHNE last_uid/uidvalidity-Resume-Stand zu zerstoeren
            conn.execute(
                "INSERT INTO mail_folders (label, name, delimiter, special_use, uidvalidity, uidnext, msg_count, synced_at, last_uid) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0) "
                "ON CONFLICT(label, name) DO UPDATE SET "
                "delimiter=excluded.delimiter, special_use=excluded.special_use, "
                "uidnext=excluded.uidnext, msg_count=excluded.msg_count, synced_at=excluded.synced_at",
                (label, name, delim, role, st["UIDVALIDITY"], st["UIDNEXT"], st["MESSAGES"], C.now_iso()),
            )
        conn.execute(
            "INSERT INTO mail_discovery (label, scanned_at, capabilities, folders_json) VALUES (?, ?, ?, ?)",
            (label, C.now_iso(), json.dumps(caps), json.dumps(rows)),
        )
        conn.commit()
        print("-" * 86)
        print(f"Summe: {len(folders)} Ordner, {total_msgs} Mails gesamt in '{label}'.")
    finally:
        try:
            mb.logout()
        except Exception:
            pass


def main() -> int:
    ap = argparse.ArgumentParser(description="IMAP Discovery (Stufe 1: durchleuchten)")
    ap.add_argument("--account", default=None, help="nur dieses Konto (label)")
    ap.add_argument("--no-dates", action="store_true", help="ohne Zeitraum-Ermittlung (schneller)")
    args = ap.parse_args()

    conn = C.db_connect()
    C.ensure_tables(conn)
    accounts = C.load_accounts(only=args.account)
    print(f"Durchleuchte {len(accounts)} Konto/Konten...")
    for account in accounts:
        try:
            discover_account(conn, account, with_dates=not args.no_dates)
        except SystemExit:
            raise
        except Exception as e:
            print(f"  FEHLER bei '{account.get('label')}': {e!r}")
    conn.close()
    print("\nDiscovery fertig. Stand liegt in data/data.db (mail_discovery / mail_folders).")
    print("Naechster Schritt: python scripts/intel/collect_imap.py --backfill")
    return 0


if __name__ == "__main__":
    sys.exit(main())
