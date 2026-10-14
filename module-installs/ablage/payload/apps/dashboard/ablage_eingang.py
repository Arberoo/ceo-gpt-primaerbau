"""Eingangsfach der automatischen Ablage: hier landet jede Datei zuerst.

Quellen-neutral mit Absicht. Egal ob eine Datei per Drag-und-Drop aus dem
Cockpit kommt, spaeter aus einem Mail-Anhang oder aus einem beobachteten
Ordner: sie landet hier und sieht danach gleich aus. Genau das macht den
Eingang zum austauschbaren Teil (siehe reference/ablage.md).

Zustaende einer Datei:
    neu -> gelesen -> vorgeschlagen -> abgelegt | abgelehnt | fehler

Zwei Sicherungen, die nicht wegoptimiert werden duerfen:

1. DAS ORIGINAL BLEIBT LIEGEN, bis die Ablage bestaetigt ist. Erst nach
   erfolgreichem Upload wird der Datensatz auf `abgelegt` gesetzt. Ein halb
   gescheiterter Stapel verliert damit keine einzige Datei.
2. DER DATEINAME WIRD GESAEUBERT, bevor irgendetwas auf die Platte geht
   (Muster dokumente._datei_pruefen). Ein "../" im Namen darf nie aus dem
   Eingangsordner herausfuehren.

Dubletten laufen ueber den sha256 des INHALTS, nicht ueber den Namen: dieselbe
Rechnung zweimal reingezogen (einmal als "scan.pdf", einmal als "scan (1).pdf")
ist eine Datei, kein zweiter Eintrag.
"""
import hashlib
import json
import re
import sqlite3
import uuid
from contextlib import closing
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DB_PATH = ROOT / "data" / "data.db"
EINGANG_DIR = ROOT / "data" / "ablage" / "eingang"

MAX_BYTES = 25 * 1024 * 1024 # wie dokumente.MAX_UPLOAD_BYTES

# Was der Leser wirklich lesen kann. Alles andere wird mit klarem Grund
# abgelehnt statt still verworfen - eine Datei, die spurlos verschwindet, ist
# der teuerste Fehler, den ein Ablagesystem machen kann.
ERLAUBT = {
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".doc": "application/msword",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".xls": "application/vnd.ms-excel",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".heic": "image/heic",
    ".webp": "image/webp",
    ".txt": "text/plain",
    ".md": "text/markdown",
    ".csv": "text/csv",
}

STATUS_OFFEN = ("neu", "gelesen", "vorgeschlagen", "fehler")


def _conn():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH), timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout=30000")
    _ensure_tables(conn)
    return conn


def _ensure_tables(conn):
    conn.execute(
        "CREATE TABLE IF NOT EXISTS ablage_eingang ("
        "id TEXT PRIMARY KEY, "
        "datei_rel TEXT, " # ROOT-relativer Pfad
        "orig_name TEXT, "
        "groesse INTEGER, "
        "mime TEXT, "
        "quelle TEXT, " # cockpit | mail | foto | …
        "sha256 TEXT, "
        "status TEXT, "
        "erkannt_json TEXT, " # Ergebnis des Lesers
        "vorschlag_json TEXT, " # Ergebnis der Einordnung
        "erstellt TEXT, "
        "erledigt TEXT, "
        "fehler TEXT)")
    conn.execute("CREATE INDEX IF NOT EXISTS ix_ablage_eingang_status "
                 "ON ablage_eingang(status)")
    conn.execute("CREATE INDEX IF NOT EXISTS ix_ablage_eingang_sha "
                 "ON ablage_eingang(sha256)")
    conn.commit()


def sicherer_name(name):
    """Dateiname ohne alles, was aus dem Ordner herausfuehren koennte."""
    roh = (name or "datei").strip().replace("\\", "/").split("/")[-1]
    safe = re.sub(r"[^A-Za-z0-9._-]", "_", roh).lstrip(".") or "datei"
    return safe[:150]


def _suffix(name):
    s = Path(sicherer_name(name)).suffix.lower()
    return s if s in ERLAUBT else ""


def annehmen(name, daten, quelle="cockpit"):
    """Datei ins Eingangsfach legen. Gibt (ok, id_oder_grund) zurueck."""
    if not isinstance(daten, (bytes, bytearray)) or not daten:
        return False, "leere Datei"
    if len(daten) > MAX_BYTES:
        mb = len(daten) / 1024 / 1024
        return False, f"zu gross ({mb:.1f} MB, erlaubt sind {MAX_BYTES // 1024 // 1024} MB)"
    suffix = _suffix(name)
    if not suffix:
        endung = Path(sicherer_name(name)).suffix or "ohne Endung"
        return False, f"Dateityp {endung} wird nicht gelesen"

    daten = bytes(daten)
    sha = hashlib.sha256(daten).hexdigest()
    with closing(_conn()) as conn:
        # Dublette: nur gegen OFFENE Eintraege pruefen. Dieselbe Datei nach
        # Monaten erneut abzulegen ist ein legitimer Vorgang (zweite Fassung,
        # erneuter Scan) - nur zweimal im selben Stapel ist einer zu viel.
        frage = ",".join("?" * len(STATUS_OFFEN))
        alt = conn.execute(
            f"SELECT id, orig_name FROM ablage_eingang WHERE sha256=? "
            f"AND status IN ({frage})", (sha, *STATUS_OFFEN)).fetchone()
        if alt:
            return False, f"liegt schon im Eingang als „{alt['orig_name']}\""

        eid = "eing-" + uuid.uuid4().hex[:12]
        EINGANG_DIR.mkdir(parents=True, exist_ok=True)
        ziel = EINGANG_DIR / f"{eid}{suffix}"
        tmp = ziel.with_suffix(ziel.suffix + ".tmp")
        tmp.write_bytes(daten)
        tmp.replace(ziel) # atomar, nie eine halbe Datei
        conn.execute(
            "INSERT INTO ablage_eingang (id, datei_rel, orig_name, groesse, mime, "
            "quelle, sha256, status, erstellt) VALUES (?,?,?,?,?,?,?,?,?)",
            (eid, str(ziel.relative_to(ROOT)), sicherer_name(name), len(daten),
             ERLAUBT[suffix], str(quelle)[:40], sha, "neu",
             datetime.now().isoformat(timespec="seconds")))
        conn.commit()
    return True, eid


def _row(r):
    d = dict(r)
    for feld in ("erkannt_json", "vorschlag_json"):
        roh = d.pop(feld, None)
        kurz = feld.replace("_json", "")
        try:
            d[kurz] = json.loads(roh) if roh else None
        except Exception:
            d[kurz] = None
    d["pfad"] = str(ROOT / d["datei_rel"]) if d.get("datei_rel") else None
    return d


def liste(status=None):
    """Eintraege, aelteste zuerst (ein Stapel wird der Reihe nach abgearbeitet)."""
    with closing(_conn()) as conn:
        if status:
            stat = (status,) if isinstance(status, str) else tuple(status)
            frage = ",".join("?" * len(stat))
            rows = conn.execute(
                f"SELECT * FROM ablage_eingang WHERE status IN ({frage}) "
                "ORDER BY erstellt", stat).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM ablage_eingang ORDER BY erstellt").fetchall()
    return [_row(r) for r in rows]


def offene():
    return liste(STATUS_OFFEN)


def holen(eid):
    with closing(_conn()) as conn:
        r = conn.execute("SELECT * FROM ablage_eingang WHERE id=?", (eid,)).fetchone()
    return _row(r) if r else None


def setze_status(eid, status, erkannt=None, vorschlag=None, fehler=None):
    felder, werte = ["status=?"], [status]
    if erkannt is not None:
        felder.append("erkannt_json=?"); werte.append(json.dumps(erkannt, ensure_ascii=False))
    if vorschlag is not None:
        felder.append("vorschlag_json=?"); werte.append(json.dumps(vorschlag, ensure_ascii=False))
    if fehler is not None:
        felder.append("fehler=?"); werte.append(str(fehler)[:500])
    if status in ("abgelegt", "abgelehnt"):
        felder.append("erledigt=?"); werte.append(datetime.now().isoformat(timespec="seconds"))
    werte.append(eid)
    with closing(_conn()) as conn:
        conn.execute(f"UPDATE ablage_eingang SET {', '.join(felder)} WHERE id=?", werte)
        conn.commit()
    return True


def daten(eid):
    """Roher Dateiinhalt. None, wenn die Datei nicht (mehr) da ist."""
    e = holen(eid)
    if not e or not e.get("datei_rel"):
        return None
    p = ROOT / e["datei_rel"]
    try:
        return p.read_bytes()
    except Exception:
        return None


def aufraeumen(eid, datei_loeschen=True):
    """Nach bestaetigter Ablage die Kopie im Eingang entfernen. Der DATENSATZ
    bleibt (er ist der Verlauf und die Idempotenz-Sperre)."""
    e = holen(eid)
    if e and datei_loeschen and e.get("datei_rel"):
        try:
            (ROOT / e["datei_rel"]).unlink()
        except Exception:
            pass
    return True


def entfernen(eid):
    """Ganz verwerfen: Datei weg, Datensatz auf abgelehnt (nicht geloescht,
    sonst kommt dieselbe Datei beim naechsten Reinziehen sofort wieder)."""
    aufraeumen(eid)
    return setze_status(eid, "abgelehnt")
