"""Wo darf etwas hin? Die Liste der gueltigen Ablageorte.

DAS HERZSTUECK GEGEN ERFUNDENE ORDNER: die Einordnung bekommt eine flache,
nummerierte Liste aller gueltigen Orte und gibt eine `ziel_id` zurueck, KEINEN
Pfad. Was nicht in dieser Liste steht, ist ungueltig - geprueft in `gueltig()`,
also im Code und nicht als Bitte im Prompt. Damit kann die KI strukturell
keinen Ordner erfinden.

FRISCHE (Vorgabe 31.08.2026: „wenn ich morgen einen neuen Ordner
erstelle, ist er auch schon da?"): vor JEDER Einordnung wird frisch gescannt.
Ein Scan kostet ein bis zwei Sekunden, der LLM-Aufruf danach zehn bis dreissig.
Ein Cache an dieser Stelle spart nichts und macht das System um einen Tag dumm.
Der Cache in data/ablage/struktur.json ist NUR fuer die Anzeige (das Dropdown
im Tab soll sofort aufgehen) und darf nie die Grundlage eines Urteils sein.

ZWECKSAETZE sind der EINZIGE kundenspezifische Teil des ganzen Systems
(data/ablage/zwecke.json). Aber: ein Ordner OHNE Zwecksatz ist trotzdem ein
gueltiges Ziel - der Ordnername geht immer mit in den Prompt und erklaert sich
meistens selbst. Ohne diese Regel waere jeder frisch angelegte Ordner
unerreichbar, bis ihn jemand beschreibt, und das fiele niemandem auf.
"""
import json
import os
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data" / "ablage"
ZWECKE_PATH = DATA / "zwecke.json"
CACHE_PATH = DATA / "struktur.json"
CACHE_SEK = 30 * 60 # NUR fuer die Anzeige

AUFFANG_ID = "auffang"


def _cfg():
    try:
        with open(ROOT / "config" / "dashboard.json", encoding="utf-8") as f:
            return json.load(f).get("ablage") or {}
    except Exception:
        return {}


def drives():
    return list(_cfg().get("drives") or [])


def auffang_folder_id():
    return (_cfg().get("auffang_folder_id") or "").strip()


def gesperrte_pfade():
    """Pfade, in die NIE abgelegt werden darf. Wichtigster Fall:
    Projekte/01 Kunden/<Kunde>/Aufnahmen - dort ist der KUNDE eingeladen
    (reference/drive-struktur.md). Ein internes Papier dort waere ein Leck."""
    return [p.lower() for p in (_cfg().get("gesperrte_pfade") or [])]


def _gesperrt(drive, pfad):
    voll = f"{drive}/{pfad}".lower()
    for muster in gesperrte_pfade():
        if muster.endswith("/*"):
            if voll.startswith(muster[:-2]):
                return True
        elif "*" in muster:
            teile = [t for t in muster.split("*") if t]
            if all(t in voll for t in teile):
                return True
        elif voll.startswith(muster):
            return True
    return False


# --- Zwecksaetze ------------------------------------------------------------

def zwecke():
    try:
        return json.loads(ZWECKE_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


def zweck_setzen(ort_id, satz):
    d = zwecke()
    satz = (satz or "").strip()
    if satz:
        d[ort_id] = satz[:300]
    else:
        d.pop(ort_id, None)
    DATA.mkdir(parents=True, exist_ok=True)
    tmp = ZWECKE_PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
    os.replace(tmp, ZWECKE_PATH)
    return True


# --- Orte -------------------------------------------------------------------

def _drive_orte():
    from apps.dashboard import ablage_drive as bd
    out = []
    for e in bd.strukturscan(drives()):
        if _gesperrt(e["drive"], e["pfad"]):
            continue
        out.append({"id": f"drive:{e['folder_id']}", "gruppe": "drive",
                    "label": f"{e['drive']} / {e['pfad']}",
                    "folder_id": e["folder_id"], "drive": e["drive"], "pfad": e["pfad"]})
    return out


def _lokal_orte():
    """Ordner auf der Platte als Ablageorte (Kunden ohne Google Drive).

    Konfiguriert ueber config/dashboard.json -> ablage.lokal:
        {"basis": "/pfad/zur/ablage", "tiefe": 2}
    Gescannt wird bis `tiefe` Ebenen, genau wie beim Drive. Fehlt der Block
    oder gibt es den Ordner nicht, liefert die Funktion eine leere Liste -
    dann laeuft das Modul einfach ohne dieses Ziel.
    """
    cfg = (_cfg().get("lokal") or {})
    basis = str(cfg.get("basis") or "").strip()
    if not basis:
        return []
    wurzel = Path(basis).expanduser()
    if not wurzel.is_dir():
        return []
    tiefe = int(cfg.get("tiefe") or 2)
    out = []

    def _lauf(ordner, ebene, praefix):
        if ebene > tiefe:
            return
        try:
            kinder = sorted([k for k in ordner.iterdir() if k.is_dir()],
                            key=lambda x: x.name)
        except Exception:
            return
        for k in kinder:
            if k.name.startswith("."):
                continue
            pfad = f"{praefix}/{k.name}" if praefix else k.name
            out.append({"id": f"lokal:{k}", "gruppe": "lokal",
                        "label": f"{wurzel.name} / {pfad}",
                        "pfad": str(k), "ebene": ebene})
            _lauf(k, ebene + 1, pfad)

    _lauf(wurzel, 1, "")
    return out


def _akte_orte():
    """Die Dokumentenakte als zweites Ziel: eine Kategorie ist ein Ort."""
    try:
        from apps.dashboard import dokumente
        cfg = dokumente._config()
        kats = dokumente._kategorien(cfg)
    except Exception:
        return []
    return [{"id": f"akte:{k}", "gruppe": "akte",
             "label": f"Dokumentenakte / {k}", "kategorie": k} for k in kats]


def _auffang_ort():
    """Der EINE Auffangordner. Entweder im Drive oder auf der Platte.

    Er wird NIE automatisch angelegt: ein Auffang, den das System sich selbst
    erfindet, ist genau der Wildwuchs, den dieses Modul verhindern soll. Fehlt
    er, sagt das der Tab, statt still irgendwohin abzulegen.
    """
    lokal = str((_cfg().get("auffang_pfad") or "")).strip()
    if lokal:
        p = Path(lokal).expanduser()
        if p.is_dir():
            return {"id": AUFFANG_ID, "gruppe": "auffang_lokal", "pfad": str(p),
                    "label": f"Auffang ({p.name}, noch nicht einsortiert)"}
        return None
    fid = auffang_folder_id()
    if not fid:
        return None
    return {"id": AUFFANG_ID, "gruppe": "auffang", "folder_id": fid,
            "label": "Auffang (noch nicht einsortiert)"}


def _cache_lesen():
    try:
        roh = json.loads(CACHE_PATH.read_text(encoding="utf-8"))
        return roh.get("orte") or [], roh.get("ts", 0)
    except Exception:
        return [], 0


_frischt = False


def _im_hintergrund_frischen():
    """Cache nachziehen, ohne den Aufrufer warten zu lassen. Single-Flight."""
    global _frischt
    if _frischt:
        return
    _frischt = True

    def _lauf():
        global _frischt
        try:
            orte(frisch=True)
        except Exception as exc:
            print(f"[ablage_struktur] Hintergrund-Scan fehlgeschlagen: {exc}", flush=True)
        finally:
            _frischt = False

    import threading
    threading.Thread(target=_lauf, daemon=True, name="ablage-struktur").start()


def orte(frisch=True):
    """Alle gueltigen Ablageorte.

    `frisch=True` scannt den Drive (fuer das URTEIL, siehe Modul-Kopf).
    `frisch=False` liefert IMMER sofort aus dem Cache, auch wenn er alt ist,
                   und zieht im Hintergrund nach. Ein Blick in den Tab darf nie
                   auf einen Drive-Scan warten - der Endpunkt haengt sonst
                   Sekunden, und am Handy sieht das aus wie ein Absturz.
    """
    if not frisch:
        gecacht, ts = _cache_lesen()
        if gecacht:
            if time.time() - ts >= CACHE_SEK:
                _im_hintergrund_frischen()
            return gecacht
        # Gar kein Cache (allererster Aufruf): einmal scannen muessen wir.

    liste = []
    for fn in (_drive_orte, _lokal_orte, _akte_orte):
        try:
            liste.extend(fn())
        except Exception as exc: # eine kaputte Quelle darf nicht alles reissen
            print(f"[ablage_struktur] {fn.__name__} fehlgeschlagen: {exc}", flush=True)
    auf = _auffang_ort()
    if auf:
        liste.append(auf)

    z = zwecke()
    for o in liste:
        o["zweck"] = z.get(o["id"], "")

    if liste:
        DATA.mkdir(parents=True, exist_ok=True)
        tmp = CACHE_PATH.with_suffix(".tmp")
        tmp.write_text(json.dumps({"ts": time.time(), "orte": liste},
                                  ensure_ascii=False, indent=1), encoding="utf-8")
        os.replace(tmp, CACHE_PATH)
    return liste


def cache_leeren():
    try:
        CACHE_PATH.unlink()
    except Exception:
        pass


def ort(ort_id, alle=None):
    for o in (alle if alle is not None else orte(frisch=False)):
        if o["id"] == ort_id:
            return o
    return None


def gueltig(ort_id, alle=None):
    """DIE deterministische Sperre. Was nicht in der Liste steht, ist ungueltig."""
    return ort(ort_id, alle) is not None


def auffang(alle=None):
    return ort(AUFFANG_ID, alle)


def ohne_zweck(alle=None):
    """Orte ohne Zwecksatz. Sie sind waehlbar (der Name traegt oft schon den
    Zweck), aber schaerfer getroffen wird mit Satz. Der Tab zeigt sie an, damit
    man sich nicht wundert, warum ein neuer Ordner nie gewaehlt wird."""
    return [o for o in (alle if alle is not None else orte(frisch=False))
            if o["gruppe"] == "drive" and not o.get("zweck")]


def als_prompt(alle=None):
    """Die Orte-Liste fuer das Modell. Der LABEL steht immer da, auch ohne
    Zwecksatz - der Ordnername ist der Zweck-Ersatz."""
    zeilen = []
    for o in (alle if alle is not None else orte()):
        z = f" ({o['zweck']})" if o.get("zweck") else ""
        zeilen.append(f"- {o['id']} = {o['label']}{z}")
    return "\n".join(zeilen)


def zwecke_vorschlagen(nur_ids=None):
    """EIN LLM-Aufruf: Zwecksatz je Ordner aus Name, Pfad und den ersten
    Dateinamen darin. Rueckgabe {ort_id: satz}, wird NICHT gespeichert -
    der Geschäftsführer bestaetigt im Tab."""
    import sys
    alle = orte()
    offen = [o for o in ohne_zweck(alle)
             if not nur_ids or o["id"] in set(nur_ids)]
    if not offen:
        return {}
    from apps.dashboard import ablage_drive as bd
    zeilen = []
    for o in offen[:40]:
        bsp = bd.beispiel_dateien(o["folder_id"])
        zeilen.append(f"{o['id']} | {o['label']} | Dateien darin: "
                      + (", ".join(bsp[:6]) if bsp else "(leer)"))
    sys.path.insert(0, str(ROOT / "scripts"))
    from claude_llm import complete
    prompt = (
        "Für jeden Ordner EIN kurzer Satz, was dort hineingehört. Nüchtern und "
        "konkret, damit eine Einordnung danach entscheiden kann. Kein Marketing.\n"
        "Antworte als Zeilen im Format `ort_id | Satz`, sonst nichts.\n\n"
        + "\n".join(zeilen))
    try:
        roh = complete(prompt, agent="ablage_zwecke") or ""
    except Exception:
        return {}
    out = {}
    gueltige = {o["id"] for o in offen}
    for zeile in roh.splitlines():
        if "|" not in zeile:
            continue
        oid, _, satz = zeile.partition("|")
        oid, satz = oid.strip().lstrip("- "), satz.strip()
        if oid in gueltige and satz: # nie einen Satz fuer einen erfundenen Ort
            out[oid] = satz[:300]
    return out
