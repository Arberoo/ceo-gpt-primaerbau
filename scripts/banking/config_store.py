"""
Banking - nicht-geheime Config (data/banking/config.json).

Haelt Metadaten pro Bank. KEINE Zugangsdaten: die liegen beim FinTS-Weg im
Schluesselbund (siehe keychain.py) und beim PSD2-Weg als Dateien in
data/banking/psd2/ (siehe psd2.py).

ZWEI WEGE, EINE LISTE (seit 2026-08-31):
Jeder Eintrag traegt 'weg' -- entweder "fints" (deutsche Bank ueber FinTS/HBCI,
Login und PIN im Schluesselbund) oder "psd2" (Enable Banking, Freigabe in der
Bank-App). Sie stehen bewusst in DERSELBEN Liste, damit der Sammler und die
Uebersicht nicht zwei Quellen zusammensuchen muessen.

RUECKWAERTSKOMPATIBEL: Eintraege aus der Zeit vor dem zweiten Weg haben weder
'key' noch 'weg'. Fuer die gilt der Schluessel = blz und der Weg = fints. Eine
bestehende Installation braucht deshalb keine Migration und merkt vom Umbau
nichts.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

from banking import rechte  # Windows-Anpassung: Rechte nur fuer den Besitzer

# scripts/banking/config_store.py -> WORKSPACE_ROOT ist drei Ebenen hoch
WORKSPACE_ROOT = Path(__file__).resolve().parent.parent.parent
BANKING_DIR = WORKSPACE_ROOT / "data" / "banking"
CONFIG_PATH = BANKING_DIR / "config.json"
PSD2_DIR = BANKING_DIR / "psd2"

WEG_FINTS = "fints"
WEG_PSD2 = "psd2"


def _ensure_dir():
    BANKING_DIR.mkdir(parents=True, exist_ok=True)
    try:
        rechte.schuetze(BANKING_DIR, 0o700)  # Windows-Anpassung, siehe rechte.py
    except Exception:
        pass


def psd2_dir():
    """Ordner fuer den PSD2-Zugang. Wird bei Bedarf mit 0700 angelegt."""
    PSD2_DIR.mkdir(parents=True, exist_ok=True)
    try:
        rechte.schuetze(PSD2_DIR, 0o700)  # Windows-Anpassung, siehe rechte.py
    except Exception:
        pass
    return PSD2_DIR


def load():
    if not CONFIG_PATH.exists():
        return {"banks": []}
    try:
        return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {"banks": []}


def save(cfg):
    _ensure_dir()
    CONFIG_PATH.write_text(
        json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    try:
        rechte.schuetze(CONFIG_PATH, 0o600)  # Windows-Anpassung, siehe rechte.py
    except Exception:
        pass


def bank_key(bank):
    """Der Schluessel eines Eintrags.

    Rueckfall auf blz, damit Konfigs aus der Zeit vor dem zweiten Weg
    unveraendert weiterlaufen."""
    return bank.get("key") or bank.get("blz") or ""


def bank_weg(bank):
    """Der Weg eines Eintrags. Fehlt die Angabe, ist es ein Alt-Eintrag und
    damit FinTS -- vor dem 31.08.2026 gab es nichts anderes."""
    return bank.get("weg") or WEG_FINTS


def banks(weg=None):
    """Alle Eintraege, optional nach Weg gefiltert."""
    alle = load().get("banks", [])
    if weg is None:
        return alle
    return [b for b in alle if bank_weg(b) == weg]


def get_bank(key):
    """Eintrag ueber den Schluessel. Findet auch Alt-Eintraege ueber ihre BLZ."""
    for b in load().get("banks", []):
        if bank_key(b) == key:
            return b
    return None


def upsert_bank(bank):
    cfg = load()
    banks_ = cfg.setdefault("banks", [])
    schluessel = bank_key(bank)
    for i, b in enumerate(banks_):
        if bank_key(b) == schluessel:
            banks_[i] = bank
            break
    else:
        banks_.append(bank)
    save(cfg)
    return bank


def remove_bank(key):
    cfg = load()
    cfg["banks"] = [b for b in cfg.get("banks", []) if bank_key(b) != key]
    save(cfg)


def session_path(blz):
    """Nur FinTS. Der PSD2-Weg legt seine Freigaben in psd2/sessions.json ab."""
    return str(BANKING_DIR / f"{blz}.session")
