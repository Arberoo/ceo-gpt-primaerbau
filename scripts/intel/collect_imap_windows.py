"""Windows-Starter fuer den Mail-Sammler (collect_imap.py) aus der Aufgabenplanung.

Laeuft unsichtbar ueber pythonw.exe, schreibt die Ausgabe nach data/imap_collect.log.
Holt nur, was neu ist (resumable ueber UID/UIDVALIDITY). Laeuft stuendlich als Sicherheitsabgleich
ALLER Ordner; neue Mails in INBOX/Gesendete kommen sofort ueber den IDLE-Dauerlaeufer idle_imap.py.
Steht dieser (kein Lebenszeichen in data/mail_sofort_status.json), wird er hier neu gestartet.
"""

import os
import sys
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
WORKSPACE = HERE.parent.parent
LOG = WORKSPACE / "data" / "imap_collect.log"
LOG.parent.mkdir(exist_ok=True)

# Log klein halten: ab 2 MB neu anfangen
if LOG.exists() and LOG.stat().st_size > 2_000_000:
    LOG.replace(LOG.with_suffix(".log.alt"))

log = open(LOG, "a", encoding="utf-8")
sys.stdout = sys.stderr = log
print(f"\n===== {datetime.now():%Y-%m-%d %H:%M} =====", flush=True)
os.chdir(WORKSPACE)
sys.path.insert(0, str(HERE))
sys.argv = [str(HERE / "collect_imap.py")]

rc = 1
try:
    import runpy
    runpy.run_path(str(HERE / "collect_imap.py"), run_name="__main__")
    rc = 0
except SystemExit as e:
    rc = e.code if isinstance(e.code, int) else 0
except Exception as e:
    print(f"[collect] Fehler: {e}", flush=True)

# Waechter: Sofort-Abruf (IDLE) neu starten, falls er kein Lebenszeichen mehr gibt
try:
    import json, subprocess
    from datetime import timezone
    status = WORKSPACE / "data" / "mail_sofort_status.json"
    age = None
    if status.exists():
        beat = datetime.fromisoformat(json.loads(status.read_text(encoding="utf-8"))["herzschlag"])
        age = (datetime.now(timezone.utc) - beat).total_seconds()
    if age is None or age > 15 * 60:
        r = subprocess.run(["schtasks", "/run", "/tn", "CEO-GPT PrimaerBau Mail-Sofort"],
                           capture_output=True, text=True, creationflags=0x08000000)
        print(f"[collect] Sofort-Abruf stand, neu gestartet: {'ok' if r.returncode == 0 else 'gescheitert'}", flush=True)
except Exception as e:
    print(f"[collect] Waechter-Fehler: {e}", flush=True)

log.close()
sys.exit(rc)
