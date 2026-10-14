#!/usr/bin/env python3
"""Selbsttest der automatischen Ablage. OHNE Netz, OHNE Modell, OHNE Drive.

Prueft genau die Stellen, an denen ein Fehler still falsche Wirkung haette:
die Ziel-Sperre (erfindet die KI einen Ordner?), die Namensregel (wird ein
guter Name zerstoert?), den Buchhaltungs-Ausschluss (legt die Ablage eine
Rechnung doppelt ab?) und die Vollstaendigkeit (faellt eine Datei durchs
Raster?).

Aufruf: .venv/bin/python scripts/test_ablage.py
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from apps.dashboard import ablage, ablage_eingang, ablage_struktur, ablage_ziele # noqa: E402

FEHLER = []


def pruef(name, bedingung, extra=""):
    if bedingung:
        print(f" OK {name}")
    else:
        print(f" FAIL {name} {extra}")
        FEHLER.append(name)


# Kuenstliche Orte-Liste: der Test fasst NIE den echten Drive an.
ORTE = [
    {"id": "drive:AAA", "gruppe": "drive", "label": "Ordner A / 02 Unterordner", "zweck": ""},
    {"id": "drive:BBB", "gruppe": "drive", "label": "Ordner A / 03 Unterordner", "zweck": ""},
    {"id": "akte:Reisepass", "gruppe": "akte", "label": "Dokumentenakte / Reisepass",
     "kategorie": "Reisepass", "zweck": ""},
    {"id": "auffang", "gruppe": "auffang", "label": "Auffang", "folder_id": "XYZ", "zweck": ""},
]


def eintrag(eid, name):
    return {"id": eid, "orig_name": name, "erkannt": {"text": "x", "meta": {}}}


def aktion(eid, ziel, name="", besch="weil"):
    return {"art": "datei_ablegen", "beschreibung": besch,
            "args": {"eingang_id": eid, "ziel_id": ziel, "dateiname": name}}


print("\n=== Namensregel: was nichts aussagt, wird umbenannt ===")
for n in ("scan_0012.pdf", "IMG_4837.jpg", "dokument(3).pdf", "IMG-20260831-WA0003.jpg",
          "20260831121500.pdf", "Scan 2026-08-31 (1).pdf", "download.pdf",
          "WhatsApp Image 2026-08-31.jpeg", "a.pdf", ""):
    pruef(f"nichtssagend: {n!r}", ablage.name_sagt_nichts(n))

print("\n=== Namensregel: was etwas aussagt, bleibt ===")
for n in ("Gesellschafterbeschluss die Firma 2026-03.pdf", "Mietvertrag Musterstadt.docx",
          "Police CC001612.pdf", "Wasser.pdf", "AVV-Rees.pdf", "Lohnabrechnung 07-2026.pdf"):
    pruef(f"sagt etwas: {n!r}", not ablage.name_sagt_nichts(n))

print("\n=== Dateiname saeubern ===")
pruef("Umlaute weg, Endung vom Original",
      ablage.sauberer_dateiname("2026-03-12 Beschluss Erhöhung", "scan.pdf")
      == "2026-03-12-Beschluss-Erhohung.pdf")
pruef("fremde Endung wird nicht uebernommen",
      ablage.sauberer_dateiname("rechnung.exe", "scan.pdf").endswith(".pdf"))
pruef("leerer Vorschlag faellt auf Original zurueck",
      ablage.sauberer_dateiname("", "scan_0012.pdf") == "scan_0012.pdf")
pruef("Pfad im Vorschlag fuehrt nicht heraus",
      "/" not in ablage.sauberer_dateiname("../../etc/passwd", "a.pdf"))

print("\n=== Ziel-Sperre: die KI kann keinen Ordner erfinden ===")
e = [eintrag("e1", "scan_0012.pdf")]
a = ablage.pruefe_aktionen([aktion("e1", "drive:ERFUNDEN")], e, ORTE)
pruef("erfundenes Ziel landet im Auffang", a[0]["args"]["ziel_id"] == "auffang")
pruef("und sagt WARUM", "gibt es nicht" in a[0]["args"]["beschreibung"])

a = ablage.pruefe_aktionen([aktion("e1", "")], e, ORTE)
pruef("leeres Ziel landet im Auffang", a[0]["args"]["ziel_id"] == "auffang")

a = ablage.pruefe_aktionen([aktion("e1", "drive:AAA")], e, ORTE)
pruef("gueltiges Ziel bleibt", a[0]["args"]["ziel_id"] == "drive:AAA")

a = ablage.pruefe_aktionen([aktion("e1", ablage_ziele.BUCHHALTUNG)], e, ORTE)
pruef("buchhaltung ist gueltige Kennung",
      a[0]["args"]["ziel_id"] == ablage_ziele.BUCHHALTUNG)

print("\n=== Vollstaendigkeit: keine Datei faellt durchs Raster ===")
e2 = [eintrag("e1", "a.pdf"), eintrag("e2", "b.pdf"), eintrag("e3", "c.pdf")]
a = ablage.pruefe_aktionen([aktion("e1", "drive:AAA")], e2, ORTE)
pruef("vergessene Dateien bekommen den Auffang", len(a) == 3, f"(waren {len(a)})")
pruef("und sind als vergessen markiert",
      any("nicht erfasst" in x["args"]["beschreibung"] for x in a))

a = ablage.pruefe_aktionen(
    [aktion("e1", "drive:AAA"), aktion("e1", "drive:BBB")], e2, ORTE)
e1_mal = [x for x in a if x["args"]["eingang_id"] == "e1"]
pruef("dieselbe Datei nur EINMAL im Buendel", len(e1_mal) == 1)

a = ablage.pruefe_aktionen([aktion("gibtsnicht", "drive:AAA")], e, ORTE)
pruef("erfundene eingang_id wird verworfen",
      all(x["args"]["eingang_id"] == "e1" for x in a))

print("\n=== Umbenennen nur, wenn der alte Name nichts sagt ===")
a = ablage.pruefe_aktionen(
    [aktion("e1", "drive:AAA", "2026-03-12-beschluss")], [eintrag("e1", "scan_0012.pdf")], ORTE)
pruef("nichtssagender Name wird ersetzt", a[0]["args"]["dateiname"].startswith("2026-03-12"))

a = ablage.pruefe_aktionen(
    [aktion("e1", "drive:AAA", "irgendwas-neues")],
    [eintrag("e1", "Gesellschafterbeschluss die Firma 2026-03.pdf")], ORTE)
pruef("guter Name wird NICHT ueberschrieben", a[0]["args"]["dateiname"] == "")

print("\n=== Fremde Aktionen bleiben unangetastet ===")
a = ablage.pruefe_aktionen(
    [{"art": "_variante", "args": {"label": "A"}}, aktion("e1", "drive:AAA")], e, ORTE)
pruef("_variante wird durchgereicht", any(x["art"] == "_variante" for x in a))

print("\n=== Buchhaltung wird NICHT von der Ablage abgelegt ===")
quelle = Path(ablage.__file__).read_text(encoding="utf-8")
pruef("datei_ablegen hat den Buchhaltungs-Ausstieg",
      "BUCHHALTUNG" in quelle and "nicht abgelegt" in quelle)
pruef("Buchhaltung ist kein Ablage-Ziel",
      ablage_ziele.BUCHHALTUNG not in ablage_ziele.ZIELE)

print("\n=== Eingangsfach ===")
pruef("Traversal im Namen wird gesaeubert",
      "/" not in ablage_eingang.sicherer_name("../../etc/passwd"))
ok, grund = ablage_eingang.annehmen("film.mp4", b"xx")
pruef("unbekannter Typ wird mit Grund abgelehnt", not ok and "mp4" in grund)
ok, grund = ablage_eingang.annehmen("gross.pdf", b"x" * (ablage_eingang.MAX_BYTES + 1))
pruef("zu grosse Datei wird mit Grund abgelehnt", not ok and "gross" in grund.lower())
ok, grund = ablage_eingang.annehmen("leer.pdf", b"")
pruef("leere Datei wird abgelehnt", not ok)

ok, eid = ablage_eingang.annehmen("t_probe.pdf", b"%PDF-1.4 selbsttest", "test")
pruef("gueltige Datei wird angenommen", ok)
if ok:
    ok2, grund2 = ablage_eingang.annehmen("anderer_name.pdf", b"%PDF-1.4 selbsttest")
    pruef("gleicher INHALT ist eine Dublette", not ok2 and "Eingang" in grund2)
    pruef("Idempotenz: abgelegte Datei wird nicht erneut abgelegt",
          (ablage_eingang.setze_status(eid, "abgelegt") or True)
          and ablage.datei_ablegen(eid, "drive:AAA")[1] == "war schon abgelegt")
    ablage_eingang.entfernen(eid)

print("\n=== Ziel-Adapter ===")
pruef("unbekannte Zielart meldet sich",
      ablage_ziele.ablegen({"gruppe": "quatsch"}, b"x", "a.pdf")[0] is False)
pruef("kein Ziel meldet sich", ablage_ziele.ablegen(None, b"x", "a.pdf")[0] is False)

print("\n=== Struktur ===")
pruef("gueltig() sperrt Erfundenes", not ablage_struktur.gueltig("drive:ERFUNDEN", ORTE))
pruef("gueltig() laesst Echtes durch", ablage_struktur.gueltig("drive:AAA", ORTE))
pruef("Ordner OHNE Zwecksatz ist trotzdem waehlbar",
      ablage_struktur.gueltig("drive:BBB", ORTE))
pruef("Orte-Prompt nennt jeden Ort",
      all(o["id"] in ablage_struktur.als_prompt(ORTE) for o in ORTE))

quelle_s = Path(ablage_struktur.__file__).read_text(encoding="utf-8")
pruef("Auffang wird nie selbst angelegt", "auffang_folder_id" in quelle_s)
quelle_a = Path(ablage.__file__).read_text(encoding="utf-8")
pruef("Einordnung scannt FRISCH (kein Cache fuers Urteil)",
      "frisch=True" in Path(ROOT / "apps/dashboard/agents/ablage_agent.py").read_text(encoding="utf-8"))

print()
if FEHLER:
    print(f"FEHLGESCHLAGEN: {len(FEHLER)}")
    for f in FEHLER:
        print(" -", f)
    sys.exit(1)
print("Alle Prüfungen bestanden.")
