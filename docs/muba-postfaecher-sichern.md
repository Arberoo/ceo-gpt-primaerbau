# MUBA-Postfächer sichern

> Warum: Es ist unklar, wer das Microsoft-365-Konto der MUBA Service GmbH weiter bezahlt. Fällt es weg, sind die Mails weg, auch Verfahrenspost zur Insolvenz. Zwei Wege, die sich ergänzen.
>
> Ablage der Sicherungen: `C:\MUBA-Sicherung` (nicht im MUBA-OneDrive, nicht im CEO-GPT-Ordner, nie zu GitHub). Zusätzlich eine Kopie auf eine externe Festplatte.

## Bestand (gesehen am 14.10.2026, nur Namen und Größen)

| Postfach (MUBA Service GmbH) | Lokal auf dem PC |
|---|---|
| info@muba-service-gmbh.de | 17,9 GB |
| a.bajraktari@muba-service-gmbh.de | 13,9 GB |
| l.bajraktari@muba-service-gmbh.de | 4,6 GB |
| e.bajraktari@muba-service-gmbh.de | 0,8 GB |
| m.bajraktari@muba-service-gmbh.de | ~0 GB |

Outlook hielt bei allen nur **12 Monate** lokal vor (Stand 14.10.2026).

**Offen (Arber klären):** Ein altes Outlook-Profil „Outlook-neu“ enthält zusätzlich Caches von **muba-bau-gmbh.de** (info@ 9 GB, l./m./e./marketing@), **muba-holding.de** (1,8 GB), **mubabau.de** (1,5 GB) und weiteren Postfächern der MUBA Service GmbH (bauleitung@, verwaltung@). Gehören diese Firmen dazu und müssen auch gesichert werden? Die .ost-Dateien lassen sich nicht direkt öffnen. Gesichert wird über Weg B, solange die Konten noch existieren.

## Weg A: über Outlook am PC (schnell, nur was lokal liegt)

1. Datei → Kontoeinstellungen → Postfach → Ändern → Schieberegler „E-Mail offline speichern“ auf **Alle** → Outlook neu starten. Den PC über Nacht laufen lassen, damit alles nachlädt.
2. Am Tag danach: **Datei → Öffnen und Exportieren → Importieren/Exportieren → In Datei exportieren → Outlook-Datendatei (.pst)** → das Postfach ganz oben auswählen (Name des Postfachs), **„Unterordner einbeziehen“** anhaken → speichern als `C:\MUBA-Sicherung\MUBA-<postfach>-<datum>.pst` → **kein Kennwort** vergeben (oder eines, das sicher notiert ist).
3. Prüfen: Die .pst-Datei sollte ungefähr so groß sein wie das Postfach.

Status: 14.10.2026 Umstellung auf „Alle“ bei info@ und l.bajraktari@, Export folgt.

## Weg B: über Microsoft Purview (vollständig, Arber mit Admin-Zugang)

Holt die Postfächer **komplett vom Server**, unabhängig von diesem PC. Arber erledigt das im Browser mit dem Admin-Zugang zum MUBA-Tenant.

1. **purview.microsoft.com** mit dem MUBA-Admin anmelden.
2. Falls nötig, sich die Rolle **eDiscovery-Manager** geben: Einstellungen → Rollen und Bereiche → Rollengruppen → eDiscovery Manager → sich selbst hinzufügen. Die Rechte greifen nach einigen Minuten bis zu einer Stunde.
3. **eDiscovery** → **Fälle** (bzw. „Cases“) → **Fall erstellen**, Name „MUBA Postfach-Sicherung“.
4. Im Fall eine **Suche** anlegen. Datenquellen: **alle MUBA-Postfächer** einzeln hinzufügen (info@, l., a., e., m., bauleitung@, verwaltung@ und weitere). Keine Suchbegriffe, also alles.
5. Suche ausführen, dann **Exportieren**: Format **PST**, eine PST pro Postfach, inklusive teilindizierter Elemente.
6. Unter **Prozesse/Exporte** herunterladen. Die Microsoft-Downloadseite führt durch. Ziel: `C:\MUBA-Sicherung\Purview\`.
7. Danach eine Kopie auf eine externe Festplatte.

Hinweise:
- Microsoft benennt Menüs gelegentlich um. Falls etwas anders heißt: Ziel ist immer „Content Search / Inhaltssuche → Export → PST“.
- Der Export enthält vertrauliche Verfahrenspost. Nicht in Clouds hochladen, nicht per Mail verschicken.
- Lizenzen: Inhaltssuche und Export gehen auch mit Business-Lizenzen (eDiscovery Standard).

## History

| Datum | Änderung |
|---|---|
| 2026-10-14 | Angelegt, Weg A gestartet (Umstellung auf „Alle“) |
