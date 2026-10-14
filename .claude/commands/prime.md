# Prime

> Lies den Kontext und mach dich für die Sitzung bereit.

## Was du tust

1. Lies `CLAUDE.md` vollständig
2. Lies alle Dateien in `context/` durch
3. Wenn `context/import/` Dateien enthält, schau auch dort rein
4. `HISTORY.md`: CEO-GPT-Logbuch (was wurde gebaut, wann, von wem)
5. `docs/_index.md`: Doku-Routing-Index (hier findest du die passenden Dokus)
6. Offene Briefings: Schau in `outputs/briefings/`. Gibt es eine Datei mit „Status: OFFEN“, ist das der wichtigste Punkt der Sitzung. Arbeite sie nach der Zusammenfassung mit Luljeta durch, wie in der Datei beschrieben (erst Technik-Check selbst erledigen, dann Punkt für Punkt erklären und fragen).
8. Privat: Lies `data/privat/offen.md` (nur lokal). Offene private Punkte bekommen in der Zusammenfassung einen **eigenen Abschnitt „🏠 Privat“**, getrennt vom Geschäftlichen, damit sie im Trubel nicht untergehen. Private Einzelheiten nie in Dateien schreiben, die zu GitHub gehen (`context/`, `outputs/`, `docs/`), sondern nur nach `data/privat/`.
7. Sicherungs-Check: Lies die letzten Zeilen von `data/auto_commit.log`. Ist der letzte erfolgreiche Lauf älter als drei Tage oder steht dort „Push scheiterte“/„Fehler“, sag das gleich zu Beginn in einem Satz (Lösung: `docs/absicherung-windows.md`).

## Zusammenfassung an den Geschäftsführer

Wenn du fertig gelesen hast, fass kurz zusammen:

1. **Wer er ist und was sein Business macht.** Ein bis zwei Sätze. Zeig, dass du das Bild hast.
2. **Seine Rolle.** Wofür er verantwortlich ist und wo seine Zeit hingeht.
3. **Aktuelle Prioritäten.** Was diese Wochen oder dieses Quartal zählt.
4. **Stand der Zahlen.** Wichtige Kennzahlen aus `current-data.md`, falls vorhanden.
5. **Verfügbare Befehle.** Welche Slash-Befehle in `.claude/commands/` liegen.
6. **Bereit.** Bestätige knapp, dass du im Bild bist und auf Anweisungen wartest.

## Verhalten

- Keine Fachsprache. Normales Deutsch.
- Knapp, nicht überfrachtet. Der Geschäftsführer will einen Überblick, kein Protokoll.
- Wenn `context/` noch leer oder dünn ist, sag das ehrlich. Empfiehl `/install module-installs/kontext`, damit das Gehirn deines Mitarbeiters einen echten Stand bekommt.
- Wenn etwas in den Kontext-Dateien widersprüchlich oder veraltet wirkt, weis darauf hin. Nicht überstimmen, sondern fragen.
