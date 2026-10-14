# Automatische Ablage einrichten

## Verbindlicher Standard für den Inhaltseingang · 1.0.1

**Vor der Einrichtung [reference/dateneingang.md](reference/dateneingang.md) lesen und anwenden.**
Empfohlen: Originaldatei direkt beim Upload bzw. abgeschlossenem Dateieingang verfügbar.

Diese Vorgabe ergänzt die bisherige Anleitung: automatische Übernahme der ausgewählten
Nachrichten und Termine gehört zur Grundeinrichtung. Frühere optionale Collector-Phasen
beschreiben nur noch zusätzliche Historienkopien; deren Zeitpläne sind kein Echtzeitnachweis.
Die Anleitung zur Quelle nennt nötige Ergänzungen und Grenzen. Keine KI-Schritte allein
für den Empfang einschalten; zusätzliche KI-Kosten vor Aktivierung erklären und Zustimmung
einholen. Bereits passende Zustimmung gilt weiter.

**Versionstyp: Installationsstandard korrigiert.** Kein mit dieser Dokumentversion
automatisch ausgerollter Echtzeitdienst; tatsächlichen Inhaltseingang im Zielsetup abnehmen.


Vier Schritte, rund zehn Minuten. Wenn etwas nicht passt, sagt jeder Schritt das und bricht ab, statt weiterzumachen.

---

## Schritt 1: Voraussetzungen prüfen

Dieses Modul erweitert das **Cockpit-Modul**. Ohne das läuft es nicht.

```bash
ls apps/dashboard/api.py
```

Kommt eine Fehlermeldung, bist du im falschen Ordner oder das Cockpit fehlt.

**Entscheide vorher, wohin abgelegt werden soll.** Das Interview fragt es gleich:

- **Google Drive**: braucht einen Zugang mit Schreibrecht. Liegt im Setup schon einer (z. B. für Aufnahmen oder Belege), wird der mitbenutzt.
- **Ordner auf der Platte**: braucht nur den Pfad. Ein Netzlaufwerk oder eine Samba-Freigabe zählt dazu, solange sie gemountet ist.
- **Beides** geht auch.

---

## Schritt 2: Code einhängen

```bash
python3 scripts/install.py
```

Das kopiert neun Dateien und hängt sie an sieben Stellen ein. Jeder Eingriff ist idempotent: zweimal laufen ändert nichts.

**Passt ein Anker nicht, wird die Datei nicht angefasst** und der Fall am Ende unter `OFFEN` gemeldet. Lieber ein Handgriff mehr als eine halb gepatchte Datei.

Nur nachsehen, ohne zu ändern:

```bash
python3 scripts/install.py --check
```

---

## Schritt 3: Das Interview

```bash
python3 scripts/setup.py
```

Drei Fragen:

1. **Wohin soll abgelegt werden?** Drive, Platte, oder beides.
2. **Welche Bereiche sind erlaubt?** Bei Drive zeigt das Skript, was dein Zugang hergibt, du wählst per Nummer. Dazu: gibt es Ordner, in die **nie** abgelegt werden darf? Typischer Fall ist ein Ordner, den Kunden einsehen können.
3. **Wo ist der Auffang?** Dorthin geht alles, was sich nicht sicher zuordnen lässt. **Dieser Ordner ist wichtig**: dank ihm muss die Ablage nie raten.

Das Skript **legt nie ungefragt etwas an**, auch den Auffang nicht. Es fragt.

Nur ansehen, was herauskäme:

```bash
python3 scripts/setup.py --zeigen
```

---

## Schritt 4: Neu starten und prüfen

Dashboard-Dienst neu starten (Knopf im System-Tab), dann:

```bash
python3 scripts/test_ablage.py
```

49 Prüfungen, ohne Netz und ohne Modell. Alle müssen grün sein.

Danach im Cockpit den Tab **Ablage** öffnen und zwei, drei Dateien reinziehen.

---

## Der erste Lauf: eine Empfehlung

**Lass eine Rechnung mitlaufen.** Sie ist die interessanteste Probe: der Agent muss sie erkennen und **liegen lassen**, falls im Setup ein Buchhaltungs-Weg existiert. Sitzt das, doppelt sich nichts.

**Drück danach auf „N Ordner ohne Zweck beschreiben lassen".** Die Einordnung läuft auch ohne (der Ordnername trägt viel), aber ein Satz je Ordner ist der Hebel für Treffsicherheit. Wo ein Satz danebenliegt, korrigierst du ihn einmal, und ab da trifft es dort dauerhaft besser.

**Das ist die wichtigste Stellschraube.** Liegt die Einordnung daneben, ist der erste Hebel der Zwecksatz, nicht der Prompt. Deshalb liegt er in einer Datei, die du anfassen kannst.

---

## Wenn etwas nicht läuft

| Was du siehst | Was los ist |
|---|---|
| Tab fehlt in der Seitenleiste | `modules.ablage` steht nicht auf `true`, oder der Dienst wurde nicht neu gestartet |
| „Kein Auffang eingerichtet" | Schritt 3 wiederholen, oder `auffang_pfad` / `auffang_folder_id` von Hand eintragen |
| Keine Drive-Ordner in der Liste | Der Drive-Zugang fehlt oder sieht die Bereiche nicht. Das lokale Ziel läuft davon unabhängig weiter |
| Alles landet im Auffang | Normal am Anfang. Zwecksätze setzen (siehe oben) |
| Ein neuer Ordner erscheint nicht | „Ordner neu einlesen" im Tab. Beim Einordnen wird ohnehin immer frisch gescannt |

---

## Ein neues Ablageziel anbinden

S3, WebDAV, Nextcloud, ein DMS: Das ist **ein Adapter mit drei Funktionen** in `apps/dashboard/ablage_ziele.py`.

```python
orte()                          -> [{"id", "label", "gruppe", ...}]
ablegen(ort, daten, name, meta) -> (ok: bool, info: str)
existiert(ort, name)            -> bool
```

Eintragen in `ZIELE`, fertig. Eingang, Leser, Agent und Oberfläche bleiben unangetastet. Der lokale Adapter (`_lokal_ablegen`) ist als Vorlage gedacht: rund zwanzig Zeilen.
