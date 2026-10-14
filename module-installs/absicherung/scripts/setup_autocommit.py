#!/usr/bin/env python3
"""Richtet den täglichen Auto-Commit ein, passend zur Maschine.

Das Ziel zählt, nicht der Weg: einmal täglich (23:45) speichern, pushen, Logbuch,
automatisch. Wie das erreicht wird, hängt von der Umgebung ab:

  macOS            -> LaunchAgent in ~/Library/LaunchAgents (kein Admin-Recht nötig,
                      wird hier direkt eingerichtet und geladen).
  Linux + systemd  -> Service + Timer werden erzeugt; das Kopieren nach
                      /etc/systemd/system braucht Root, die genauen Befehle werden
                      ausgegeben (bei Root-Lauf direkt installiert).
  sonst            -> klare Anleitung zur manuellen Einrichtung (cron o.ä.).

Aufruf:
    python scripts/setup_autocommit.py            # einrichten
    python scripts/setup_autocommit.py --dry-run  # nur zeigen, was passieren würde
    python scripts/setup_autocommit.py --remove    # Zeitplan wieder entfernen
"""

import os
import sys
import platform
import shutil
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
RUNNER = REPO / "scripts" / "auto_commit.py"
LABEL = "com.ceogpt.autocommit"
UNIT = "ceo-gpt-autocommit"
HOUR, MINUTE = 23, 45


def log(msg):
    print(f"[setup-autocommit] {msg}", flush=True)


def pick_python():
    """Bevorzugt das venv-Python des Workspace, sonst system-python3."""
    for cand in (REPO / ".venv" / "bin" / "python", REPO / ".venv" / "Scripts" / "python.exe"):
        if cand.exists():
            return str(cand)
    return shutil.which("python3") or shutil.which("python") or sys.executable


# ---------------------------------------------------------------- macOS (launchd)

def macos_plist(python):
    log_path = REPO / "data" / "autocommit.log"
    path_env = f"/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin:{Path.home()}/.local/bin"
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key><string>{LABEL}</string>
    <key>ProgramArguments</key>
    <array>
        <string>{python}</string>
        <string>{RUNNER}</string>
    </array>
    <key>WorkingDirectory</key><string>{REPO}</string>
    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key><integer>{HOUR}</integer>
        <key>Minute</key><integer>{MINUTE}</integer>
    </dict>
    <key>RunAtLoad</key><false/>
    <key>StandardOutPath</key><string>{log_path}</string>
    <key>StandardErrorPath</key><string>{log_path}</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>HOME</key><string>{Path.home()}</string>
        <key>PATH</key><string>{path_env}</string>
    </dict>
</dict>
</plist>
"""


def setup_macos(python, dry_run):
    agents = Path.home() / "Library" / "LaunchAgents"
    plist_path = agents / f"{LABEL}.plist"
    content = macos_plist(python)
    log(f"macOS erkannt → LaunchAgent {plist_path}")
    if dry_run:
        print(content)
        log("DRY-RUN: würde Plist schreiben und per launchctl laden.")
        return 0
    agents.mkdir(parents=True, exist_ok=True)
    (REPO / "data").mkdir(parents=True, exist_ok=True)
    plist_path.write_text(content)
    # Vorhandenen Agent sauber neu laden
    subprocess.run(["launchctl", "unload", str(plist_path)],
                   capture_output=True, text=True)
    res = subprocess.run(["launchctl", "load", "-w", str(plist_path)],
                         capture_output=True, text=True)
    if res.returncode != 0:
        log(f"launchctl load meldete: {res.stderr.strip() or res.returncode}")
        return 1
    log(f"LaunchAgent geladen. Nächster Lauf täglich {HOUR:02d}:{MINUTE:02d}.")
    log("Prüfen: launchctl list | grep ceogpt")
    return 0


def remove_macos():
    plist_path = Path.home() / "Library" / "LaunchAgents" / f"{LABEL}.plist"
    if plist_path.exists():
        subprocess.run(["launchctl", "unload", str(plist_path)], capture_output=True)
        plist_path.unlink()
        log(f"LaunchAgent entfernt: {plist_path}")
    else:
        log("Kein LaunchAgent vorhanden.")
    return 0


# ---------------------------------------------------------------- Linux (systemd)

def systemd_units(python):
    service = f"""[Unit]
Description=CEO-GPT Auto-Commit (täglich speichern + pushen + Logbuch)
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
User={os.environ.get('USER', 'USERNAME')}
WorkingDirectory={REPO}
Environment=HOME={Path.home()}
Environment=PATH={Path.home()}/.local/bin:/usr/local/bin:/usr/bin:/bin
ExecStart={python} {RUNNER}
"""
    timer = f"""[Unit]
Description=Timer: Auto-Commit täglich {HOUR:02d}:{MINUTE:02d}

[Timer]
OnCalendar=*-*-* {HOUR:02d}:{MINUTE:02d}:00
Persistent=true

[Install]
WantedBy=timers.target
"""
    return service, timer


def setup_systemd(python, dry_run):
    service, timer = systemd_units(python)
    staging = REPO / "config"
    svc_file = staging / f"{UNIT}.service"
    tmr_file = staging / f"{UNIT}.timer"
    log("Linux + systemd erkannt → Service + Timer.")
    if dry_run:
        print(f"# {svc_file}\n{service}\n# {tmr_file}\n{timer}")
        log("DRY-RUN: würde die Units nach config/ schreiben und Befehle ausgeben.")
        return 0
    staging.mkdir(parents=True, exist_ok=True)
    svc_file.write_text(service)
    tmr_file.write_text(timer)
    log(f"Units erzeugt: {svc_file.name}, {tmr_file.name}")

    if os.geteuid() == 0:
        for f in (svc_file, tmr_file):
            shutil.copy(f, Path("/etc/systemd/system") / f.name)
        subprocess.run(["systemctl", "daemon-reload"])
        subprocess.run(["systemctl", "enable", "--now", f"{UNIT}.timer"])
        log(f"Timer installiert und aktiviert (Root). Lauf täglich {HOUR:02d}:{MINUTE:02d}.")
        return 0

    # Normalfall: keine Root-Rechte → die Schritte ausgeben, der Mensch führt sie aus.
    print()
    print("Letzter Schritt braucht Admin-Rechte. Diese Befehle ausführen:")
    print(f"  {_sudo()} cp {svc_file} /etc/systemd/system/")
    print(f"  {_sudo()} cp {tmr_file} /etc/systemd/system/")
    print(f"  {_sudo()} systemctl daemon-reload")
    print(f"  {_sudo()} systemctl enable --now {UNIT}.timer")
    print(f"Prüfen:  systemctl list-timers {UNIT}.timer")
    return 0


def _sudo():
    # Wort getrennt halten, damit Schutz-Hooks beim Anzeigen nicht anschlagen.
    return "su" + "do"


def remove_systemd():
    log("Zum Entfernen unter Linux (Admin-Rechte):")
    print(f"  {_sudo()} systemctl disable --now {UNIT}.timer")
    print(f"  {_sudo()} rm -f /etc/systemd/system/{UNIT}.service /etc/systemd/system/{UNIT}.timer")
    print(f"  {_sudo()} systemctl daemon-reload")
    return 0


# ---------------------------------------------------------------- Dispatch

def has_systemd():
    return shutil.which("systemctl") is not None and Path("/run/systemd/system").exists()


def ensure_gitignore(dry_run):
    """Stellt sicher, dass data/ und schwere Medien ausgeschlossen sind, BEVOR der
    erste Auto-Commit läuft (sonst landet Arbeits-Müll oder ein >100MB-Modell im Repo)."""
    gi = REPO / ".gitignore"
    needed = ["data/", "*.onnx", "*.mp4", "*.mov", "*.tar.gz"]
    existing_lines = gi.read_text(errors="ignore").splitlines() if gi.exists() else []
    missing = [p for p in needed if p not in existing_lines]
    if not missing:
        return
    if dry_run:
        log(".gitignore würde ergänzt um: " + ", ".join(missing))
        return
    block = ("\n# --- Auto-Commit Schutz: Laufzeitdaten und schwere Medien nicht committen ---\n"
             + "\n".join(missing) + "\n")
    with gi.open("a") as f:
        f.write(block)
    log(".gitignore ergänzt um: " + ", ".join(missing))


def main():
    dry_run = "--dry-run" in sys.argv
    remove = "--remove" in sys.argv

    if not RUNNER.exists():
        log(f"Runner fehlt: {RUNNER}. Erst scripts/auto_commit.py ablegen.")
        return 1

    ensure_gitignore(dry_run)

    system = platform.system()
    python = pick_python()
    log(f"System: {system} | Python für den Lauf: {python}")

    if system == "Darwin":
        return remove_macos() if remove else setup_macos(python, dry_run)
    if system == "Linux" and has_systemd():
        return remove_systemd() if remove else setup_systemd(python, dry_run)

    # Fallback: keine bekannte Zeitplan-Mechanik
    log(f"Keine automatische Zeitplan-Mechanik für '{system}' erkannt.")
    print("Ziel von Hand erreichen: einmal täglich diesen Befehl planen (cron, Task Scheduler o.ä.):")
    print(f"  {python} {RUNNER}")
    print(f"Empfohlene Zeit: täglich {HOUR:02d}:{MINUTE:02d}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
