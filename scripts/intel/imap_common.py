"""IntelOS - IMAP-Modul: gemeinsame Helfer (Konten-Config, Verbindung, DB-Schema).

Konten liegen NICHT-geheim in config/imap-accounts.json. Passwoerter kommen
aus der .env (pro Konto ueber den Schluessel in "password_env"). Beispiel-Eintrag:

[
  {
    "label": "info",
    "imap_host": "imap.example.com", "imap_port": 993, "imap_ssl": true,
    "smtp_host": "smtp.example.com", "smtp_port": 465,
    "username": "info@example.com",
    "provider": "generic",
    "password_env": "IMAP_PW_INFO"
  }
]

Secrets bleiben in der .env (IMAP_PW_INFO=...), NIE in der Config oder DB.
"""

import os
import sys
import json
import sqlite3
import importlib
from pathlib import Path
from datetime import datetime, timezone

WORKSPACE = Path(__file__).resolve().parent.parent.parent
ACCOUNTS_FILE = Path(os.getenv("IMAP_ACCOUNTS_FILE", str(WORKSPACE / "config" / "imap-accounts.json")))
PIP_HINT = "pip install imap-tools IMAPClient python-dotenv"

try:
    from dotenv import load_dotenv
    load_dotenv(WORKSPACE / ".env")
except ImportError:
    pass


def imp(modname: str):
    try:
        return importlib.import_module(modname)
    except ImportError:
        print(f"FEHLER: Python-Paket fehlt. Installier:\n  {PIP_HINT}")
        sys.exit(1)


def load_accounts(only: str | None = None) -> list[dict]:
    if not ACCOUNTS_FILE.exists():
        print(f"FEHLER: Konten-Datei fehlt: {ACCOUNTS_FILE}")
        print("        Lege sie an (Vorlage steht oben in imap_common.py / INSTALL.md).")
        sys.exit(1)
    try:
        raw = json.loads(ACCOUNTS_FILE.read_text())
    except json.JSONDecodeError as e:
        print(f"FEHLER: {ACCOUNTS_FILE} ist kein gueltiges JSON: {e}")
        sys.exit(1)
    if not isinstance(raw, list) or not raw:
        print(f"FEHLER: {ACCOUNTS_FILE} muss eine nicht-leere Liste von Konten sein.")
        sys.exit(1)
    accounts = []
    for a in raw:
        if only and a.get("label") != only:
            continue
        a = dict(a)
        a["password"] = os.getenv(a.get("password_env", ""), "").strip()
        accounts.append(a)
    if not accounts:
        print(f"FEHLER: Kein Konto{' mit label ' + only if only else ''} gefunden.")
        sys.exit(1)
    return accounts


def connect(account: dict):
    """Read-only IMAP-Verbindung via imap-tools. Markiert nichts als gelesen."""
    mt = imp("imap_tools")
    host = account.get("imap_host")
    port = int(account.get("imap_port", 993))
    user = account.get("username") or account.get("label")
    pw = account.get("password", "")
    if not host:
        print(f"FEHLER: imap_host fehlt fuer Konto '{account.get('label')}'.")
        sys.exit(1)
    if not pw:
        print(f"FEHLER: Kein Passwort fuer '{account.get('label')}' "
              f"(.env-Schluessel '{account.get('password_env')}' leer).")
        sys.exit(1)
    # imap_ssl=true -> implizites TLS (993). Sonst STARTTLS-faehig via MailBoxUnencrypted+starttls.
    mb = mt.MailBox(host, port).login(user, pw)
    return mb


def db_connect() -> sqlite3.Connection:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    try:
        from db import init_db  # type: ignore
        return init_db()
    except ImportError:
        p = WORKSPACE / "data" / "data.db"
        p.parent.mkdir(parents=True, exist_ok=True)
        return sqlite3.connect(str(p))


def ensure_tables(conn: sqlite3.Connection) -> None:
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS mail_accounts (
            label TEXT PRIMARY KEY,
            imap_host TEXT, imap_port INTEGER DEFAULT 993,
            smtp_host TEXT, smtp_port INTEGER DEFAULT 465,
            username TEXT, provider TEXT, auth_type TEXT DEFAULT 'app_password',
            created_at TEXT
        );
        CREATE TABLE IF NOT EXISTS mail_folders (
            label TEXT NOT NULL,
            name TEXT NOT NULL,
            delimiter TEXT,
            special_use TEXT,
            uidvalidity INTEGER,
            last_uid INTEGER DEFAULT 0,
            uidnext INTEGER,
            msg_count INTEGER,
            synced_at TEXT,
            PRIMARY KEY (label, name)
        );
        CREATE TABLE IF NOT EXISTS mail_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            label TEXT NOT NULL,
            folder TEXT NOT NULL,
            uid INTEGER NOT NULL,
            message_id TEXT,
            gm_msgid TEXT,
            gm_labels TEXT,
            from_name TEXT, from_email TEXT,
            to_recipients TEXT, cc_recipients TEXT,
            subject TEXT, body_preview TEXT,
            received_at TEXT, flags TEXT, size_bytes INTEGER,
            has_attach INTEGER DEFAULT 0,
            collected_at TEXT NOT NULL,
            UNIQUE(label, folder, uid)
        );
        CREATE INDEX IF NOT EXISTS idx_mm_msgid ON mail_messages(message_id);
        CREATE INDEX IF NOT EXISTS idx_mm_received ON mail_messages(received_at);
        CREATE INDEX IF NOT EXISTS idx_mm_from ON mail_messages(from_email);
        CREATE INDEX IF NOT EXISTS idx_mm_label ON mail_messages(label);
        CREATE TABLE IF NOT EXISTS mail_discovery (
            label TEXT NOT NULL,
            scanned_at TEXT NOT NULL,
            capabilities TEXT,
            folders_json TEXT
        );
    """)
    conn.commit()


def upsert_account(conn: sqlite3.Connection, account: dict) -> None:
    conn.execute(
        "INSERT OR REPLACE INTO mail_accounts "
        "(label, imap_host, imap_port, smtp_host, smtp_port, username, provider, auth_type, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (account.get("label"), account.get("imap_host"), int(account.get("imap_port", 993)),
         account.get("smtp_host"), int(account.get("smtp_port", 465)) if account.get("smtp_port") else None,
         account.get("username"), account.get("provider", "generic"),
         account.get("auth_type", "app_password"), now_iso()),
    )
    conn.commit()


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def special_use_of(flags) -> str:
    """Mappt RFC-6154-Flags auf eine Rolle, sonst ''."""
    roles = {"\\Sent", "\\Drafts", "\\Junk", "\\Trash", "\\All", "\\Archive", "\\Flagged"}
    for f in (flags or []):
        if str(f) in roles:
            return str(f)
    return ""
