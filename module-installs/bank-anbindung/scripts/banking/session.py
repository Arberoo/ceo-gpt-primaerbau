"""
Banking - FinTS-Session-Persistenz.

Speichert/laedt den serialisierten Client-State (client.deconstruct) als
lokale Datei mit Rechten 0600.

SICHERHEIT: from_data NUR aus eigenen, lokal geschriebenen Blobs laden.
python-fints warnt explizit, dass das Deserialisieren von fremden Quellen
gefaehrlich ist (pickle-aehnliches Risiko). Diese Datei wird nur lokal vom
Modul selbst geschrieben und gelesen.
"""
from __future__ import annotations

import os
from pathlib import Path


def save(path, blob):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(blob)
    try:
        os.chmod(p, 0o600)
    except Exception:
        pass


def load(path):
    if not path:
        return None
    p = Path(path)
    if not p.exists():
        return None
    try:
        return p.read_bytes()
    except Exception:
        return None


def clear(path):
    try:
        Path(path).unlink()
    except Exception:
        pass
