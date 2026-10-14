"""Windows-Starter fuer den Live-Mailzugriff (ai-zerolab/mcp-email-server) je Postfach.

Ersetzt imap-mcp-run.sh aus dem Modul intelligenz-imap (Mac). Aufruf aus .mcp.json:
    .venv/Scripts/python.exe scripts/intel/imap_mcp_run.py <label>

- liest Server-Daten aus config/imap-accounts.json und das Passwort aus der .env
  (Schluessel aus "password_env"), zeigt nichts davon an
- erlaubt nur Entwuerfe (ACCOUNT_ALLOWED_MUTATIONS=draft): kein Senden, kein Loeschen,
  kein Verschieben. Ohne SMTP-Daten gibt es ausserdem keinen Sendeweg.
- eigene, leere Config-Datei je Postfach unter %USERPROFILE%\\.ceo-gpt-primaerbau\\mcp-email,
  damit nichts geteilt oder dauerhaft gespeichert wird
"""

import json
import os
import subprocess
import sys
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parent.parent.parent
SERVER = "mcp-email-server==1.13.1"  # fest, damit kein ungeprueftes Update automatisch kommt
UVX = Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft/WinGet/Packages/astral-sh.uv_Microsoft.Winget.Source_8wekyb3d8bbwe/uvx.exe"


def env_wert(key: str) -> str:
    for line in (WORKSPACE / ".env").read_text(encoding="utf-8", errors="ignore").splitlines():
        line = line.strip()
        if line.startswith(key + "="):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    return ""


def main() -> int:
    if len(sys.argv) < 2:
        print("Aufruf: imap_mcp_run.py <label>", file=sys.stderr)
        return 2
    label = sys.argv[1]
    konten = json.loads((WORKSPACE / "config" / "imap-accounts.json").read_text(encoding="utf-8"))
    konto = next((k for k in konten if k.get("label") == label), None)
    if not konto:
        print(f"Konto '{label}' nicht in config/imap-accounts.json", file=sys.stderr)
        return 2
    pw = env_wert(konto["password_env"])
    if not pw:
        print(f"Passwort {konto['password_env']} fehlt in der .env", file=sys.stderr)
        return 2

    # Der Server verlangt unter Windows einen Ordner, auf den nur dieses Konto Zugriff hat.
    # Nicht C:\CEO-GPT-PrimaerBau (erbt Schreibrecht fuer alle Benutzer) und nicht %LOCALAPPDATA%
    # (dort hat auch die Claude-App als Paket Vollzugriff), sondern der Benutzerordner.
    cfg_dir = Path.home() / ".ceo-gpt-primaerbau" / "mcp-email"
    cfg_dir.mkdir(parents=True, exist_ok=True)
    env = {k: v for k, v in os.environ.items() if not k.startswith("MCP_EMAIL_SERVER_")}
    env.update({
        "MCP_EMAIL_SERVER_CONFIG_PATH": str(cfg_dir / f"{label}.toml"),
        "MCP_EMAIL_SERVER_CREDENTIAL_STORAGE": "plaintext",  # nichts wird gespeichert, alles kommt aus Env
        "MCP_EMAIL_SERVER_ACCOUNT_NAME": label,
        "MCP_EMAIL_SERVER_FULL_NAME": konto.get("full_name", konto["username"]),
        "MCP_EMAIL_SERVER_EMAIL_ADDRESS": konto["username"],
        "MCP_EMAIL_SERVER_USER_NAME": konto["username"],
        "MCP_EMAIL_SERVER_PASSWORD": pw,
        "MCP_EMAIL_SERVER_IMAP_HOST": konto["imap_host"],
        "MCP_EMAIL_SERVER_IMAP_PORT": str(konto.get("imap_port", 993)),
        "MCP_EMAIL_SERVER_IMAP_SSL": "true",
        "MCP_EMAIL_SERVER_DRAFTS_MAILBOX": konto.get("drafts_mailbox", "Entwürfe"),
        "MCP_EMAIL_SERVER_ACCOUNT_ALLOWED_MUTATIONS": "draft",
        "MCP_EMAIL_SERVER_ALLOWED_MUTATIONS": "draft",
        "PYTHONUTF8": "1",
    })
    uvx = str(UVX) if UVX.exists() else "uvx"
    return subprocess.call([uvx, "--quiet", "--from", SERVER, "mcp-email-server", "stdio"], env=env)


if __name__ == "__main__":
    sys.exit(main())
