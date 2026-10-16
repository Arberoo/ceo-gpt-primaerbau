"""
Taeglicher DataOS-Lauf unter Windows (Gegenstueck zu launchd com.ceogpt.daten-collect).

Startet scripts/collect.py (alle collect_*.py, derzeit nur die Bankanbindung)
und schreibt die Ausgabe nach data/daten_abruf.log, weil pythonw kein Fenster
und keine Konsole hat. Eingerichtet ueber scripts/setup_daten_abruf_windows.ps1.

Headless: fragt nie nach TAN oder PIN. Braucht die Bank eine Bestaetigung,
meldet der Bank-Sammler needs_tan (sichtbar in data/kennzahlen/key-metrics.md).
"""
import runpy
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOG = ROOT / "data" / "daten_abruf.log"


def main():
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG, "a", encoding="utf-8") as log:
        sys.stdout = sys.stderr = log
        print(f"\n===== {datetime.now():%Y-%m-%d %H:%M} =====")
        sys.argv = [str(ROOT / "scripts" / "collect.py")]
        code = 0
        try:
            runpy.run_path(str(ROOT / "scripts" / "collect.py"), run_name="__main__")
        except SystemExit as e:
            code = e.code or 0
        except Exception as e:  # nie still sterben, immer ins Log
            print(f"Abbruch: {type(e).__name__}: {e}")
            code = 1
        log.flush()
    return code


if __name__ == "__main__":
    sys.exit(main())
