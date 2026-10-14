"""Standalone-Verifikation der IMAP-Pipeline.

Prueft:
    1. config/imap-accounts.json vorhanden + gueltiges JSON + Pflichtfelder
    2. Pro Konto: Passwort in der .env gesetzt (nur GESETZT/FEHLT, nie der Wert)
    3. Python-Pakete da (imap-tools, IMAPClient)
    4. uvx vorhanden (fuer den Live-MCP-Server mcp-email-server)
    5. Best effort: Login-Test je Konto (Ordner zaehlen), damit falsche Zugaenge frueh auffallen

Exit 0 = Grundlage ok, 1 = harter Fehler.

Lauf:
    python3 scripts/intel/verify_imap_pipeline.py
"""

import sys
import shutil
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import imap_common as C  # noqa: E402


def main() -> int:
    print("=== IMAP Pipeline Verification ===\n")

    # 1) + 2) Konten-Config + Passwoerter
    print(f"Konten-Datei: {C.ACCOUNTS_FILE}")
    accounts = C.load_accounts()  # beendet hart, wenn Datei fehlt/kaputt
    ok = True
    for a in accounts:
        label = a.get("label", "?")
        missing = [k for k in ("imap_host", "username", "password_env") if not a.get(k)]
        pw_set = bool(a.get("password"))
        status = "ok" if (not missing and pw_set) else "FEHLT"
        detail = ""
        if missing:
            detail += f" Pflichtfeld fehlt: {', '.join(missing)}."
        if not pw_set:
            detail += f" Passwort (.env {a.get('password_env')}) leer."
        print(f"  - {label:<16} {status}{detail}")
        if missing or not pw_set:
            ok = False
    print()

    # 3) Pakete
    try:
        import imap_tools  # noqa: F401
        print("imap-tools:   vorhanden")
    except ImportError:
        print("imap-tools:   FEHLT -> pip install imap-tools IMAPClient python-dotenv")
        ok = False

    # 4) uvx
    uvx = shutil.which("uvx") or shutil.which("uv")
    print(f"uv/uvx:       {uvx or 'FEHLT (brew install uv) - nur fuer den Live-MCP noetig'}")

    # 5) Login-Test (best effort)
    print("\nLogin-Test (read-only, zaehlt nur Ordner):")
    for a in accounts:
        if not a.get("password"):
            print(f"  - {a.get('label')}: uebersprungen (kein Passwort)")
            continue
        try:
            mb = C.connect(a)
            n = len(list(mb.folder.list()))
            try:
                mb.logout()
            except Exception:
                pass
            print(f"  - {a.get('label')}: OK, {n} Ordner erreichbar")
        except SystemExit:
            raise
        except Exception as e:
            print(f"  - {a.get('label')}: LOGIN FEHLGESCHLAGEN ({e!r})")
            ok = False

    print()
    if ok:
        print("Verifikation ok. Naechster Schritt: discover_imap.py, dann collect_imap.py --? (Backfill).")
        return 0
    print("Es gibt offene Punkte (siehe oben). Erst beheben, dann erneut pruefen.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
