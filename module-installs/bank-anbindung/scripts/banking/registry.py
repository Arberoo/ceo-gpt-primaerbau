"""
Banking - FinTS-Institut-Registry.

Loest Bankleitzahl (BLZ) bzw. deutsche IBAN auf die FinTS-PIN/TAN-Server-URL auf,
damit der Kunde beim Setup nur seine IBAN angeben muss und der Server automatisch
gefunden wird (pro Bank ein eigener Server).

Datenquelle: gebuendelter Snapshot der hbci4j-BLZ-Datenbank
(data/fints_institutes.properties). Siehe data/SOURCE.md.
Format pro Zeile: BLZ=Name|Ort|BIC|version|dns|pintan_url|...
"""
from __future__ import annotations

import re
import urllib.request
from pathlib import Path

DATA_FILE = Path(__file__).resolve().parent / "data" / "fints_institutes.properties"
MIRROR_URL = (
    "https://raw.githubusercontent.com/hbci4j/hbci4java/master/"
    "src/main/resources/blz.properties"
)

_CACHE = None


def _load():
    global _CACHE
    if _CACHE is not None:
        return _CACHE
    institutes = {}
    if DATA_FILE.exists():
        for line in DATA_FILE.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            blz, _, rest = line.partition("=")
            blz = blz.strip()
            if not blz.isdigit():
                continue
            parts = rest.split("|")
            name = parts[0].strip() if len(parts) > 0 else ""
            bic = parts[2].strip() if len(parts) > 2 else ""
            url = parts[5].strip() if len(parts) > 5 else ""
            if not url.startswith("http"):
                url = ""
            institutes[blz] = {
                "blz": blz,
                "bank_name": name,
                "bic": bic,
                "pintan_url": url,
            }
    _CACHE = institutes
    return institutes


def normalize_iban(iban):
    return re.sub(r"\s+", "", (iban or "")).upper()


def extract_blz_from_iban(iban):
    """Deutsche IBAN: DE + 2 Pruefziffern + 8 BLZ + 10 Kontonummer."""
    iban = normalize_iban(iban)
    if not iban.startswith("DE") or len(iban) < 12 or not iban[2:].isdigit():
        raise ValueError(
            f"Keine gueltige deutsche IBAN: {iban!r}. "
            "FinTS unterstuetzt nur deutsche Banken."
        )
    return iban[4:12]


def lookup(blz):
    """BLZ -> {blz, bank_name, bic, pintan_url} oder None."""
    return _load().get((blz or "").strip())


def lookup_by_iban(iban):
    """IBAN -> Institut-Dict. Wenn unbekannt: Dict mit leerer pintan_url."""
    blz = extract_blz_from_iban(iban)
    info = lookup(blz)
    if info is None:
        return {"blz": blz, "bank_name": "", "bic": "", "pintan_url": ""}
    return info


def refresh():
    """Laedt eine frische BLZ-Datei vom Mirror und ueberschreibt den Snapshot."""
    global _CACHE
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(MIRROR_URL, timeout=30) as r:
        content = r.read().decode("utf-8", errors="replace")
    DATA_FILE.write_text(content, encoding="utf-8")
    _CACHE = None
    return len(_load())


if __name__ == "__main__":
    import sys

    insts = _load()
    print(f"{len(insts)} Institute geladen aus {DATA_FILE}")
    for blz in (sys.argv[1:] or ["25050000", "12030000", "50010517"]):
        print(blz, "->", lookup(blz))
