# Buchhaltung

> Dein Mitarbeiter macht den Monatsabschluss. Jede Kontobewegung bekommt ihren Beleg, nichts fehlt mehr, und dein Steuerberater bekommt fristgerecht eine fertige Liste.

| Feld | Wert |
|---|---|
| Modul | `buchhaltung` |
| Version | v1 |
| Status | RELEASED |
| Voraussetzung | `kontext` empfohlen |
| Optional | `stimme` (Reminder), `intelligenz-google`/`intelligenz-imap` (Beleg-Suche, Steuerberater-Mails), Bankanbindungs-Modul |
| Setup-Zeit | 25 bis 40 Minuten |
| Laufende Kosten | kostenlos, keine API Keys |

## Was hier passiert

- Eine **saubere Ordnerstruktur** pro Monat: Ausgangsrechnungen, Eingangsrechnungen, Ausgaben, Kontoauszug, Privatauslagen
- Eine **Engine**, die dein Bank-CSV als Hauptbuch nimmt und jede Buchung gegen die abgelegten Belege abgleicht
- Ein **Audit**, der dir pro Monat sagt, was belegt ist, was belegfrei ist und was noch fehlt, inklusive Kontoauszug als CSV und PDF
- **Privatauslagen und Cash** werden separat erfasst und am Monatsende aktiv abgefragt, damit nichts durchfällt, was nie über die Bank lief
- Eine **Buchungsliste** als fertiges Arbeitspapier für deinen Steuerberater
- Ein **Reminder** vor der Frist, per Telegram (optional, wenn die Stimme installiert ist)
- Ein **Playbook** (Skill), mit dem dein Mitarbeiter den Ablauf jeden Monat gleich sauber abzieht

## Wie er dich produktiver macht

Der Monatsabschluss ist lästig und frisst Zeit: Belege zusammensuchen, zuordnen, prüfen, was fehlt, alles an den Steuerberater geben. Dein Mitarbeiter übernimmt genau das. Du legst die Belege ab, er macht den Rest und sagt dir, was noch fehlt. Die Theorie ist immer gleich: Du hast Buchungen, jede braucht einen Beleg. Nur die Quelle der Buchungen ist von Setup zu Setup anders, und genau das stellt der Installer mit ein paar Fragen ein.

## Was du brauchst

- Einen Computer (Mac empfohlen für den Reminder, der Rest läuft überall)
- Python 3.10 oder neuer
- Einen Ort für deine Buchhaltung (lokal oder Cloud wie Google Drive, Dropbox)
- Den Kontoauszug deiner Bank als Export (CSV und PDF). Falls deine Bank ans CEO-GPT angebunden ist, zieht es die Buchungen direkt.

## Installation

1. Der `buchhaltung`-Ordner liegt in `module-installs/`.
2. Starte `/install module-installs/buchhaltung`.
3. Dein Mitarbeiter stellt dir ein paar Fragen (Bank, Steuerberater, Frist, Sprache, Privatauslagen) und richtet alles darauf ein.

## Kosten

Kostenlos. Keine API Keys. Der optionale Reminder nutzt deinen bestehenden Telegram-Bot aus dem Stimme-Modul.

## Was hier drin liegt

| Datei | Zweck |
|---|---|
| `INSTALL.md` | Das geführte Setup (für deinen Mitarbeiter) |
| `README.md` | Diese Übersicht |
| `scripts/buchungsliste.py` | Die Engine: Abgleich, Buchungsliste, Audit, Privatauslagen |
| `scripts/check_buchungsquelle.py` | Prüft, ob eine Bankanbindung existiert |
| `scripts/buchhaltung_reminder.py` | Telegram-Reminder vor der Frist |
| `config/buchhaltung.config.example.json` | Vorlage der Anpassungsschicht |
| `config/com.ceogpt.buchhaltung-reminder.plist` | launchd-Vorlage für den Reminder |
| `templates/bank-presets.json` | Spalten-Mappings pro Bank (Revolut fertig, Rest ausfüllbar) |
| `skill/SKILL.md` | Das Playbook für den Monatsabschluss |
| `skill/references/beleg-beschaffung.md` | Wo und wie die Belege zusammenkommen |

## Wie das mit der Hand zusammenhängt

Buchhaltung ist ein Stück von "Die Hand": wiederkehrende Arbeit, die dein Mitarbeiter dir abnimmt. Sie steht für sich, wird aber stärker mit anderen Modulen: mit der Stimme erinnert sie dich, mit den Intelligenz-Modulen sucht sie Belege in deinen Mails und schreibt die Steuerberater-Entwürfe, mit einem Bankanbindungs-Modul zieht sie die Buchungen selbst.

## Pro-Tipp

Leg jeden Beleg sofort in den richtigen Monatsordner, sobald er reinkommt. Dann ist der Monatsabschluss am Ende fast geschenkt, und dein Mitarbeiter muss nur noch den Kontoauszug drüberlegen.

## Nach diesem Modul

Wenn du willst, dass dein Mitarbeiter die Buchungen selbst aus der Bank zieht, statt sie zu exportieren, ist das ein eigenes Bankanbindungs-Modul. Das Buchhaltungs-Modul erkennt eine solche Anbindung automatisch und nutzt sie.

## Inhaltseingang

Belege und freigegebene Buchungen unmittelbar nach Verfügbarkeit übernehmen.

Einrichtungsstandard und Grenzen: [reference/dateneingang.md](reference/dateneingang.md).
Dieses Patch-Update korrigiert die Installationsvorgaben; zusätzliche Dienste werden
dadurch nicht automatisch eingerichtet. KI-Schritte sind separat zu aktivieren.
