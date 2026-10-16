"""
Banking - Dateirechte "nur der Besitzer", auf Mac/Linux UND Windows.

WINDOWS-ANPASSUNG (PrimaerBau, 16.10.2026, siehe module-installs/bank-anbindung/ANPASSUNGEN.md):
Das Modul ist fuer macOS geschrieben und schuetzt seine Dateien mit
os.chmod(0o600 / 0o700). Unter Windows wirkt chmod nur auf das
Schreibschutz-Flag, die Datei bleibt fuer alle angemeldeten Benutzer lesbar
(st_mode 0o666). Deshalb setzt schuetze() unter Windows echte Zugriffsrechte:
Vererbung brechen, nur das eigene Konto und SYSTEM (S-1-5-18) erhalten Zugriff.

Fehlschlag ist kein Abbruch: wie bisher bei chmod laeuft das Modul weiter.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

IST_WINDOWS = sys.platform.startswith("win")
SID_SYSTEM = "S-1-5-18"


def _eigene_sid():
    """SID des angemeldeten Kontos (sprachunabhaengig, anders als Kontonamen)."""
    out = subprocess.run(
        ["whoami", "/user", "/fo", "csv", "/nh"],
        capture_output=True, text=True, timeout=10, check=True,
    ).stdout.strip()
    # "pc\\muba","S-1-5-21-..."
    return out.rsplit(",", 1)[-1].strip().strip('"')


def schuetze(pfad, modus=0o600):
    """Nur der Besitzer darf lesen/schreiben. Gibt True zurueck, wenn es klappte."""
    p = Path(pfad)
    if not IST_WINDOWS:
        try:
            os.chmod(p, modus)
            return True
        except Exception:
            return False
    try:
        sid = _eigene_sid()
        erben = "(OI)(CI)" if p.is_dir() else ""
        subprocess.run(
            ["icacls", str(p), "/inheritance:r",
             "/grant:r", f"*{sid}:{erben}F", f"*{SID_SYSTEM}:{erben}F"],
            capture_output=True, timeout=20, check=True,
        )
        return True
    except Exception:
        return False


def nur_besitzer(pfad):
    """Pruefung fuer den Selbsttest: liegt der Schutz wirklich an?

    Mac/Linux: Rechte sind exakt 0600 (Datei) bzw. 0700 (Ordner).
    Windows: keine geerbten Eintraege, und nur eigenes Konto + SYSTEM."""
    p = Path(pfad)
    if not IST_WINDOWS:
        soll = 0o700 if p.is_dir() else 0o600
        return (p.stat().st_mode & 0o777) == soll
    ps = (
        "$a = Get-Acl -LiteralPath $env:PFAD; "
        "$a.Access | ForEach-Object { "
        "$_.IdentityReference.Translate([System.Security.Principal.SecurityIdentifier]).Value "
        "+ '|' + $_.IsInherited }"
    )
    try:
        out = subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps],
            capture_output=True, text=True, timeout=30, check=True,
            env={**os.environ, "PFAD": str(p)},
        ).stdout.split()
    except Exception:
        return False
    erlaubt = {_eigene_sid(), SID_SYSTEM}
    if not out:
        return False
    for zeile in out:
        sid, _, geerbt = zeile.partition("|")
        if geerbt.lower() == "true" or sid not in erlaubt:
            return False
    return True
