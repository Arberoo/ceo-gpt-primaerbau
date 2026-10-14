"""Windows-Starter fuer den Mail-Sammler (collect_imap.py) aus der Aufgabenplanung.

Laeuft unsichtbar ueber pythonw.exe, schreibt die Ausgabe nach data/imap_collect.log.
Holt nur, was neu ist (resumable ueber UID/UIDVALIDITY). Uebergangsloesung im 15-Minuten-Takt,
bis der IDLE-Dauerlaeufer steht (siehe module-installs/intelligenz-imap/ANPASSUNGEN.md).
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
log.close()
sys.exit(rc)
