"""IntelOS - Outlook (Microsoft 365) E-Mail-Collector. PHASE 2.

Zieht E-Mails ueber die Microsoft-Graph-API in die CEO-GPT-Datenbank
(data/data.db, Tabelle `outlook_messages`). NUR E-Mails, kein Kalender.

Auth: eigener MSAL-Login (device-code) mit DERSELBEN Entra-App-Client-ID wie
der MCP-Server, aber eigenem Token-Cache. Der Collector und der MCP-Server sind
getrennte Prozesse, darum ein eigener (zweiter) Login pro Konto.

Multi-Account: alle im Token-Cache hinterlegten Konten werden nacheinander
abgefragt. Neue Konten via --login hinzufuegen.

Usage:
    python scripts/intel/collect_outlook.py --login      # Konto per device-code hinzufuegen
    python scripts/intel/collect_outlook.py              # neue Mails seit ~1 Tag
    python scripts/intel/collect_outlook.py --days 7     # letzte 7 Tage
"""

import os
import sys
import json
import sqlite3
import argparse
from pathlib import Path
from datetime import datetime, timedelta, timezone

try:
    from dotenv import load_dotenv
    for _p in (
        Path(__file__).resolve().parent / ".env",
        Path(__file__).resolve().parent.parent / ".env",
        Path(__file__).resolve().parent.parent.parent / ".env",
    ):
        load_dotenv(_p)
except ImportError:
    pass

GRAPH = "https://graph.microsoft.com/v1.0"
SCOPES = ["Mail.Read"]  # read-only fuer den Collector; MSAL ergaenzt reservierte Scopes

CLIENT_ID = os.getenv("MS365_MCP_CLIENT_ID", "").strip()
TENANT_ID = (os.getenv("MS365_MCP_TENANT_ID", "common").strip() or "common")
AUTHORITY = f"https://login.microsoftonline.com/{TENANT_ID}"
TOKEN_CACHE_PATH = Path(
    os.getenv(
        "OUTLOOK_COLLECTOR_TOKEN_CACHE",
        str(Path(__file__).resolve().parent.parent.parent / "data" / "outlook-collector-token-cache.json"),
    )
)
MAX_PAGES = 20  # Sicherheitskappe: ~1000 Mails pro Konto und Lauf


def _require(modname: str):
    try:
        return __import__(modname)
    except ImportError:
        print(f"FEHLER: Python-Paket '{modname}' fehlt. Installier: pip install msal requests python-dotenv")
        sys.exit(1)


def _build_app():
    msal = _require("msal")
    if not CLIENT_ID:
        print("FEHLER: MS365_MCP_CLIENT_ID nicht gesetzt (eigene Entra-App). In .env eintragen.")
        sys.exit(1)
    cache = msal.SerializableTokenCache()
    if TOKEN_CACHE_PATH.exists():
        cache.deserialize(TOKEN_CACHE_PATH.read_text())
    app = msal.PublicClientApplication(CLIENT_ID, authority=AUTHORITY, token_cache=cache)
    return app, cache


def _save_cache(cache) -> None:
    if cache.has_state_changed:
        TOKEN_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        TOKEN_CACHE_PATH.write_text(cache.serialize())


def login() -> None:
    """Fuegt ein Konto per device-code hinzu."""
    app, cache = _build_app()
    flow = app.initiate_device_flow(scopes=SCOPES)
    if "user_code" not in flow:
        print(f"FEHLER: device-flow konnte nicht gestartet werden: {json.dumps(flow)[:300]}")
        sys.exit(1)
    print(flow["message"])  # enthaelt URL + Code
    result = app.acquire_token_by_device_flow(flow)  # blockiert bis User fertig
    _save_cache(cache)
    if "access_token" in result:
        accts = app.get_accounts()
        names = ", ".join(a.get("username", "?") for a in accts)
        print(f"Login ok. Konten im Cache: {names}")
    else:
        print(f"Login fehlgeschlagen: {result.get('error_description', result)}")
        sys.exit(1)


def _token_for(app, account):
    result = app.acquire_token_silent(SCOPES, account=account)
    if not result or "access_token" not in result:
        return None
    return result["access_token"]


def _fetch_messages(token: str, since_iso: str) -> list[dict]:
    requests = _require("requests")
    headers = {"Authorization": f"Bearer {token}", "Prefer": 'outlook.body-content-type="text"'}
    params = (
        "?$select=id,subject,from,toRecipients,receivedDateTime,bodyPreview,isRead,hasAttachments,webLink"
        "&$top=50"
        f"&$filter=receivedDateTime ge {since_iso}"
        "&$orderby=receivedDateTime desc"
    )
    url = f"{GRAPH}/me/messages{params}"
    out: list[dict] = []
    pages = 0
    while url and pages < MAX_PAGES:
        r = requests.get(url, headers=headers, timeout=30)
        if r.status_code != 200:
            print(f"  Graph-Fehler {r.status_code}: {r.text[:200]}")
            break
        data = r.json()
        out.extend(data.get("value", []))
        url = data.get("@odata.nextLink")
        pages += 1
    return out


def collect(days: int | None = None) -> list[dict]:
    """Sammelt E-Mails aller eingeloggten Konten. Returns Liste von dicts."""
    app, cache = _build_app()
    accounts = app.get_accounts()
    if not accounts:
        print("Keine eingeloggten Konten. Fuehr zuerst aus: python collect_outlook.py --login")
        return []

    lookback = days if days is not None else 1
    since_dt = datetime.now(timezone.utc) - timedelta(days=lookback)
    since_iso = since_dt.strftime("%Y-%m-%dT%H:%M:%SZ")

    messages: list[dict] = []
    for acct in accounts:
        username = acct.get("username", "unknown")
        token = _token_for(app, acct)
        if not token:
            print(f"  {username}: Token abgelaufen, bitte neu einloggen (--login).")
            continue
        raw = _fetch_messages(token, since_iso)
        for m in raw:
            frm = (m.get("from") or {}).get("emailAddress") or {}
            to = ", ".join(
                (r.get("emailAddress") or {}).get("address", "")
                for r in (m.get("toRecipients") or [])
            )
            messages.append({
                "message_id": f"{username}:{m.get('id', '')}",
                "account": username,
                "from_name": frm.get("name", ""),
                "from_email": frm.get("address", ""),
                "to_recipients": to,
                "subject": m.get("subject", ""),
                "body_preview": (m.get("bodyPreview") or "").strip(),
                "received_at": m.get("receivedDateTime", ""),
                "is_read": 1 if m.get("isRead") else 0,
                "has_attachments": 1 if m.get("hasAttachments") else 0,
                "web_link": m.get("webLink", ""),
            })
        print(f"  {username}: {len(raw)} Mails seit {since_iso}")

    _save_cache(cache)
    print(f"Outlook: insgesamt {len(messages)} Mails gesammelt.")
    return messages


def write(conn: sqlite3.Connection, messages: list[dict]) -> int:
    """Schreibt E-Mails in die CEO-GPT-Datenbank. Returns Anzahl neu geschrieben."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS outlook_messages (
            message_id TEXT PRIMARY KEY,
            account TEXT NOT NULL,
            from_name TEXT,
            from_email TEXT,
            to_recipients TEXT,
            subject TEXT,
            body_preview TEXT,
            received_at TEXT,
            is_read INTEGER DEFAULT 0,
            has_attachments INTEGER DEFAULT 0,
            web_link TEXT,
            collected_at TEXT NOT NULL
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_ol_received ON outlook_messages(received_at)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_ol_account ON outlook_messages(account)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_ol_from ON outlook_messages(from_email)")

    now = datetime.now(timezone.utc).isoformat()
    count = 0
    for m in messages:
        try:
            conn.execute(
                "INSERT OR IGNORE INTO outlook_messages "
                "(message_id, account, from_name, from_email, to_recipients, subject, "
                "body_preview, received_at, is_read, has_attachments, web_link, collected_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (m["message_id"], m["account"], m["from_name"], m["from_email"],
                 m["to_recipients"], m["subject"], m["body_preview"], m["received_at"],
                 m["is_read"], m["has_attachments"], m["web_link"], now),
            )
            count += 1
        except sqlite3.IntegrityError:
            pass

    conn.commit()

    # Collection-Log (best effort, Tabelle existiert evtl. nur mit IntelOS)
    try:
        conn.execute(
            "INSERT INTO collection_log (collected_at, source, status, reason, records_written) "
            "VALUES (?, 'outlook', 'success', NULL, ?)",
            (now, count),
        )
        conn.commit()
    except sqlite3.OperationalError:
        pass

    return count


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Outlook E-Mail-Collector fuer IntelOS (Phase 2)")
    parser.add_argument("--login", action="store_true", help="Konto per device-code hinzufuegen")
    parser.add_argument("--days", type=int, default=None, help="Tage zurueck (Default: 1)")
    args = parser.parse_args()

    if args.login:
        login()
        sys.exit(0)

    msgs = collect(days=args.days)
    if not msgs:
        print("Keine neuen Mails zu schreiben.")
        sys.exit(0)

    # In die CEO-GPT-DB schreiben (IntelOS-db.init_db falls vorhanden, sonst direkt)
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    try:
        from db import init_db  # type: ignore
        conn = init_db()
    except ImportError:
        db_path = Path(__file__).resolve().parent.parent.parent / "data" / "data.db"
        db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(db_path))

    written = write(conn, msgs)
    print(f"Geschrieben: {written} Mails in die Datenbank.")
    if msgs:
        s = msgs[0]
        print(f"\nBeispiel: [{s['from_name'] or s['from_email']}] {s['subject'][:70]}")
    conn.close()
