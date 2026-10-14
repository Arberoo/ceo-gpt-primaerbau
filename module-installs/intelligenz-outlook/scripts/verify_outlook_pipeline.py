"""Standalone-Verifikation der Outlook-Intel-Pipeline (Phase 1, MCP-Server).

Prueft Schritt fuer Schritt, ob alles haengt:
    1. .env gefunden, MS365_MCP_CLIENT_ID gesetzt (eigene App, nicht Softerias Default)
    2. Node 20+ vorhanden
    3. Lokaler, gepatchter Softeria-Build gefunden (tools/ms-365-mcp/dist/index.js)
    4. Konten eingeloggt (--list-accounts ueber den lokalen Build)

Hintergrund: Softeria v0.113.0 hat zwei Bugs (offline_access fehlt im Login-Scope;
--read-only Scope-Mismatch), darum laeuft das Modul ueber einen LOKAL gebauten +
gepatchten Build, NICHT ueber npx. Tokens liegen auf macOS in der Keychain.

Exit-Code 0 = ok, 1 = Fehler (mit klarer Diagnose).

Lauf:
    python3 scripts/intel/verify_outlook_pipeline.py
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path


def find_env_file() -> Path | None:
    here = Path(__file__).resolve()
    candidates = [here.parent / ".env", here.parent.parent / ".env", here.parent.parent.parent / ".env"]
    cwd = Path.cwd().resolve()
    for parent in [cwd, *cwd.parents]:
        candidates.append(parent / ".env")
    for p in candidates:
        if p.exists():
            return p
    return None


def load_env(env_path: Path | None) -> None:
    if not env_path or not env_path.exists():
        return
    try:
        from dotenv import load_dotenv
        load_dotenv(env_path)
        return
    except ImportError:
        pass
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def check_env() -> None:
    env_path = find_env_file()
    print(f".env:        {env_path or '(nicht gefunden, evtl. via Shell-Export gesetzt)'}")
    load_env(env_path)

    client_id = os.environ.get("MS365_MCP_CLIENT_ID", "").strip()
    if not client_id:
        print("FEHLER: MS365_MCP_CLIENT_ID nicht gesetzt.")
        print("        Ohne eigene Client-ID nutzt Softeria seine Default-App (= Abhaengigkeit).")
        print("        Setz die Client-ID deiner Entra-App (.env oder export).")
        sys.exit(1)
    print(f"Client-ID:   {client_id[:8]}... (eigene App)")
    print(f"Tenant:      {os.environ.get('MS365_MCP_TENANT_ID', 'common').strip() or 'common'}")
    print("Token-Cache: macOS Keychain (kein Datei-Pfad noetig)")


def check_node() -> None:
    node = shutil.which("node")
    if not node:
        print("FEHLER: Node.js nicht gefunden. Installier Node 20+ (macOS: brew install node).")
        sys.exit(1)
    try:
        out = subprocess.run([node, "--version"], capture_output=True, text=True, timeout=15).stdout.strip()
    except Exception as e:
        print(f"FEHLER: 'node --version' schlug fehl: {e!r}")
        sys.exit(1)
    print(f"Node:        {out}")
    m = re.match(r"v(\d+)", out)
    if m and int(m.group(1)) < 20:
        print("WARNUNG: Node < 20. Softeria empfiehlt Node 20+.")


def find_server_entry() -> Path:
    env_entry = os.environ.get("MS365_MCP_SERVER_ENTRY", "").strip()
    candidates = []
    if env_entry:
        candidates.append(Path(env_entry))
    cwd = Path.cwd().resolve()
    for base in [cwd, *cwd.parents]:
        candidates.append(base / "tools" / "ms-365-mcp" / "dist" / "index.js")
    for p in candidates:
        if p.exists():
            return p
    print("FEHLER: Lokaler Softeria-Build nicht gefunden (tools/ms-365-mcp/dist/index.js).")
    print("        Erst bauen: git clone ... && npm install && npm run build (siehe INSTALL.md Step 2).")
    print("        Oder MS365_MCP_SERVER_ENTRY auf den dist/index.js-Pfad setzen.")
    sys.exit(1)


def check_accounts(entry: Path) -> None:
    node = shutil.which("node")
    print(f"Build:       {entry}")
    print("Konten:      starte --list-accounts ueber den lokalen Build...")
    try:
        proc = subprocess.run(
            [node, str(entry), "--list-accounts"],
            capture_output=True, text=True, timeout=60, env=os.environ.copy(),
        )
    except subprocess.TimeoutExpired:
        print("FEHLER: --list-accounts lief in Timeout.")
        sys.exit(1)
    except Exception as e:
        print(f"FEHLER: Aufruf schlug fehl: {e!r}")
        sys.exit(1)

    output = (proc.stdout + "\n" + proc.stderr).strip()
    accounts = [ln.strip() for ln in output.splitlines() if "@" in ln]
    if not accounts:
        print("WARNUNG: Keine eingeloggten Konten erkannt.")
        print(f"         Logg pro Firma ein: node {entry} --login --org-mode")
        print("         Roh-Ausgabe (erste Zeilen):")
        for ln in output.splitlines()[:10]:
            print("           " + ln)
        sys.exit(1)
    print(f"             {len(accounts)} Konto/Konten eingeloggt")
    for a in accounts:
        print("           - " + a)


def main() -> int:
    print("=== Outlook-Intel Pipeline Verification (Phase 1) ===\n")
    check_env()
    print()
    check_node()
    print()
    entry = find_server_entry()
    check_accounts(entry)
    print()
    print("Verifikation erfolgreich. Outlook-Intel (MCP) ist bereit.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
