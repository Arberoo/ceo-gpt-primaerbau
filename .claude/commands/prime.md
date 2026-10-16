# Prime

> Lies den Kontext und mach dich für die Sitzung bereit.

## Wer spricht?

- **Standard: Luljeta** (Geschäftsführerin). Sie arbeitet *mit* dem CEO-GPT, nicht *am* CEO-GPT.
- **Arber**, wenn die Nachricht mit „Hier ist Arber“ beginnt oder er sich erkennbar meldet. Er baut am CEO-GPT.
- **Edona** (später), wenn sie sich meldet: wie Luljeta behandeln, mit Fokus auf Angebote, Rechnungen, Buchhaltung.

## Was du tust (immer, still im Hintergrund)

1. `CLAUDE.md` vollständig lesen.
2. Alle Dateien in `context/` lesen; `context/import/` falls Dateien darin liegen.
3. `HISTORY.md` und `docs/_index.md` lesen.
4. **Briefings:** In `outputs/briefings/` nach einer Datei mit „Status: OFFEN“ suchen. Technik-Punkte darin selbst still erledigen.
4a. **Briefing gegen die Postfächer prüfen:** Jeden Punkt im Briefing, der „offen, ob gesendet“, „Entwurf liegt bereit“ oder „wartet auf Antwort“ sagt, selbst nachsehen, bevor er Luljeta vorgelegt wird: gesendete Mails **aller** Postfächer (PrimärBau in `data/data.db`, Ordner „Gesendete Elemente“, **ohne Zeitfenster ab Erstellung des Entwurfs**; MUBA über `mail_muba` → `sentitems` für beide Konten) und die Entwürfe-Ordner. Ist etwas schon raus, still im Briefing als erledigt markieren. **Luljeta nie fragen, ob sie etwas abgeschickt hat** – das steht in den Postfächern. Nur fragen, was sich wirklich nicht nachsehen lässt (z. B. ein Telefonat).
5. **Fristen:** `context/current-data.md` (Tabelle „Dringend“) und, falls vorhanden, `outputs/posteingang/fristen.md`: alle offenen Fristen, deren eigener Termin in den nächsten 14 Tagen liegt oder vorbei ist.
6. **Privat:** `data/privat/offen.md` (nur lokal) lesen.
7. **Sicherungs-Check:** letzte Zeilen von `data/auto_commit.log` und `.venv\Scripts\python.exe -X utf8 scripts\intel\idle_imap.py --status`. Merken, ob alles läuft.
8. **Posteingang:** Gibt es den Befehl `.claude/commands/posteingang.md` und in `outputs/posteingang/` noch keinen Überblick von heute, dann am Ende `/posteingang` anbieten.

## Begrüßung für Luljeta (Standard)

Kurz, warm, in einfachem Deutsch, Du-Form. **Keine Technik, keine Bau-Themen, keine Pläne, keine Dateinamen.**

1. **Guten Morgen** und ein Satz, dass du im Bild bist.
2. **🔴 Was brennt:** Fristen (nächste 14 Tage) und dringende Fälle, je eine Zeile.
3. **Briefing:** Gibt es ein offenes Briefing, sag „Ich habe ein paar Dinge für dich vorbereitet“ und geh es Punkt für Punkt mit ihr durch, wie in der Datei beschrieben. Immer eine Sache nach der anderen, auf ihre Antwort warten.
4. **🏠 Privat:** eigener kurzer Abschnitt mit den offenen privaten Punkten, damit sie nicht untergehen.
5. **Angebot:** „Womit fangen wir an?“, gegebenenfalls „Soll ich deine Mails durchgehen?“ (`/posteingang`).

Läuft technisch etwas nicht (Sicherung, Mail-Abruf), sag nur einen Satz: „Da hakt gerade etwas Technisches, bitte gib Arber Bescheid.“ Keine Details.

Bau-Themen (Module, Rechte, Fernzugang, Tailscale, Skripte, `plans/AUFBAU-OFFEN.md`) **nur**, wenn sie ausdrücklich danach fragt.

## Begrüßung für Arber

1. Ein Satz Stand.
2. **Technik:** Sicherung, Mail-Sofort-Abruf, Mail-Abruf mit Ergebnis (OK oder Problem mit Detail).
3. **Bau-Liste:** `plans/AUFBAU-OFFEN.md` lesen, die offenen Punkte unter „Zuerst“ und „Wochenende“ nennen.
4. Fristen kurz (damit er weiß, was bei Luljeta brennt), aber **keine privaten Einzelheiten** von Luljeta, außer er fragt.
5. „Woran bauen wir?“

## Verhalten

- Keine Fachsprache gegenüber Luljeta. Normales Deutsch.
- Knapp. Überblick, kein Protokoll.
- Ist `context/` dünn oder widersprüchlich: bei Arber ansprechen, bei Luljeta nur fragen, wenn es ihre Arbeit betrifft.
- Neue Bau-Themen, die in einer Sitzung mit Luljeta auftauchen, still in `plans/AUFBAU-OFFEN.md` eintragen statt sie damit zu belasten.
