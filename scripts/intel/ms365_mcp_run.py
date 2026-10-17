"""Windows-Starter fuer den Live-Zugriff auf die MUBA-Postfaecher (Microsoft 365, Graph).

Startet den lokal gebauten und gepatchten Softeria-Server tools/ms-365-mcp (v0.113.0,
offline_access-Patch) mit der eigenen Entra-App der MUBA. Aufruf aus .mcp.json:
    .venv/Scripts/python.exe scripts/intel/ms365_mcp_run.py
Anmelden (einmal je Postfach, im Terminal):
    .venv/Scripts/python.exe scripts/intel/ms365_mcp_run.py --login
Angemeldete Postfaecher:
    .venv/Scripts/python.exe scripts/intel/ms365_mcp_run.py --list-accounts

- Kennungen MS365_MCP_CLIENT_ID / MS365_MCP_TENANT_ID aus der .env (nicht geheim)
- Anmeldung liegt in der Windows-Anmeldeinformationsverwaltung (keytar), nicht im Repo
- Nur Lese- und Entwurfs-Werkzeuge (ERLAUBT), dazu Entwuerfe aendern/loeschen (nur isDraft).
  Senden ist zusaetzlich in der Entra-App nicht freigegeben (kein Mail.Send).
- Login und Betrieb MUESSEN dieselben Werkzeuge nutzen, sonst passen die Berechtigungen
  des gespeicherten Tokens nicht (Softeria baut die Scopes aus den Werkzeugen).
"""

import os
import subprocess
import sys
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parent.parent.parent
SERVER = WORKSPACE / "tools" / "ms-365-mcp" / "dist" / "index.js"
NODE = Path(r"C:\Program Files\nodejs\node.exe")

ERLAUBT = [
    "list-mail-messages", "list-mail-folders", "list-mail-child-folders",
    "list-mail-folder-messages", "get-mail-message", "list-mail-attachments",
    "create-draft-email", "create-reply-draft", "create-reply-all-draft",
    # Nur fuer Entwuerfe (Pruefung im gepatchten Server, src/graph-tools.ts), Arber 17.10.2026.
    # Loeschen = in "Geloeschte Elemente" verschieben, zurueckholbar.
    "update-mail-message", "delete-mail-message",
]


def env_wert(key: str) -> str:
    for line in (WORKSPACE / ".env").read_text(encoding="utf-8", errors="ignore").splitlines():
        line = line.strip()
        if line.startswith(key + "="):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    return ""


def main() -> int:
    client_id, tenant_id = env_wert("MS365_MCP_CLIENT_ID"), env_wert("MS365_MCP_TENANT_ID")
    if not client_id or not tenant_id:
        print("MS365_MCP_CLIENT_ID / MS365_MCP_TENANT_ID fehlen in der .env", file=sys.stderr)
        return 2
    env = dict(os.environ)
    env.update({"MS365_MCP_CLIENT_ID": client_id, "MS365_MCP_TENANT_ID": tenant_id})
    regex = "^(" + "|".join(ERLAUBT) + ")$"
    args = [str(NODE if NODE.exists() else "node"), str(SERVER), "--org-mode", "--enabled-tools", regex]
    args += sys.argv[1:]  # z. B. --login, --list-accounts, --verify-login
    return subprocess.call(args, env=env, cwd=str(WORKSPACE))


if __name__ == "__main__":
    sys.exit(main())
