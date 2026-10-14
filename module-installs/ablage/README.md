# Automatische Ablage

Dateien reinziehen, KI ordnet ein, ein Klick legt ab.

## Was es macht

Du ziehst Dateien in den Cockpit-Tab „Ablage". Ein Agent liest jede vollständig aus (PDF, Word, Excel, Scans, Fotos), erkennt worum es geht, und schlägt für den **ganzen Stapel eine Liste** vor: wohin die Datei gehört und wie sie heißen soll. Ein Klick nimmt alle Vorschläge, einzelne Zeilen korrigierst du per Dropdown.

Danach liegen die Dateien wirklich an ihrem Platz, und jeder Agent im System findet sie wieder.

## Das Problem dahinter

Dokumente einsortieren kostet Zeit und schafft keinen Wert. Teurer ist aber das Zweite: was `scan_0012.pdf` heißt, ist auch im richtigen Ordner verloren.

## Drei Teile, die du bestimmst

| | |
|---|---|
| **Der Eingang** | Woher Dateien kommen. Heute: Drag-und-Drop im Cockpit. |
| **Der Agent** | Läuft von selbst, liest, urteilt, schlägt vor. Führt nie ungefragt aus. |
| **Die Ablage** | Wohin. Google Drive, ein Ordner auf der Platte, ein Netzlaufwerk, oder mehreres nebeneinander. |

Alle drei werden beim Einrichten **im Interview** abgefragt (`scripts/setup.py`).

## Warum die KI hier nichts kaputt machen kann

Das ist der Kern: **die KI wählt aus einer Liste, sie erfindet keinen Pfad.**

Sie bekommt alle gültigen Ablageorte vorgelegt und gibt eine Kennung zurück. Was nicht in der Liste steht, wird im Code verworfen und landet im Auffang. Das ist keine Bitte im Prompt, sondern eine Eigenschaft des Systems.

Dazu vier Dinge, die es **nie** tut:
- einen Ordner anlegen (neue Ordner schlägt es vor, ab vier gleichartigen Dokumenten, mit den vieren als Begründung)
- einen aussagekräftigen Dateinamen überschreiben
- eine Rechnung ablegen (die lässt es liegen, falls ein Buchhaltungs-Weg existiert)
- etwas ausführen, das du nicht freigegeben hast

## Einrichten

```bash
python3 scripts/install.py     # Code einhängen
python3 scripts/setup.py       # Interview: wohin soll abgelegt werden
python3 scripts/test_ablage.py # 49 Prüfungen, ohne Netz
```

Danach den Dashboard-Dienst neu starten. Details in `INSTALL.md`.

## Voraussetzungen

- Das **Cockpit-Modul** (dieses Modul erweitert es)
- Für Google Drive als Ziel: ein Drive-Zugang mit Schreibrecht
- Für die Dokumentenakte als Ziel: das **life**-Modul (optional)

Ohne Drive läuft es vollständig mit einem Ordner auf der Platte.

## Inhaltseingang

Originaldatei direkt beim Upload bzw. abgeschlossenem Dateieingang verfügbar.

Einrichtungsstandard und Grenzen: [reference/dateneingang.md](reference/dateneingang.md).
Dieses Patch-Update korrigiert die Installationsvorgaben; zusätzliche Dienste werden
dadurch nicht automatisch eingerichtet. KI-Schritte sind separat zu aktivieren.
