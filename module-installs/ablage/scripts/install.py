#!/usr/bin/env python3
"""Installiert die automatische Ablage in ein bestehendes Cockpit-Modul.

Kopiert den Code aus payload/ und haengt ihn an sieben Stellen ein. Jeder
Patch ist IDEMPOTENT (zweimal laufen aendert nichts) und prueft vorher, ob die
Stelle ueberhaupt so aussieht wie erwartet - passt ein Anker nicht, wird die
Datei NICHT angefasst und der Fall am Ende gemeldet. Lieber ein Handgriff mehr
als eine halb gepatchte Datei.

Aufruf:  python3 scripts/install.py          (installieren)
         python3 scripts/install.py --check  (nur pruefen, nichts aendern)
"""
import shutil
import sys
from pathlib import Path

MODUL = Path(__file__).resolve().parent.parent
PAYLOAD = MODUL / "payload"
ROOT = Path.cwd()

DASH = "apps/dashboard"
KOPIEN = [
    (f"{DASH}/ablage.py",) * 2,
    (f"{DASH}/ablage_drive.py",) * 2,
    (f"{DASH}/ablage_eingang.py",) * 2,
    (f"{DASH}/ablage_leser.py",) * 2,
    (f"{DASH}/ablage_struktur.py",) * 2,
    (f"{DASH}/ablage_ziele.py",) * 2,
    (f"{DASH}/agents/ablage_agent.py",) * 2,
    (f"{DASH}/static/views/ablage.js",) * 2,
    ("scripts/test_ablage.py",) * 2,
]

# (Datei, Erkennung "schon drin", Anker, was eingefuegt wird, davor/danach)
PATCHES = [
    (f"{DASH}/api.py", "from apps.dashboard import ablage as _ablage",
     "    for mod in modules:",
     '''    try:
        from apps.dashboard import ablage as _ablage
        modules.append(_ablage)
    except Exception as exc:  # pragma: no cover
        print(f"[dashboard] Modul 'ablage' nicht geladen: {exc}", flush=True)

''', "davor"),

    (f"{DASH}/static/app.js", "import './views/ablage.js';",
     "import './views/system.js';",
     "import './views/ablage.js';\n", "davor"),

    (f"{DASH}/agent_runner.py", 'reg["ablage"]',
     "        _registry_cache = reg",
     '''        try:
            from apps.dashboard.agents.ablage_agent import Agent as Ablage
            reg["ablage"] = Ablage()
        except Exception as exc:
            print(f"[agent_runner] ablage nicht geladen: {exc}", flush=True)
''', "davor"),

    (f"{DASH}/belege.py", '("ablage", _ablage)',
     "QUELLEN = [",
     '''def _ablage(stichwort, seit):
    """Liegt das Dokument schon abgelegt in der Ablage?

    Der Rueckweg zur automatischen Ablage: was der Ablage-Agent einsortiert hat,
    muss jeder Agent wiederfinden - sonst legt einer eine Aufgabe "Vertrag
    ablegen" an, waehrend der Vertrag laengst abgelegt ist. Weil die Quelle HIER
    eingetragen ist, gilt das sofort fuer jeden Agenten, ohne dass ein einziger
    Prompt sich aendert. `seit` gilt bewusst NICHT: ein vor Monaten abgelegtes
    Dokument ist genauso ein Beleg wie eines von heute.
    """
    treffer, begriffe = [], _begriffe(stichwort)
    if not begriffe:
        return treffer
    try:
        from apps.dashboard import ablage
        for r in ablage.verlauf_suche(begriffe, limit=LOKAL):
            treffer.append({
                "wann": r.get("wann"), "kanal": "Ablage",
                "text": (f"abgelegt als \\u201e{r.get('dateiname')}\\" in {r.get('ziel_label')}"
                         + (f" - {(r.get('zusammenfassung') or '')[:120]}"
                            if r.get("zusammenfassung") else "")),
                "wer": ""})
    except Exception:
        pass
    return treffer


''', "davor"),
]


def kopiere(check):
    fehlt, kopiert = [], 0
    for quelle, ziel in KOPIEN:
        q, z = PAYLOAD / quelle, ROOT / ziel
        if not q.exists():
            fehlt.append(quelle); continue
        if not z.parent.exists():
            fehlt.append(f"{ziel} (Zielordner fehlt - ist das ein Cockpit-Setup?)"); continue
        if not check:
            shutil.copy2(q, z)
        kopiert += 1
    return kopiert, fehlt


def patche(check):
    getan, offen = [], []
    for datei, marke, anker, einfuegung, wo in PATCHES:
        p = ROOT / datei
        if not p.exists():
            offen.append(f"{datei}: gibt es nicht"); continue
        t = p.read_text(encoding="utf-8")
        if marke in t:
            getan.append(f"{datei}: war schon drin"); continue
        if anker not in t:
            offen.append(f"{datei}: Anker nicht gefunden ({anker[:40]!r}) - bitte von Hand")
            continue
        neu = (einfuegung + anker) if wo == "davor" else (anker + einfuegung)
        if not check:
            p.write_text(t.replace(anker, neu, 1), encoding="utf-8")
        getan.append(f"{datei}: eingehaengt")
    return getan, offen


def passkey_patch(check):
    """Der Tab zeigt Inhalte fremder Dokumente im Klartext - er gehoert hinter
    dasselbe Schloss wie die uebrigen privaten Endpunkte. Gibt es kein Schloss
    im Setup, ist das kein Fehler, nur ein Hinweis."""
    p = ROOT / DASH / "passkey.py"
    if not p.exists():
        return "kein Passkey-Schloss im Setup (uebersprungen)"
    t = p.read_text(encoding="utf-8")
    if "/api/ablage" in t:
        return "Schloss: war schon drin"
    import re
    m = re.search(r"GESCHUETZT = \(([^)]*)\)", t)
    if not m:
        return "Schloss: GESCHUETZT nicht gefunden - bitte '/api/ablage' von Hand ergaenzen"
    if not check:
        neu = f'GESCHUETZT = ({m.group(1).rstrip().rstrip(",")}, "/api/ablage")'
        p.write_text(t.replace(m.group(0), neu, 1), encoding="utf-8")
    return "Schloss: /api/ablage ergaenzt"


def aktions_patch(check):
    """Aktions-Werkzeug + Executor. Ohne beides entsteht zwar ein Vorschlag,
    aber die Freigabe fuehrt nichts aus."""
    meldungen = []
    at = ROOT / DASH / "agents" / "actions_tools.py"
    if at.exists():
        t = at.read_text(encoding="utf-8")
        if "datei_ablegen" in t:
            meldungen.append("Aktion: war schon drin")
        elif "ACTION_TOOLS = [variante," in t:
            werkzeug = '''@tool("datei_ablegen",
      "Eine Datei aus dem Eingangsfach an ihren Platz legen. ziel_id MUSS aus der "
      "vorgelegten Orte-Liste stammen - erfinde keinen Pfad und keinen Ordner; bist du "
      "unsicher, nimm 'auffang'. Ist es eine Rechnung oder ein Kaufbeleg, nimm "
      "'buchhaltung' (die legt ein eigener Weg ab, nicht du). dateiname NUR setzen, wenn "
      "der bisherige Name nichts aussagt (scan_0012, IMG_4837) - sonst leer lassen. "
      "Vorgemerkt zur Freigabe.",
      {"eingang_id": str, "ziel_id": str, "dateiname": str, "beschreibung": str})
async def datei_ablegen(args):
    return _record("datei_ablegen", f"Datei ablegen: {args.get('eingang_id','')}", **args)


ACTION_TOOLS = [variante, datei_ablegen,'''
            if not check:
                at.write_text(t.replace("ACTION_TOOLS = [variante,", werkzeug, 1), encoding="utf-8")
            meldungen.append("Aktion: datei_ablegen ergaenzt")
        else:
            meldungen.append("Aktion: Anker nicht gefunden - bitte von Hand")

    ac = ROOT / DASH / "agent_actions.py"
    if ac.exists():
        t = ac.read_text(encoding="utf-8")
        if "_datei_ablegen" in t:
            meldungen.append("Executor: war schon drin")
        elif '        if art == "aufgabe_anlegen":' in t:
            zweig = '''        if art == "datei_ablegen":
            return _datei_ablegen(args)
        if art == "aufgabe_anlegen":'''
            fn = '''def _datei_ablegen(args):
    """Eine Datei aus dem Eingangsfach ablegen (automatische Ablage).

    Die ziel_id wird HIER NOCHMAL geprueft, obwohl das beim Komponieren schon
    geschah: der Executor ist die letzte Instanz vor der echten Wirkung, und
    zwischen Komponieren und Freigeben koennen Stunden liegen (ein Ordner kann
    in der Zeit geloescht worden sein).
    """
    from apps.dashboard import ablage
    eid = str(args.get("eingang_id") or "").strip()
    if not eid:
        return False, "keine eingang_id"
    return ablage.datei_ablegen(
        eid, str(args.get("ziel_id") or "").strip(),
        args.get("dateiname"), args.get("beschreibung"))


'''
            if not check:
                t = t.replace('        if art == "aufgabe_anlegen":', zweig, 1)
                # Funktion vor die erste Hilfsfunktion setzen
                import re
                m = re.search(r"^def _[a-z]", t, re.M)
                t = t[:m.start()] + fn + t[m.start():] if m else t + "\n\n" + fn
                ac.write_text(t, encoding="utf-8")
            meldungen.append("Executor: _datei_ablegen ergaenzt")
        else:
            meldungen.append("Executor: Anker nicht gefunden - bitte von Hand")
    return meldungen


def main():
    check = "--check" in sys.argv
    print("=" * 62)
    print("  Automatische Ablage " + ("pruefen" if check else "installieren"))
    print("=" * 62)
    if not (ROOT / DASH / "api.py").exists():
        print(f"\nFEHLER: {ROOT} sieht nicht nach einem Cockpit-Setup aus")
        print("(apps/dashboard/api.py fehlt). Bitte im Hauptordner ausfuehren.")
        return 2

    n, fehlt = kopiere(check)
    print(f"\nDateien: {n} {'gefunden' if check else 'kopiert'}")
    for f in fehlt:
        print(f"  FEHLT  {f}")

    print("\nEinhaengen:")
    getan, offen = patche(check)
    for g in getan:
        print(f"  OK     {g}")
    print(f"  OK     {passkey_patch(check)}")
    for m in aktions_patch(check):
        print(f"  OK     {m}")
    for o in offen:
        print(f"  OFFEN  {o}")

    print("\n" + "-" * 62)
    if fehlt or offen:
        print("Nicht alles ging automatisch. Die OFFEN-Zeilen bitte von Hand.")
    elif check:
        print("Alles vorhanden.")
    else:
        print("Fertig. Naechster Schritt:")
        print("  1) python3 scripts/setup.py     (Interview: wohin soll abgelegt werden)")
        print("  2) Dashboard-Dienst neu starten (Knopf im System-Tab)")
        print("  3) python3 scripts/test_ablage.py")
    return 1 if (fehlt or offen) else 0


if __name__ == "__main__":
    sys.exit(main())
