"""Automatische Ablage: der Kern.

DIE EINE EINORDNUNG. Agent, Cockpit und Chat rufen dieselben Funktionen -
deshalb kann es nie zwei Urteile ueber dieselbe Datei geben. Wer das aufteilt,
bekommt frueher oderspaeter zwei Wege, die verschieden entscheiden, und merkt
es erst, wenn dasselbe Dokument beim zweiten Mal woanders landet.

Aufbau (drei austauschbare Teile plus dieser Kern):
    ablage_eingang Datei rein, quellen-neutral
    ablage_leser Text + Metadaten raus, reine Mechanik
    ablage_struktur wohin DARF es (die Orte-Liste)
    ablage_ziele wie wird tatsaechlich geschrieben
    ablage <- hier: das Urteil und die Ausfuehrung

VIER REGELN IM PROMPT, alles andere ist Urteil (Vorgabe: moeglichst
viel ueber KI, moeglichst wenig statisch gecodet):
    1. Waehle GENAU EINE ziel_id aus der Liste. Unsicher heisst Auffang.
    2. Rechnung/Kaufbeleg -> ziel_id "buchhaltung", NICHT selbst ablegen.
    3. Umbenennen nur, wenn der Name nichts aussagt. Name aus dem INHALT.
    4. Ein Satz je Datei, warum dieses Ziel.

Was NICHT im Prompt steht, sondern im Code (weil eine Bitte vergessen werden
kann, eine Pruefung nicht):
    - gueltige ziel_id (ablage_struktur.gueltig) -> sonst Auffang
    - Dateiname gesaeubert und gekuerzt
    - Buchhaltungs-Dateien werden hier nie abgelegt
    - Idempotenz: Zielordner pruefen UND Eingangs-Status
"""
import json
import os
import re
import sqlite3
import unicodedata
from contextlib import closing
from datetime import datetime
from pathlib import Path

from apps.dashboard import ablage_eingang, ablage_leser, ablage_struktur, ablage_ziele

ROOT = Path(__file__).resolve().parents[2]
DB_PATH = ROOT / "data" / "data.db"

MAX_JE_STAPEL = 15
MAX_NAME = 120


# --- Verlauf (Grundlage der belege-Quelle) ---------------------------------

def _conn():
    conn = sqlite3.connect(str(DB_PATH), timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout=30000")
    conn.execute(
        "CREATE TABLE IF NOT EXISTS ablage_verlauf ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, "
        "eingang_id TEXT, ziel_id TEXT, ziel_label TEXT, "
        "dateiname TEXT, orig_name TEXT, zusammenfassung TEXT, "
        "info TEXT, wann TEXT)")
    conn.execute("CREATE INDEX IF NOT EXISTS ix_ablage_verlauf_wann "
                 "ON ablage_verlauf(wann)")
    conn.commit()
    return conn


def _verlauf_schreiben(eingang, ziel, name, zusammenfassung, info):
    with closing(_conn()) as conn:
        conn.execute(
            "INSERT INTO ablage_verlauf (eingang_id, ziel_id, ziel_label, dateiname, "
            "orig_name, zusammenfassung, info, wann) VALUES (?,?,?,?,?,?,?,?)",
            (eingang.get("id"), ziel.get("id"), ziel.get("label"), name,
             eingang.get("orig_name"), (zusammenfassung or "")[:1500], str(info)[:300],
             datetime.now().isoformat(timespec="seconds")))
        conn.commit()


# --- Dateiname --------------------------------------------------------------

# Woerter, die ueber den Inhalt nichts sagen. BEWUSST token-basiert und nicht
# als ein grosses Muster: ein Muster wie "^img.*\\d+$" verfehlt WhatsApp-Namen
# (IMG-20260831-WA0003), und "wa" als Teilstring wuerde "Wasser" mitnehmen.
_RAUSCHEN = {
    "scan", "scans", "img", "image", "foto", "photo", "pic", "picture",
    "dok", "doc", "docx", "document", "dokument", "datei", "file", "bild",
    "unbenannt", "untitled", "neu", "new", "download", "downloads",
    "attachment", "anhang", "pdf", "whatsapp", "wa", "screenshot",
    "kopie", "copy", "final", "version", "v", "seite", "page", "export",
}


def name_sagt_nichts(name):
    """Sagt der Dateiname, was drin ist?

    Nur wenn NEIN wird umbenannt. `scan_0012.pdf` ja, aber
    `Gesellschafterbeschluss die Firma 2026-03.pdf` bleibt, wie es ist: da hat
    sich jemand etwas gedacht, und wer danach sucht, sucht nach dem Namen, den
    er kennt.

    Gemessen wird, was nach Abzug von Ziffern und Rauschwoertern uebrig bleibt.
    Ein reines Muster reichte nicht: `IMG-20260831-WA0003.jpg` (WhatsApp) kam
    damit als aussagekraeftig durch, weil nach den Ziffern noch Zeichen standen.
    """
    stamm = Path(str(name or "")).stem.strip()
    if not stamm:
        return True
    rest = []
    for token in re.split(r"[\s_\-.()\[\]]+", stamm):
        wort = re.sub(r"\d+", "", token).strip().lower()
        if not wort or wort in _RAUSCHEN:
            continue
        rest.append(wort)
    # Weniger als vier echte Buchstaben uebrig heisst: der Name traegt nichts.
    return sum(len(w) for w in rest) < 4


def sauberer_dateiname(vorschlag, orig_name):
    """Vorschlag saeubern. Endung kommt IMMER vom Original.

    Der Name kommt aus dem INHALT, nie aus etwas, das zufaellig danebensteht.
    Genau daran lief die Beleg-Automatik am 24.08.2026 auf: der letzte Pfadteil
    einer Stripe-Rechnungsadresse war schlicht `pdf`, die Datei hiess `pdf.pdf`,
    und die naechste verlinkte Rechnung eines voellig anderen Anbieters waere
    als "schon vorhanden" verworfen worden.
    """
    endung = Path(str(orig_name or "")).suffix.lower()
    roh = Path(str(vorschlag or "")).stem.strip()
    if not roh:
        return ablage_eingang.sicherer_name(orig_name)
    roh = unicodedata.normalize("NFKD", roh)
    roh = "".join(c for c in roh if not unicodedata.combining(c))
    for a, b in (("ä", "ae"), ("ö", "oe"), ("ü", "ue"), ("ß", "ss")):
        roh = roh.replace(a, b).replace(a.upper(), b)
    roh = re.sub(r"[^A-Za-z0-9._-]+", "-", roh).strip("-._")
    roh = re.sub(r"-{2,}", "-", roh) or Path(ablage_eingang.sicherer_name(orig_name)).stem
    return (roh[:MAX_NAME] + endung)


# --- Prompt-Bausteine -------------------------------------------------------

def system_regeln(orte=None):
    """Der fachliche Kern des System-Prompts. Der Agent haengt Prime-Brief und
    Gelerntes davor, die geteilten Regeln haengt research_actions selbst an."""
    orte = orte if orte is not None else ablage_struktur.orte()
    return (
        "\n\n=== SO ORDNEST DU EIN ===\n"
        "Du bekommst Dateien mit ihrem ausgelesenen Inhalt. Für JEDE rufst du "
        "genau einmal `datei_ablegen` auf.\n\n"
        "1. ZIEL: Wähle GENAU EINE ziel_id aus der Liste unten. Erfinde keinen "
        "Pfad und keinen Ordner - was nicht in der Liste steht, gibt es nicht. "
        "Bist du dir nicht sicher, nimm `auffang`. Das ist eine vollwertige "
        "Antwort und besser als ein Ordner, der fast passt.\n"
        "2. RECHNUNGEN: Ist es eine Rechnung, ein Kaufbeleg oder eine Quittung, "
        "setz ziel_id `buchhaltung`. Du legst sie NICHT selbst ab, dafür gibt es "
        "einen eigenen Weg. Ein Vertrag oder ein Angebot ist KEINE Rechnung.\n"
        "3. NAME: Sagt der Dateiname schon, was drin ist, lass ihn wie er ist "
        "(dateiname leer lassen). Nur wenn er nichts aussagt (scan_0012, IMG_4837, "
        "dokument(3)), schlag einen neuen vor: `JJJJ-MM-TT-was-es-ist`, kleingeschrieben, "
        "Bindestriche, keine Umlaute. Das Datum kommt aus dem INHALT des Dokuments "
        "(Ausstellungsdatum), nicht von heute. Findest du keins, lass es weg.\n"
        "4. BEGRÜNDUNG: In `beschreibung` EIN Satz, warum dieses Ziel. Konkret "
        "('Vertrag der die Firma, gehört zu den Firmenverträgen'), nicht allgemein.\n\n"
        "Schreib zum Schluss 1-2 Sätze über den Stapel als Ganzes. Zähl die "
        "Dateien NICHT einzeln auf, das steht schon auf der Karte.\n\n"
        "=== GÜLTIGE ABLAGEORTE (nur aus dieser Liste wählen) ===\n"
        + ablage_struktur.als_prompt(orte)
        + f"\n- {ablage_ziele.BUCHHALTUNG} = Rechnung/Beleg, läuft über den Buchhaltungs-Weg\n"
    )


def task(eintraege):
    """Der Auftrag: die gelesenen Dateien."""
    teile = [f"{len(eintraege)} Datei(en) liegen im Eingang. Ordne jede ein.\n"]
    for i, e in enumerate(eintraege, 1):
        erk = e.get("erkannt") or {}
        meta = erk.get("meta") or {}
        teile.append(f"\n--- Datei {i} ---")
        teile.append(f"eingang_id: {e['id']}")
        teile.append(f"Dateiname: {e.get('orig_name')}")
        infos = [f"{k}={v}" for k, v in meta.items()
                 if k in ("seiten", "title", "author", "created", "geaendert", "groesse_kb")]
        if infos:
            teile.append("Metadaten: " + ", ".join(str(x) for x in infos))
        if erk.get("fehler"):
            teile.append(f"HINWEIS: Inhalt nicht lesbar ({erk['fehler']}). "
                         "Ordne nach Dateiname ein, im Zweifel Auffang.")
        text = (erk.get("text") or "").strip()
        teile.append("Inhalt:\n" + (text[:6000] if text else "(kein Text erkannt)"))
    return "\n".join(teile)


# --- Lesen ------------------------------------------------------------------

def lesen(eingang_ids=None):
    """Offene Eingaenge auslesen (nur was noch nicht gelesen ist)."""
    if eingang_ids:
        eintraege = [ablage_eingang.holen(i) for i in eingang_ids]
        eintraege = [e for e in eintraege if e]
    else:
        eintraege = ablage_eingang.liste(("neu", "gelesen", "fehler"))
    out = []
    for e in eintraege[:MAX_JE_STAPEL]:
        if not e.get("erkannt"):
            erk = ablage_leser.lies(e["pfad"], e.get("orig_name"))
            ablage_eingang.setze_status(e["id"], "gelesen", erkannt=erk,
                                        fehler=erk.get("fehler"))
            e["erkannt"] = erk
        out.append(e)
    return out


# --- Validierung ------------------------------------------------------------

def pruefe_aktionen(actions, eintraege, orte=None):
    """DIE deterministische Sperre nach dem Modell-Lauf.

    Jede Aktion wird gegen die echte Orte-Liste gehalten. Ungueltiges landet im
    Auffang mit Vermerk, statt still zu verschwinden oder irgendwo zu landen.
    Fehlt eine Datei ganz im Bündel, bekommt sie ebenfalls den Auffang - keine
    Datei darf durch das Raster fallen.
    """
    orte = orte if orte is not None else ablage_struktur.orte(frisch=False)
    auffang = ablage_struktur.auffang(orte)
    per_id = {e["id"]: e for e in eintraege}
    gesehen, geprueft = set(), []

    for a in actions:
        if a.get("art") != "datei_ablegen":
            geprueft.append(a) # z. B. _variante, unveraendert durch
            continue
        args = a.setdefault("args", {})
        eid = str(args.get("eingang_id") or "").strip()
        if eid not in per_id or eid in gesehen:
            continue # erfundene oder doppelte ID: weg
        gesehen.add(eid)
        e = per_id[eid]

        ziel_id = str(args.get("ziel_id") or "").strip()
        vermerk = ""
        if ziel_id == ablage_ziele.BUCHHALTUNG:
            pass # gueltige Kennung, kein Ablageort
        elif not ablage_struktur.gueltig(ziel_id, orte):
            vermerk = (f"Ziel „{ziel_id}\" gibt es nicht, deshalb Auffang."
                       if ziel_id else "Kein Ziel genannt, deshalb Auffang.")
            ziel_id = ablage_struktur.AUFFANG_ID if auffang else ""
        args["ziel_id"] = ziel_id

        vorschlag = str(args.get("dateiname") or "").strip()
        if vorschlag and name_sagt_nichts(e.get("orig_name")):
            args["dateiname"] = sauberer_dateiname(vorschlag, e.get("orig_name"))
        else:
            # Sagt der alte Name etwas, bleibt er - auch wenn das Modell einen
            # neuen vorschlaegt. Die Entscheidung "umbenennen ja/nein" trifft
            # der Code, nur der NEUE NAME kommt vom Modell.
            args["dateiname"] = ""
        # Die Begruendung des Modells steht in args["beschreibung"] (dem
        # Werkzeug-Parameter). a["beschreibung"] traegt zu diesem Zeitpunkt nur
        # das technische Label aus _record ("Datei ablegen: eing-…") - wer das
        # zuerst nimmt, zeigt der Geschäftsführer im Tab eine ID statt eines Satzes.
        args["beschreibung"] = (str(args.get("beschreibung") or "").strip()
                                + (f" [{vermerk}]" if vermerk else ""))[:400]
        if ziel_id == ablage_ziele.BUCHHALTUNG:
            # Rechnungen legt der Buchhaltungs-Weg ab; ein Namensvorschlag von
            # hier waere wirkungslos und auf der Karte nur irrefuehrend.
            args["dateiname"] = ""
            ort = {"label": "Buchhaltung (eigener Weg)"}
        else:
            ort = ablage_struktur.ort(ziel_id, orte)
        a["beschreibung"] = (f"{e.get('orig_name')} → {(ort or {}).get('label', '?')}"
                             + (f" (als {args['dateiname']})" if args["dateiname"] else ""))
        geprueft.append(a)

    # Vergessene Dateien: nie stillschweigend liegen lassen.
    for eid, e in per_id.items():
        if eid in gesehen or not auffang:
            continue
        geprueft.append({
            "art": "datei_ablegen",
            "beschreibung": f"{e.get('orig_name')} → {auffang['label']}",
            "args": {"eingang_id": eid, "ziel_id": ablage_struktur.AUFFANG_ID,
                     "dateiname": "",
                     "beschreibung": "Vom Einordnen nicht erfasst, deshalb Auffang."}})
    return geprueft


# --- Ausfuehren -------------------------------------------------------------

def datei_ablegen(eingang_id, ziel_id, dateiname=None, beschreibung=None):
    """Eine Datei wirklich ablegen. (ok, info). Wird vom Executor gerufen."""
    e = ablage_eingang.holen(eingang_id)
    if not e:
        return False, f"Eingang {eingang_id} nicht gefunden"
    if e.get("status") == "abgelegt":
        return True, "war schon abgelegt" # Idempotenz, Ebene 1

    if ziel_id == ablage_ziele.BUCHHALTUNG:
        # Rechnungen laufen ueber beleg_automatik. Hier wird NICHT abgelegt,
        # sondern die Datei bleibt sichtbar liegen - zwei Automatiken, die
        # dieselbe Rechnung ablegen, waeren der klassische Doppel-Fehler.
        ablage_eingang.setze_status(eingang_id, "vorgeschlagen",
                                    fehler="Rechnung: gehört in die Buchhaltung "
                                           "(eigener Weg), hier nicht abgelegt")
        return True, "als Rechnung erkannt, bleibt für den Buchhaltungs-Weg liegen"

    orte = ablage_struktur.orte(frisch=False)
    ort = ablage_struktur.ort(ziel_id, orte)
    if not ort:
        ort = ablage_struktur.auffang(orte)
        if not ort:
            return False, f"Ziel {ziel_id} unbekannt und kein Auffang eingerichtet"

    daten = ablage_eingang.daten(eingang_id)
    if not daten:
        ablage_eingang.setze_status(eingang_id, "fehler", fehler="Datei im Eingang fehlt")
        return False, "Datei im Eingang fehlt"

    name = (dateiname or "").strip() or e.get("orig_name")
    meta = {"mime": e.get("mime")}
    erk = e.get("erkannt") or {}
    if ort.get("gruppe") == "akte":
        meta.update({"titel": Path(name).stem, "notiz": (erk.get("text") or "")[:400]})

    ok, info = ablage_ziele.ablegen(ort, daten, name, meta)
    if not ok:
        ablage_eingang.setze_status(eingang_id, "fehler", fehler=info)
        return False, info

    _verlauf_schreiben(e, ort, name, (erk.get("text") or "")[:1500], info)
    ablage_eingang.setze_status(eingang_id, "abgelegt")
    ablage_eingang.aufraeumen(eingang_id) # Original erst JETZT weg
    return True, f"{name} → {ort['label']}"


# --- Suche (Quelle fuer belege.py) -----------------------------------------

def verlauf_suche(begriffe, limit=20):
    """Abgelegte Dokumente finden. `begriffe` ist eine Liste von Woertern."""
    if not begriffe:
        return []
    with closing(_conn()) as conn:
        rows = conn.execute(
            "SELECT ziel_label, dateiname, orig_name, zusammenfassung, wann "
            "FROM ablage_verlauf ORDER BY wann DESC LIMIT 400").fetchall()
    out = []
    for r in rows:
        heu = " ".join(str(r[k] or "") for k in
                       ("dateiname", "orig_name", "zusammenfassung", "ziel_label")).lower()
        if any(b in heu for b in begriffe):
            out.append(dict(r))
        if len(out) >= limit:
            break
    return out


# --- Ordner-Vorschlaege aus Belegen ----------------------------------------

def ordner_vorschlaege(min_treffer=4, min_tage=7):
    """Neue Ordner entstehen aus BELEGEN, nicht aus Ideen.

    Sammeln sich gleichartige Dokumente im Auffang, entsteht ein Vorschlag mit
    den Dokumenten als Begruendung. Dasselbe Muster wie agent_lernen.verdichten()
    (Regel erst ab drei Faellen). Die KI legt NIE selbst einen Ordner an.
    """
    import sys
    from datetime import timedelta
    grenze = (datetime.now() - timedelta(days=min_tage)).isoformat(timespec="seconds")
    with closing(_conn()) as conn:
        rows = conn.execute(
            "SELECT dateiname, orig_name, zusammenfassung, wann FROM ablage_verlauf "
            "WHERE ziel_id = ? AND wann <= ? ORDER BY wann DESC LIMIT 60",
            (ablage_struktur.AUFFANG_ID, grenze)).fetchall()
    if len(rows) < min_treffer:
        return []

    zeilen = [f"{i+1}. {r['dateiname']}: {(r['zusammenfassung'] or '')[:200]}"
              for i, r in enumerate(rows)]
    sys.path.insert(0, str(ROOT / "scripts"))
    try:
        from claude_llm import complete
        roh = complete(
            "Diese Dokumente liegen unsortiert im Auffang. Finde Gruppen von "
            f"MINDESTENS {min_treffer} Dokumenten, die inhaltlich zusammengehören und "
            "einen eigenen Ordner verdienen. Gibt es keine solche Gruppe, antworte "
            "nur mit KEINE.\nFormat je Gruppe eine Zeile: "
            "`Ordnername | Nummern der Dokumente (Komma) | ein Satz Begründung`\n\n"
            + "\n".join(zeilen), agent="ablage_ordner") or ""
    except Exception:
        return []

    out = []
    for zeile in roh.splitlines():
        if zeile.strip().upper().startswith("KEINE") or zeile.count("|") < 2:
            continue
        name, nummern, grund = [t.strip() for t in zeile.split("|", 2)]
        idx = [int(n) - 1 for n in re.findall(r"\d+", nummern)]
        belege = [dict(rows[i]) for i in idx if 0 <= i < len(rows)]
        if name and len(belege) >= min_treffer:
            out.append({"name": name[:80], "grund": grund[:300], "belege": belege})
    return out


# --- HTTP -------------------------------------------------------------------

def _demo_aktiv():
    try:
        from apps.dashboard import demo
        return bool(demo.is_active())
    except Exception:
        return False


def uebersicht(query=None):
    """Alles, was der Tab braucht. Liest NUR lokal (Anzeige-Cache), damit ein
    Blick in den Tab nie einen Drive-Scan ausloest.

    GET-Routen liefern (status, obj) - handle_get entpackt genau zwei Werte.
    """
    if _demo_aktiv():
        return 403, {"error": "Im Demo-Modus nicht verfügbar"}
    orte = ablage_struktur.orte(frisch=False)
    eintraege = ablage_eingang.offene()
    from apps.dashboard import agent_proposals
    karten = [p for p in agent_proposals.raw_proposals()
              if p.get("agent") == "ablage" and p.get("status") == "entwurf"]
    karte = karten[0] if karten else None
    return 200, {
        "eingang": [{k: e.get(k) for k in
                     ("id", "orig_name", "groesse", "mime", "status", "erstellt", "fehler")}
                    | {"vorschlag": e.get("vorschlag")} for e in eintraege],
        "orte": [{k: o.get(k) for k in ("id", "label", "gruppe", "zweck")} for o in orte],
        "ohne_zweck": len(ablage_struktur.ohne_zweck(orte)),
        # Der VOLLE Payload geht mit: Korrekturen laufen ueber den bestehenden
        # Freigabe-Weg (/api/agents/proposal/decide ersetzt den payload), nicht
        # ueber einen eigenen Endpunkt. Ein zweiter Schreibweg neben decide waere
        # eine zweite Stelle, an der Freigaben vorbeilaufen koennen.
        "vorschlag_id": (karte or {}).get("id"),
        "vorschlag_payload": (karte or {}).get("payload"),
        "auffang_da": bool(ablage_struktur.auffang(orte)),
    }


def upload_http(body):
    if _demo_aktiv():
        return 403, {"error": "Im Demo-Modus nicht verfügbar"}
    import base64
    dateien = (body or {}).get("dateien") or []
    ok, fehler = [], []
    for d in dateien[:MAX_JE_STAPEL]:
        try:
            roh = base64.b64decode(str(d.get("daten") or ""), validate=False)
        except Exception:
            fehler.append(f"{d.get('name')}: nicht lesbar")
            continue
        gut, info = ablage_eingang.annehmen(d.get("name"), roh, quelle="cockpit")
        (ok if gut else fehler).append(info if gut else f"{d.get('name')}: {info}")
    return 200, {"angenommen": len(ok), "ids": ok, "fehler": fehler}


def einordnen_http(body=None):
    """Stösst den Agenten an. Antwortet SOFORT, der Lauf geht im Hintergrund -
    ein LLM-Lauf dauert zehn bis dreissig Sekunden, und ein Request, der
    darauf wartet, sieht am Handy aus wie ein Absturz (Lehre vom Paseo-Import)."""
    if _demo_aktiv():
        return 403, {"error": "Im Demo-Modus nicht verfügbar"}
    import threading
    if not ablage_eingang.liste(("neu", "gelesen", "vorgeschlagen", "fehler")):
        return 200, {"status": "leer"}

    def _lauf():
        try:
            from apps.dashboard import agent_runner
            agent_runner.run_now("ablage")
        except Exception as exc:
            print(f"[ablage] Einordnen gescheitert: {exc}", flush=True)

    threading.Thread(target=_lauf, daemon=True, name="ablage-einordnen").start()
    return 202, {"status": "laeuft"}


def verwerfen_http(body):
    if _demo_aktiv():
        return 403, {"error": "Im Demo-Modus nicht verfügbar"}
    eid = (body or {}).get("id")
    if not eid:
        return 400, {"error": "keine id"}
    ablage_eingang.entfernen(eid)
    return 200, {"ok": True}


def zwecke_http(body):
    """Zwecksätze lesen, vorschlagen lassen oder setzen."""
    if _demo_aktiv():
        return 403, {"error": "Im Demo-Modus nicht verfügbar"}
    body = body or {}
    if body.get("aktion") == "vorschlagen":
        return 200, {"vorschlaege": ablage_struktur.zwecke_vorschlagen(body.get("ids"))}
    for oid, satz in (body.get("zwecke") or {}).items():
        ablage_struktur.zweck_setzen(oid, satz)
    ablage_struktur.cache_leeren()
    return 200, {"ok": True, "zwecke": ablage_struktur.zwecke()}


def orte_http(query=None):
    """Frische Orte-Liste (Aktualisieren-Knopf im Tab)."""
    if _demo_aktiv():
        return 403, {"error": "Im Demo-Modus nicht verfügbar"}
    orte = ablage_struktur.orte(frisch=True)
    return 200, {"orte": [{k: o.get(k) for k in ("id", "label", "gruppe", "zweck")} for o in orte],
            "ohne_zweck": len(ablage_struktur.ohne_zweck(orte))}


def ordner_http(body):
    if _demo_aktiv():
        return 403, {"error": "Im Demo-Modus nicht verfügbar"}
    body = body or {}
    if body.get("aktion") == "anlegen":
        from apps.dashboard import ablage_drive as bd
        ziel = ablage_struktur.ort(body.get("parent_id") or "")
        if not ziel or ziel.get("gruppe") not in ("drive", "auffang"):
            return 400, {"error": "kein gültiger Elternordner"}
        fid = bd.ordner_anlegen(ziel["folder_id"], str(body.get("name") or "")[:80])
        ablage_struktur.cache_leeren()
        return 200, {"ok": True, "folder_id": fid}
    return 200, {"vorschlaege": ordner_vorschlaege()}


def register(GET, POST):
    GET["/api/ablage"] = uebersicht
    GET["/api/ablage/orte"] = orte_http
    POST["/api/ablage/upload"] = upload_http
    POST["/api/ablage/einordnen"] = einordnen_http
    POST["/api/ablage/verwerfen"] = verwerfen_http
    POST["/api/ablage/zwecke"] = zwecke_http
    POST["/api/ablage/ordner"] = ordner_http
