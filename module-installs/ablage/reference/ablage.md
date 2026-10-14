# Automatische Ablage

> Betriebs-Doku des Ablage-Moduls. Dateien reinziehen, KI ordnet ein, ein Klick legt ab.
> Code: `apps/dashboard/ablage*.py` + `agents/ablage_agent.py` + `static/views/ablage.js`.

---

## Was es macht

der Geschäftsführer zieht Dateien in den Cockpit-Tab „Ablage". Ein Agent liest jede Datei vollständig aus (PDF, Word, Excel, Scans, Fotos), erkennt, worum es geht, und schlägt für den **ganzen Stapel eine Liste** vor: wohin die Datei gehört und wie sie heißen soll. Ein Klick nimmt alle Vorschläge, einzelne Zeilen korrigiert ein Dropdown. Danach liegen die Dateien wirklich im Google Drive beziehungsweise in der Dokumentenakte, und jeder Agent findet sie über `belege_suchen` wieder.

## Aufbau: drei austauschbare Teile plus ein Kern

| Modul | Rolle | Bei einem anderen Kunden |
|---|---|---|
| `ablage_eingang.py` | Datei rein, quellen-neutral | unverändert |
| `ablage_leser.py` | Text + Metadaten raus, reine Mechanik | unverändert |
| `ablage_struktur.py` | Welche Orte gibt es? | Konfiguration |
| `ablage_ziele.py` | Wie wird geschrieben? | **hier hängt der neue Speicher** |
| `ablage.py` | Das Urteil und die Ausführung | unverändert |

**Ein neues Ziel anzubinden** (lokaler Ordner, Samba, S3) heißt: einen Adapter mit drei Funktionen schreiben und in `ablage_ziele.ZIELE` eintragen. Sonst nichts.

```python
orte() -> [{"id","label","gruppe", ...}]
ablegen(ort, daten, name, meta) -> (ok: bool, info: str)
existiert(ort, name) -> bool
```

## Die vier Regeln im Prompt

Alles andere ist Urteil (Vorgabe: möglichst viel über KI, möglichst wenig statisch gecodet).

1. Wähle **genau eine** `ziel_id` aus der Liste. Unsicher heißt `auffang`, und das ist eine vollwertige Antwort.
2. Rechnung oder Kaufbeleg heißt `ziel_id: buchhaltung`. Du legst sie **nicht** selbst ab.
3. Umbenennen nur, wenn der Name nichts aussagt. Der neue Name kommt aus dem **Inhalt**.
4. Ein Satz je Datei, warum dieses Ziel.

## Die Sperren im Code (nicht im Prompt)

Eine Bitte im Prompt kann das Modell vergessen, eine Prüfung nicht.

| Sperre | Wo | Was sie verhindert |
|---|---|---|
| `ablage_struktur.gueltig(ziel_id)` | `pruefe_aktionen` | Erfundene Ordner und Pfade |
| Vergessene Dateien bekommen den Auffang | `pruefe_aktionen` | Eine Datei fällt still durchs Raster |
| Doppelte `eingang_id` fliegt raus | `pruefe_aktionen` | Dieselbe Datei zweimal im Bündel |
| `name_sagt_nichts()` entscheidet über das Umbenennen | `pruefe_aktionen` | Ein guter Name wird zerstört |
| Buchhaltungs-Ausstieg | `datei_ablegen` | Rechnung liegt doppelt (auch bei `beleg_automatik`) |
| Zielordner-Prüfung plus Eingangs-Status | `datei_ablegen`, `ablegen_frei` | Zweimal Freigeben lädt zweimal hoch |
| Zweite Ziel-Prüfung | `agent_actions._datei_ablegen` | Ordner zwischen Komponieren und Freigeben gelöscht |

## Frische: ein neuer Ordner ist sofort wählbar

**Vor jeder Einordnung wird frisch gescannt** (`orte(frisch=True)`). Ein Scan kostet ein bis zwei Sekunden, der LLM-Aufruf danach zehn bis dreißig. Ein Cache an dieser Stelle spart nichts und macht das System um einen Tag dumm.

Der Cache in `data/ablage/struktur.json` ist **nur für die Anzeige** und darf nie die Grundlage eines Urteils sein. Er liefert immer sofort, auch wenn er alt ist, und zieht im Hintergrund nach: ein Blick in den Tab darf nie auf einen Drive-Scan warten.

**Ein Ordner ohne Zwecksatz ist trotzdem ein gültiges Ziel.** Der Ordnername geht immer mit in den Prompt und erklärt sich meistens selbst. Ohne diese Regel wäre jeder frisch angelegte Ordner unerreichbar, bis ihn jemand beschreibt, und das fiele niemandem auf. Der Tab zeigt „N Ordner ohne Zweck" mit einem Knopf.

## Zwecksätze: der einzige kundenspezifische Teil

`data/ablage/zwecke.json` hält je Ordner einen Satz, was dort hineingehört. Beim ersten Lauf schlägt die KI die Sätze selbst vor (aus Ordnername, Pfad und den ersten Dateinamen darin), der Geschäftsführer korrigiert einmal.

**Liegt die Einordnung zu oft daneben, ist der erste Hebel nicht der Prompt, sondern der Zwecksatz.** Genau deshalb liegt er in einer Datei, die man anfassen kann, und nicht im Code.

## Neue Ordner entstehen aus Belegen

Die KI legt nie selbst einen Ordner an. Sammeln sich vier gleichartige Dokumente länger als sieben Tage im Auffang, erzeugt `ordner_vorschlaege()` einen Vorschlag **mit den vier Dokumenten als Begründung**. Dasselbe Muster wie `agent_lernen.verdichten()` (Regel erst ab drei Fällen).

## Konfiguration

`config/dashboard.json` → `ablage`:

| Schlüssel | Bedeutung |
|---|---|
| `drives` | Ziel-Drives. Draußen: Buchhaltung (macht `beleg_automatik`), Content (eigene Logik), Marketing, Backup, AI PIONEERS |
| `auffang_folder_id` | Der Auffangordner, bei der Geschäftsführer in **My Drive** — niemand außer ihm sieht ihn, damit liegt Unsortiertes nie in einem Team-Ordner |
| `gesperrte_pfade` | `Projekte/01 Kunden/*/Aufnahmen` (dort ist der **Kunde** eingeladen) |
| `max_je_stapel` | 15 |

`data/agents/config.json` → `ablage`: `enabled`, `auto_eingang` (Mail-Anhänge, noch aus).

## Betrieb

```bash
.venv/bin/python -m apps.dashboard.agents.ablage_agent # zeigen, was er vorhätte
.venv/bin/python -m apps.dashboard.agents.ablage_agent --schreiben # Karte anlegen
.venv/bin/python scripts/test_ablage.py # 49 Prüfungen, ohne Netz
.venv/bin/python scripts/test_ablage_browser.py # 13 Prüfungen im echten Browser
```

Scheduler-Tick `_tick_ablage` alle 5 Minuten (liest nur die lokale Eingangs-Tabelle, kostet ohne Dateien nichts). Agenten-Takt `interval_hours = 0.1`.

## Fallstricke

- **My Drive braucht andere API-Parameter als ein Shared Drive.** Die bestehenden Aufrufe setzen `corpora="drive"` plus `driveId`; für My Drive muss beides **weg**. Ein Shared-Drive-Aufruf gegen My Drive liefert stillschweigend eine **leere Liste**, der Auffangordner sähe damit aus, als gäbe es ihn nicht, und es erschiene nirgends ein Fehler. Gekapselt in `beleg_drive._list_args()`.
- **Der Drive heißt `Ordner A`, nicht `Manag`.** `reference/drive-struktur.md` nennt ihn falsch. Dort stehen außerdem zwei `Marketing`-Drives nicht drin, die es gibt.
- **GET-Routen liefern `(status, obj)`, nicht nur das Objekt.** `api.handle_get` entpackt genau zwei Werte; ein nacktes dict ergibt „too many values to unpack" als HTTP 500.
- **Die Begründung des Modells steht in `args["beschreibung"]`, nicht in `a["beschreibung"]`.** Letzteres trägt nur das technische Label aus `_record` („Datei ablegen: eing-…"). Wer das zuerst nimmt, zeigt im Tab eine ID statt eines Satzes.
- **Der Dateiname kommt aus dem Inhalt, nie aus etwas, das zufällig danebensteht.** Bei der Beleg-Automatik war der letzte Pfadteil einer Stripe-Adresse schlicht `pdf`, alles hieß `pdf.pdf`, und die nächste Rechnung wurde als Dublette verworfen.
- **Smoke-Checks prüfen den Quelltext, nicht die Ausführung.** Beim Bau waren zwei Fehler grün, die den Tab komplett lahmlegten: `pageHead()` mit einem statt zwei Argumenten und `el(tag, cls, html)` mit einem Objekt statt einem Klassen-String. Der Tab zeigte nur „Diese Ansicht konnte nicht geladen werden". **Ob eine Seite lädt, kann nur ein Browser sagen** — dafür gibt es `scripts/test_ablage_browser.py` (13 Prüfungen).
- **Die Bausteine haben feste Signaturen**, die man nicht raten darf: `el(tag, cls, html)` (Klasse als String), `pageHead(root, {...})` und `guard(host, …)` hängen selbst an und geben nichts Anhängbares zurück, `schlossKnopf()` liefert ein **Array**, `icons()` nimmt keine Argumente (Icons kommen als `<i data-lucide="…">`), `toast(text, {type})` kennt `success|warn|error|info`.
- **Jede Kürzung wird markiert.** Ein Modell, das nicht weiß, dass es nur 20 von 120 Seiten sieht, urteilt selbstbewusst falsch.

## Bewusst nicht gebaut

- **Mail-Anhänge als automatischer Eingang.** Schalter `auto_eingang` steht auf `false`. Erst soll der Handweg sauber laufen.
- **Ein Skill.** Nicht auf Vorrat. Weil die Einordnung in `ablage.py` liegt, kostet er später eine halbe Stunde und kann nie ein zweites Urteil erzeugen.
- **Volltext-Index über den ganzen Drive.** `ablage_verlauf` beantwortet die eigentliche Frage schon.
- **Das Kundenmodul.** Erst bei der Geschäftsführer sauber. Der Adapter-Vertrag ist die ganze Vorbereitung dafür.

## History

| Datum | Änderung |
|---|---|
| 2026-08-31 | Gebaut. Erster echter Lauf: 4 Dateien, Rechnung korrekt liegen gelassen, guter Name unangetastet, `scan_0012.pdf` mit Datum aus dem Inhalt umbenannt, Unpassendes in den Auffang. Im Drive gegengeprüft. |
