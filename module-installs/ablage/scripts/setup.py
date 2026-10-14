#!/usr/bin/env python3
"""Einrichtungs-Interview der automatischen Ablage.

Fragt nacheinander die drei Dinge ab, die bei jedem Setup anders sind, und
schreibt daraus den `ablage`-Block in config/dashboard.json:

    1. WO soll abgelegt werden?   Google Drive, ein Ordner auf der Platte, oder beides
    2. WELCHE Orte sind erlaubt?  (und welche ausdruecklich nicht)
    3. WO ist der Auffang?        fuer alles, was sich nicht sicher zuordnen laesst

Zwei Grundsaetze, die das Interview durchhaelt:

- ES WIRD NIE ETWAS ANGELEGT, ohne zu fragen. Auch der Auffangordner nicht.
  Ein Ablagesystem, das beim Einrichten ungefragt Ordner erzeugt, ist genau
  der Wildwuchs, den es verhindern soll.
- ES WIRD NIE GERATEN. Was das Skript nicht sicher weiss (welcher Drive, welcher
  Pfad), fragt es. Was es sehen kann (welche Drives der Zugang ueberhaupt
  hergibt), zeigt es zur Auswahl, statt es abzutippen zu lassen.

Aufruf:  python3 scripts/setup.py            (fragt und schreibt)
         python3 scripts/setup.py --zeigen   (nur anzeigen, nichts schreiben)
"""
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]      # …/CEO-GPT
CONFIG = ROOT / "config" / "dashboard.json"


def frage(text, standard=None):
    zusatz = f" [{standard}]" if standard else ""
    try:
        a = input(f"{text}{zusatz}: ").strip()
    except EOFError:
        a = ""
    return a or (standard or "")


def ja(text, standard=True):
    s = "J/n" if standard else "j/N"
    a = frage(f"{text} ({s})").lower()
    if not a:
        return standard
    return a.startswith("j") or a.startswith("y")


def waehle(titel, optionen):
    """Mehrfachauswahl aus einer Liste. Gibt die gewaehlten Werte zurueck."""
    print(f"\n{titel}")
    for i, o in enumerate(optionen, 1):
        print(f"  {i}) {o}")
    a = frage("Nummern (Komma getrennt, leer = keine)")
    gewaehlt = []
    for teil in a.replace(" ", "").split(","):
        if teil.isdigit() and 1 <= int(teil) <= len(optionen):
            gewaehlt.append(optionen[int(teil) - 1])
    return gewaehlt


def drives_lesen():
    """Welche Shared Drives gibt der Zugang her? Leer, wenn kein Drive da ist."""
    try:
        sys.path.insert(0, str(ROOT))
        from apps.dashboard.agents import beleg_drive as bd
        d = bd._drive()
        return [x["name"] for x in d.drives().list(
            pageSize=100, fields="drives(id,name)").execute().get("drives", [])]
    except Exception as exc:
        print(f"  (Google Drive nicht lesbar: {type(exc).__name__})")
        return []


def auffang_im_drive_anlegen(name):
    """Legt den Auffangordner im persoenlichen Drive an. NUR nach Rueckfrage."""
    sys.path.insert(0, str(ROOT))
    from apps.dashboard.agents import beleg_drive as bd
    d = bd._drive()
    q = (f"'root' in parents and name = '{name}' "
         "and mimeType='application/vnd.google-apps.folder' and trashed=false")
    da = d.files().list(q=q, fields="files(id,name)").execute().get("files", [])
    if da:
        return da[0]["id"]
    return d.files().create(
        body={"name": name, "mimeType": "application/vnd.google-apps.folder"},
        fields="id").execute()["id"]


def main():
    nur_zeigen = "--zeigen" in sys.argv
    print("=" * 62)
    print("  Automatische Ablage einrichten")
    print("=" * 62)
    print("\nDrei Fragen: wohin abgelegt wird, welche Orte erlaubt sind,")
    print("und wo alles landet, was sich nicht sicher zuordnen laesst.\n")

    block = {"_hinweis": ("Automatische Ablage. Die KI WAEHLT aus den Orten, die sich aus "
                          "dieser Konfiguration ergeben - sie erfindet keinen Pfad. Was sie "
                          "nicht sicher zuordnen kann, landet im Auffang."),
             "max_je_stapel": 15}

    # --- 1. Wohin ---------------------------------------------------------
    print("--- 1. Wohin soll abgelegt werden? ---")
    print("  1) Google Drive")
    print("  2) Ein Ordner auf der Platte (auch Netzlaufwerk oder Samba)")
    print("  3) Beides")
    wohin = frage("Auswahl", "1")
    drive_an = wohin in ("1", "3")
    lokal_an = wohin in ("2", "3")

    # --- 2. Welche Orte ---------------------------------------------------
    if drive_an:
        print("\n--- 2a. Welche Google-Drive-Bereiche darf die Ablage benutzen? ---")
        verfuegbar = drives_lesen()
        if verfuegbar:
            block["drives"] = waehle("Gefundene Bereiche:", verfuegbar)
        else:
            roh = frage("Keine gefunden. Namen von Hand (Komma getrennt)")
            block["drives"] = [x.strip() for x in roh.split(",") if x.strip()]
        print(f"  -> {len(block.get('drives') or [])} Bereich(e) gewaehlt")

    if lokal_an:
        print("\n--- 2b. Welcher Ordner auf der Platte? ---")
        basis = frage("Vollstaendiger Pfad")
        tiefe = frage("Wie viele Ebenen tief scannen?", "2")
        block["lokal"] = {"basis": basis, "tiefe": int(tiefe or 2)}
        if basis and not Path(basis).expanduser().is_dir():
            print(f"  ACHTUNG: {basis} gibt es (noch) nicht. Die Ablage ueberspringt")
            print("  dieses Ziel dann still, bis der Ordner existiert.")

    # --- 2c. Was ist gesperrt --------------------------------------------
    print("\n--- 2c. Gibt es Ordner, in die NIE abgelegt werden darf? ---")
    print("  Typischer Fall: ein Ordner, den Kunden oder Externe einsehen koennen.")
    print("  Muster erlaubt, z. B.  Projekte/01 Kunden/*/Freigegeben")
    roh = frage("Pfade (Komma getrennt, leer = keine)")
    block["gesperrte_pfade"] = [x.strip() for x in roh.split(",") if x.strip()]

    # --- 3. Auffang -------------------------------------------------------
    print("\n--- 3. Wo landet, was sich nicht sicher zuordnen laesst? ---")
    print("  Dieser Ordner ist wichtig: dank ihm muss die Ablage NIE raten.")
    if lokal_an and not drive_an:
        pfad = frage("Pfad des Auffangordners")
        block["auffang_pfad"] = pfad
        if pfad and not Path(pfad).expanduser().is_dir():
            if ja(f"  {pfad} gibt es nicht. Jetzt anlegen?"):
                Path(pfad).expanduser().mkdir(parents=True, exist_ok=True)
                print("  angelegt.")
    else:
        vorhandene = frage("Ordner-ID im Drive (leer = neuen anlegen lassen)")
        if vorhandene:
            block["auffang_folder_id"] = vorhandene
        elif not nur_zeigen and ja("  Einen Auffangordner im persoenlichen Drive anlegen?"):
            name = frage("  Wie soll er heissen?", "00 Eingang (Ablage)")
            try:
                block["auffang_folder_id"] = auffang_im_drive_anlegen(name)
                print(f"  angelegt: {block['auffang_folder_id']}")
            except Exception as exc:
                print(f"  ging nicht ({exc}). Bitte spaeter von Hand eintragen.")
        else:
            print("  Ohne Auffang meldet der Tab das und ordnet vorsichtiger ein.")

    # --- Ergebnis ---------------------------------------------------------
    print("\n" + "=" * 62)
    print(json.dumps({"ablage": block}, ensure_ascii=False, indent=2))
    print("=" * 62)
    if nur_zeigen:
        print("\n--zeigen: nichts geschrieben.")
        return 0
    if not ja("\nSo in config/dashboard.json uebernehmen?"):
        print("Abgebrochen, nichts geaendert.")
        return 1

    cfg = json.loads(CONFIG.read_text(encoding="utf-8")) if CONFIG.exists() else {}
    cfg["ablage"] = block
    cfg.setdefault("modules", {})["ablage"] = True
    cfg.setdefault("demo", {}).setdefault("surfaces", {})["ablage"] = "hide"
    tmp = CONFIG.with_suffix(".tmp")
    tmp.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, CONFIG)
    print(f"\nGeschrieben: {CONFIG}")
    print("Danach einmal den Dashboard-Dienst neu starten (Knopf im System-Tab).")
    print("\nTipp fuer den ersten Lauf: lass dir im Tab die Zwecksaetze vorschlagen")
    print("('N Ordner ohne Zweck beschreiben lassen'). Ein Satz je Ordner ist der")
    print("Hebel fuer Treffsicherheit - nicht der Prompt.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
