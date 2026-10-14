"""Ziel-Adapter der Ablage: DER austauschbare Teil.

Hier haengt jeder Kunde seinen eigenen Speicher ein, ohne dass Eingang, Leser,
Agent oder Oberflaeche sich aendern. Bei der Geschäftsführer sind es zwei: Google Drive
und die Dokumentenakte. Bei Rees waere es deren eigener Server, bei Reiber die
Samba-Freigabe - jeweils EIN neuer Adapter mit drei Funktionen.

VERTRAG EINES ADAPTERS (Muster: belege.QUELLEN)
-----------------------------------------------
    orte() -> [{"id","label","gruppe",...}]
    ablegen(ort, daten, name, meta) -> (ok: bool, info: str)
    existiert(ort, name) -> bool

Die Orte-Liste baut `ablage_struktur.orte()` zusammen; hier steht nur, wie
tatsaechlich geschrieben wird. Jeder Adapter faengt seine eigenen Fehler ab:
ein kaputtes Ziel darf die anderen nie mitreissen.

BUCHHALTUNG IST HIER BEWUSST KEIN ZIEL. Rechnungen legt `beleg_automatik.py`
ab (seit 24.08.2026). Zwei Automatiken, die dieselbe Rechnung an zwei Orte
legen, waeren der klassische Doppel-Fehler; ein Smoke-Check wacht darueber.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

# Ziel-Kennung, die die Einordnung setzt, wenn sie eine RECHNUNG erkennt.
# Sie ist KEIN Ablageort: der Ablage-Weg fasst solche Dateien nicht an.
BUCHHALTUNG = "buchhaltung"


def _drive_ablegen(ort, daten, name, meta=None):
    from apps.dashboard import ablage_drive as bd
    mime = (meta or {}).get("mime") or "application/octet-stream"
    return bd.ablegen_frei(daten, name, ort["folder_id"], mime=mime)


def _drive_existiert(ort, name):
    from apps.dashboard import ablage_drive as bd
    return bd.datei_vorhanden(ort["folder_id"], name)


def _akte_ablegen(ort, daten, name, meta=None):
    """In die Dokumentenakte schreiben.

    Die Kerndaten (Nummer, ausgestellt von, Ablaufdatum) hat die Einordnung
    ohnehin schon gelesen und reicht sie in `meta` durch - damit funktioniert
    die Ablauf-Ampel sofort, ohne dass jemand nachtippt.
    """
    import base64
    from apps.dashboard import dokumente
    meta = meta or {}
    body = {
        "titel": (meta.get("titel") or Path(name).stem)[:200],
        "kategorie": ort["kategorie"],
        "nummer": meta.get("nummer") or "",
        "aussteller": meta.get("aussteller") or "",
        "ausstelldatum": meta.get("ausstelldatum") or "",
        "ablaufdatum": meta.get("ablaufdatum") or "",
        "notizen": meta.get("notiz") or "",
        "datei": base64.b64encode(daten).decode("ascii"),
        "datei_name": name,
    }
    res = dokumente.speichern(body)
    if isinstance(res, dict) and res.get("error"):
        return False, str(res["error"])
    return True, f"Dokumentenakte / {ort['kategorie']}"


def _akte_existiert(ort, name):
    """Gleicher Titel in derselben Kategorie gilt als vorhanden."""
    try:
        from apps.dashboard import dokumente
        stamm = Path(name).stem.lower()
        for d in (dokumente.overview() or {}).get("dokumente", []):
            if (d.get("kategorie") == ort["kategorie"]
                    and str(d.get("titel", "")).lower() == stamm):
                return True
    except Exception:
        pass
    return False


def _lokal_ablegen(ort, daten, name, meta=None):
    """In einen ORDNER AUF DER PLATTE legen (auch Netzlaufwerk oder Samba).

    Der Weg fuer Kunden ohne Google Drive. Absichtlich das einfachste denkbare
    Ziel - er zeigt, wie schmal der Adapter-Vertrag ist: drei Funktionen, keine
    Anmeldung, keine Fremdbibliothek.
    """
    import os
    ziel = Path(ort["pfad"])
    if not ziel.is_dir():
        return False, f"Ordner gibt es nicht: {ziel}"
    datei = ziel / name
    if datei.exists():
        return True, f"schon vorhanden: {name}"
    tmp = datei.with_name(datei.name + ".tmp")
    tmp.write_bytes(daten)
    os.replace(tmp, datei)        # atomar: nie eine halbe Datei im Zielordner
    return True, str(datei)


def _lokal_existiert(ort, name):
    return (Path(ort["pfad"]) / name).exists()


# gruppe -> (ablegen, existiert).
# EIN NEUES ZIEL (S3, WebDAV, Nextcloud, DMS) wird HIER eingetragen und steht
# damit sofort zur Verfuegung - Eingang, Leser, Agent und Oberflaeche bleiben
# unangetastet. Das ist der ganze Umbau.
ZIELE = {
    "drive": (_drive_ablegen, _drive_existiert),
    "auffang": (_drive_ablegen, _drive_existiert),
    "akte": (_akte_ablegen, _akte_existiert),
    "lokal": (_lokal_ablegen, _lokal_existiert),
    "auffang_lokal": (_lokal_ablegen, _lokal_existiert),
}


def ablegen(ort, daten, name, meta=None):
    """(ok, info). Wirft nie - ein kaputtes Ziel meldet sich als Fehler."""
    if not ort:
        return False, "kein Ziel"
    fn = ZIELE.get(ort.get("gruppe"))
    if not fn:
        return False, f"unbekannte Zielart: {ort.get('gruppe')}"
    try:
        return fn[0](ort, daten, name, meta)
    except Exception as exc:
        return False, f"{type(exc).__name__}: {exc}"


def existiert(ort, name):
    fn = ZIELE.get((ort or {}).get("gruppe"))
    if not fn:
        return False
    try:
        return bool(fn[1](ort, name))
    except Exception:
        return False
