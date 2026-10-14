# Kontext

> Das Gehirn deines Mitarbeiters. Ab der ersten Sitzung kennt er dein Business.

| Feld | Wert |
|---|---|
| Modul | `kontext` |
| Version | v1 |
| Status | RELEASED |
| Released | 2026-02-27 |
| Voraussetzung | Absicherung installiert |
| Setup-Zeit | 30 bis 45 Minuten |
| Laufende Kosten | kostenlos |

## Was hier passiert

- **Geführtes Kontext-Sammeln.** Dein Mitarbeiter interviewt dich zu Business, Rolle, Strategie und Lage. Du wählst zwischen Gespräch, Einfügen oder Dokument-Import.
- **Vier strukturierte Kontext-Dateien** aus deinen Roh-Infos: Geschäfts-Überblick, deine Rolle, Strategie, aktuelle Zahlen.
- **Personalisierte CLAUDE.md.** Deine CEO-GPT-Master-Datei wird auf dein konkretes Business zugeschnitten.
- **Unterstützung für mehrere Geschäfte.** Wenn du mehrere Geschäftsbereiche hast, baut dein Mitarbeiter die Ordner-Struktur passend um.
- **Funktionierender /prime.** Sitzung starten, /prime laufen lassen, dein Mitarbeiter ist im Bild.

## Was du brauchst

- Einen Computer (Mac, Linux, Windows)
- Claude Code installiert und laufend
- Das CEO-GPT-Template entpackt und in deiner IDE offen
- Absicherung installiert (Basis steht)

## Installation

1. Der `kontext` Ordner liegt schon in `module-installs/`
2. Führe `/install module-installs/kontext` aus
3. Folge dem Interview, dein Mitarbeiter führt dich durch

**Geschätzte Setup-Zeit:** 30 bis 45 Minuten

## Kosten

Kostenlos. Keine API Keys und keine externen Dienste, auch keine laufenden Kosten.

## Was hier drin liegt

| Datei | Zweck |
|---|---|
| `INSTALL.md` | Geführtes Interview und Kontext-Aufbau (liest dein Mitarbeiter) |
| `README.md` | Diese Datei, der Überblick für dich |

## Eingabe-Methoden

Du wählst, wie der Kontext reinkommt:

| Methode | Passt gut für |
|---|---|
| **Dokumente importieren** | Dateien in `context/import/` werfen. Businesspläne, ChatGPT-Exporte, Notion-Seiten, alles |
| **Gespräch** | Übers Business reden. Dein Mitarbeiter fragt, du antwortest |
| **Text einfügen** | Aus Webseite, LinkedIn, Strategie-Docs, Notizen reinkopieren |

Du kannst auch mischen, alle drei gleichzeitig nutzen geht.

## Pro-Tipp

Exportier deine ChatGPT-Historie (Einstellungen → Datenkontrolle → Daten exportieren) und leg sie in `context/import/`. Dein Mitarbeiter lernt jede Menge aus deinen alten Gesprächen mit anderen KI-Tools.

## Nach diesem Modul

Dein Mitarbeiter kennt dich jetzt. Er weiß was du machst, wer deine Kunden sind und worauf du gerade Bock hast. Im nächsten Schritt sieht er auch deine Zahlen mit `/install module-installs/daten`.
