"""Windows-Starter fuer die naechtliche Sicherung (auto_commit.py).

Laeuft unsichtbar ueber pythonw.exe aus der Windows-Aufgabenplanung.
- schreibt die Ausgabe nach data/auto_commit.log (bleibt lokal, steht in .gitignore)
- holt einen liegengebliebenen Push nach, auch wenn es nichts Neues zu speichern gibt
"""

import os
import sys
import subprocess
from datetime import datetime
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
LOG = REPO / "data" / "auto_commit.log"
LOG.parent.mkdir(exist_ok=True)

os.environ.setdefault("PYTHONUTF8", "1")
os.environ["GIT_TERMINAL_PROMPT"] = "0"  # nie auf eine Eingabe warten

log_file = open(LOG, "a", encoding="utf-8")
sys.stdout = sys.stderr = log_file
print(f"\n===== {datetime.now():%Y-%m-%d %H:%M} =====", flush=True)

sys.path.insert(0, str(Path(__file__).resolve().parent))
os.chdir(REPO)

rc = 1
try:
    import auto_commit
    rc = auto_commit.main()
except Exception as exc:  # Sicherung darf nie still sterben
    print(f"[auto-commit] Fehler: {exc}", flush=True)

# Liegengebliebene Speicherpunkte nachschieben
ahead = subprocess.run(["git", "rev-list", "--count", "@{u}..HEAD"], cwd=REPO,
                       capture_output=True, text=True, encoding="utf-8")
if ahead.returncode == 0 and ahead.stdout.strip() not in ("", "0"):
    push = subprocess.run(["git", "push"], cwd=REPO, capture_output=True, text=True, encoding="utf-8")
    print(f"[auto-commit] Nachgeschoben ({ahead.stdout.strip()} Speicherpunkte): "
          f"{'ok' if push.returncode == 0 else 'gescheitert'}", flush=True)
    rc = rc if push.returncode == 0 else 1

log_file.close()
sys.exit(rc)
