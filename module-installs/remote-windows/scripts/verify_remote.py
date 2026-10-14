#!/usr/bin/env python3
"""
CEO-GPT Remote-Windows, Endkontrolle IN DER VM.

Prueft, ob in der Ubuntu-VM alles steht: Workspace, venv, Datenbank, .env,
MCP-Konfig, die ceo-gpt-* systemd-Dienste (und Timer) und Tailscale.
Read-only, stdlib-only, liest niemals den Inhalt der .env.

Aufruf (in der VM, aus dem migrierten/aufgebauten Workspace):
  python3 verify_remote.py
"""
import subprocess
import sys
from pathlib import Path


def run(cmd):
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    except Exception:
        return None


def find_workspace() -> Path:
    for cand in [Path.cwd()] + list(Path.cwd().parents):
        if (cand / "CLAUDE.md").exists() and (cand / "context").is_dir():
            return cand
    return Path.cwd()


def mark(ok):
    return "OK  " if ok else "FEHLT"


def main():
    ws = find_workspace()
    print(f"Endkontrolle in der VM, Workspace: {ws}\n")

    checks = []
    core = (ws / "CLAUDE.md").exists() and (ws / "context").is_dir()
    checks.append((core, "Workspace-Grundgeruest (CLAUDE.md, context/)"))

    venv_py = ws / ".venv" / "bin" / "python"
    venv_ok = venv_py.exists()
    ver = ""
    if venv_ok:
        r = run([str(venv_py), "--version"])
        ver = (r.stdout or r.stderr).strip() if r else ""
    checks.append((venv_ok, f"venv vorhanden {('(' + ver + ')') if ver else ''}"))

    db = ws / "data" / "data.db"
    checks.append((db.exists(), "Datenbank data/data.db vorhanden"))

    env = ws / ".env"
    checks.append((env.exists() and env.stat().st_size > 0, ".env vorhanden (Inhalt wird nicht gelesen)"))
    checks.append(((ws / ".mcp.json").exists(), ".mcp.json vorhanden"))
    checks.append(((ws / "requirements.txt").exists(), "requirements.txt vorhanden"))

    for ok, label in checks:
        print(f"  [{mark(ok)}] {label}")

    # systemd-Dienste
    print("\nHintergrund-Dienste (systemd, ceo-gpt-*):")
    r = run(["systemctl", "list-units", "--type=service", "--all", "--no-legend", "ceo-gpt-*"])
    units = []
    if r and r.returncode == 0:
        for line in r.stdout.splitlines():
            line = line.strip().lstrip("●").strip()  # evtl. fuehrenden Punkt entfernen
            parts = line.split()
            if parts and parts[0].startswith("ceo-gpt-"):
                name = parts[0]
                active = parts[2] if len(parts) > 2 else "?"
                units.append((name, active))
    if units:
        for name, active in sorted(units):
            print(f"  [{mark(active == 'active')}] {name} ({active})")
    else:
        print("  Keine ceo-gpt-* Dienste gefunden. Module installiert und 'systemctl enable' gesetzt?")

    # Timer
    rt = run(["systemctl", "list-timers", "--all", "--no-legend", "ceo-gpt-*"])
    timers = set()
    if rt and rt.returncode == 0:
        for line in rt.stdout.splitlines():
            for tok in line.split():
                if tok.startswith("ceo-gpt-") and tok.endswith(".timer"):
                    timers.add(tok)
    if timers:
        print(f"  Timer aktiv: {', '.join(sorted(timers))}")

    # Tailscale
    print("\nFernzugriff:")
    ts = run(["tailscale", "status"])
    if ts is not None and ts.returncode == 0:
        ip = run(["tailscale", "ip", "-4"])
        ipv = ip.stdout.strip().splitlines()[0] if (ip and ip.stdout.strip()) else "?"
        print(f"  [OK  ] Tailscale aktiv (IP {ipv})")
    else:
        print("  [FEHLT] Tailscale nicht aktiv. 'sudo tailscale up --ssh --unattended' ausstehend?")

    core_ok = all(ok for ok, _ in checks[:4])  # Workspace, venv, db, env
    print("\n" + ("Kern steht. Jetzt den Telegram-Bot mit einer echten Nachricht testen."
                  if core_ok else "Kern unvollstaendig, oben die FEHLT-Zeilen abarbeiten."))
    return 0 if core_ok else 1


if __name__ == "__main__":
    sys.exit(main())
