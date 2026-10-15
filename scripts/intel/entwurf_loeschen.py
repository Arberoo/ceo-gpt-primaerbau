"""Entwuerfe in einem PrimaerBau-Postfach auflisten oder wegraeumen.

Der Live-Mailzugriff (mail_pb_*) darf nur Entwuerfe ANLEGEN. Dieses Skript ergaenzt
genau einen weiteren Schritt: einen Entwurf wieder wegraeumen (freigegeben von Arber, 15.10.2026).
Bewusst eng:

- arbeitet NUR im Entwuerfe-Ordner (IMAP-Kennzeichen \\Drafts)
- trifft NUR Nachrichten mit dem Kennzeichen \\Draft und genau passender Message-ID
- loescht nicht endgueltig, sondern VERSCHIEBT in "Geloeschte Elemente" (\\Trash),
  dort laesst sich der Entwurf jederzeit zurueckholen

Usage:
    python scripts/intel/entwurf_loeschen.py pb_info --liste
    python scripts/intel/entwurf_loeschen.py pb_info --message-id "<abc@primaerbau.com>"
"""

import sys
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import imap_common as C  # noqa: E402


def ordner_mit(mb, kennzeichen: str) -> str | None:
    for f in mb.folder.list():
        if C.special_use_of(getattr(f, "flags", ())) == kennzeichen:
            return f.name
    return None


def message_id(m) -> str:
    return (m.headers.get("message-id") or ("",))[0].strip()


def norm(mid: str) -> str:
    return mid.strip().strip("<>").strip().lower()


def main() -> int:
    ap = argparse.ArgumentParser(description="Entwuerfe auflisten oder in den Papierkorb verschieben")
    ap.add_argument("konto", help="Label aus config/imap-accounts.json, z. B. pb_info")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--liste", action="store_true", help="Entwuerfe anzeigen")
    g.add_argument("--message-id", help="Message-ID des Entwurfs, der weg soll")
    args = ap.parse_args()

    mb = C.connect(C.load_accounts(args.konto)[0])
    try:
        entwuerfe = ordner_mit(mb, "\\Drafts")
        papierkorb = ordner_mit(mb, "\\Trash")
        if not entwuerfe or not papierkorb:
            print("FEHLER: Entwuerfe- oder Papierkorb-Ordner nicht gefunden.")
            return 1
        mb.folder.set(entwuerfe)
        msgs = list(mb.fetch(mark_seen=False, headers_only=True))

        if args.liste:
            for m in msgs:
                print(f"{m.date_str[:25]:25} | {m.subject[:70]:70} | {message_id(m)}")
            print(f"{len(msgs)} Entwurf/Entwuerfe in '{entwuerfe}'")
            return 0

        ziel = norm(args.message_id)
        treffer = [m for m in msgs if norm(message_id(m)) == ziel and "\\Draft" in m.flags]
        if len(treffer) != 1:
            print(f"Nichts verschoben: {len(treffer)} passende Entwuerfe gefunden (erwartet genau 1).")
            return 1
        m = treffer[0]
        mb.move(m.uid, papierkorb)
        print(f"Verschoben nach '{papierkorb}': {m.subject}")
        return 0
    finally:
        try:
            mb.logout()
        except Exception:
            pass


if __name__ == "__main__":
    sys.exit(main())
