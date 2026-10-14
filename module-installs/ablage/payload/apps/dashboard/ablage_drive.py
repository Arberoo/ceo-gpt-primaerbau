"""Google Drive als Ablageziel: lesen, Ordner finden, Datei hochladen.

EIGENE DATEI, damit das Modul den Beleg-/Buchhaltungs-Weg des Setups NICHT
anfassen muss. Ein Patch an fremdem Code waere die schlechtere Wahl: er kann
misslingen, er muss bei jedem Update nachgezogen werden, und er macht aus zwei
Zustaendigkeiten eine.

Die Anmeldung wird geteilt, nicht nachgebaut: wenn das Setup schon einen
Drive-Zugang hat (`beleg_drive._drive()`), wird der benutzt. Sonst zieht diese
Datei den Token selbst aus `data/google-recordings-token.json` bzw. dem in
config/dashboard.json unter `ablage.drive_token` genannten Pfad.

ACHTUNG MY DRIVE: Suchaufrufe gegen einen Shared Drive brauchen `corpora` plus
`driveId`, gegen My Drive duerfen BEIDE nicht gesetzt sein. Ein Shared-Drive-
Aufruf gegen My Drive liefert stillschweigend eine LEERE LISTE - ein Ordner
saehe damit aus, als gaebe es ihn nicht, und nirgends erschiene ein Fehler.
Gekapselt in `_list_args()`.
"""
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCOPES = ["https://www.googleapis.com/auth/drive"]


def _token_pfad():
    try:
        with open(ROOT / "config" / "dashboard.json", encoding="utf-8") as f:
            eigen = (json.load(f).get("ablage") or {}).get("drive_token")
        if eigen:
            return ROOT / eigen
    except Exception:
        pass
    return ROOT / "data" / "google-recordings-token.json"


def _atomic_write(path, text):
    path = Path(path)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(text)
    os.replace(tmp, path)


def _drive():
    """Der Drive-Dienst. Nutzt den Zugang des Setups, wenn es einen gibt."""
    try:
        from apps.dashboard.agents import beleg_drive
        return beleg_drive._drive()
    except Exception:
        pass
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
    tok = _token_pfad()
    if not tok.exists() or tok.stat().st_size == 0:
        raise RuntimeError(f"Drive-Zugang fehlt ({tok.name}) - Drive-Ablage nicht moeglich")
    creds = Credentials.from_authorized_user_file(str(tok), SCOPES)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        _atomic_write(tok, creds.to_json())
    return build("drive", "v3", credentials=creds, cache_discovery=False)


def _list_args(drive_id):
    """Such-Parameter je nach Ort: Shared Drive oder My Drive."""
    if drive_id:
        return {"corpora": "drive", "driveId": drive_id,
                "supportsAllDrives": True, "includeItemsFromAllDrives": True}
    return {}                            # My Drive: nichts davon, sonst leer


def unterordner(drive, parent_id, drive_id=None, limit=200):
    """Direkte Unterordner von parent_id. Nie anlegen, nur lesen."""
    q = (f"'{parent_id}' in parents and mimeType = 'application/vnd.google-apps.folder' "
         "and trashed = false")
    return drive.files().list(
        q=q, fields="files(id,name)", pageSize=limit,
        **_list_args(drive_id)).execute().get("files", [])


def strukturscan(drive_namen, tiefe=2):
    """Ordner-Baum der genannten Shared Drives bis `tiefe` Ebenen.

    Rueckgabe: [{"folder_id", "drive", "pfad", "ebene"}]. Nur LESEN - hier wird
    nie ein Ordner angelegt. Genau das ist der Grund, warum die Einordnung
    keinen Pfad erfinden kann: sie waehlt aus dieser Liste.
    """
    drive = _drive()
    vorhanden = {d["name"]: d["id"] for d in drive.drives().list(
        pageSize=100, fields="drives(id,name)").execute().get("drives", [])}
    out = []
    for name in drive_namen:
        did = vorhanden.get(name)
        if not did:
            continue                     # unbekannter Drive: still ueberspringen
        ebene1 = unterordner(drive, did, did)
        for f in sorted(ebene1, key=lambda x: x["name"]):
            out.append({"folder_id": f["id"], "drive": name,
                        "pfad": f["name"], "ebene": 1})
            if tiefe < 2:
                continue
            for s in sorted(unterordner(drive, f["id"], did), key=lambda x: x["name"]):
                out.append({"folder_id": s["id"], "drive": name,
                            "pfad": f"{f['name']}/{s['name']}", "ebene": 2})
    return out


def ordner_info(folder_id):
    """Name und Eltern eines Ordners. None, wenn es ihn nicht (mehr) gibt."""
    try:
        return _drive().files().get(
            fileId=folder_id, fields="id,name,parents,trashed",
            supportsAllDrives=True).execute()
    except Exception:
        return None


def beispiel_dateien(folder_id, drive_id=None, n=6):
    """Die ersten Dateinamen in einem Ordner - Rohstoff fuer den Zwecksatz."""
    q = f"'{folder_id}' in parents and trashed = false"
    try:
        files = _drive().files().list(
            q=q, fields="files(name)", pageSize=n,
            **_list_args(drive_id)).execute().get("files", [])
        return [f["name"] for f in files]
    except Exception:
        return []


def ordner_anlegen(parent_id, name, drive_id=None):
    """Einen Ordner anlegen. NUR nach ausdruecklicher Freigabe aufrufen -
    die Einordnung selbst legt nie Ordner an."""
    meta = {"name": name, "mimeType": "application/vnd.google-apps.folder",
            "parents": [parent_id]}
    return _drive().files().create(
        body=meta, fields="id", supportsAllDrives=True).execute()["id"]


def datei_vorhanden(folder_id, name, drive_id=None):
    safe = name.replace("'", "\\'")
    q = f"'{folder_id}' in parents and name = '{safe}' and trashed = false"
    try:
        files = _drive().files().list(
            q=q, fields="files(id)", **_list_args(drive_id)).execute().get("files", [])
        return bool(files)
    except Exception:
        return False


def ablegen_frei(daten, name, folder_id, mime="application/pdf", drive_id=None):
    """Rohdaten in einen BELIEBIGEN Ordner legen (Shared Drive oder My Drive).

    Idempotent ueber den Dateinamen im Zielordner - zweimal freigeben laedt
    einmal hoch. Rueckgabe (ok, info).
    """
    import io
    from googleapiclient.http import MediaIoBaseUpload
    if not folder_id:
        return False, "kein Zielordner"
    if not daten:
        return False, "keine Daten"
    drive = _drive()
    if datei_vorhanden(folder_id, name, drive_id):
        return True, f"schon vorhanden: {name}"
    media = MediaIoBaseUpload(io.BytesIO(daten), mimetype=mime or "application/octet-stream",
                              resumable=False)
    datei = drive.files().create(
        body={"name": name, "parents": [folder_id]}, media_body=media,
        fields="id,webViewLink", supportsAllDrives=True).execute()
    return True, datei.get("webViewLink") or datei.get("id")
