# Buchhaltung: Installation

## Verbindlicher Standard für den Inhaltseingang · 1.0.1

**Vor der Einrichtung [reference/dateneingang.md](reference/dateneingang.md) lesen und anwenden.**
Empfohlen: Belege und freigegebene Buchungen unmittelbar nach Verfügbarkeit übernehmen.

Diese Vorgabe ergänzt die bisherige Anleitung: automatische Übernahme der ausgewählten
Nachrichten und Termine gehört zur Grundeinrichtung. Frühere optionale Collector-Phasen
beschreiben nur noch zusätzliche Historienkopien; deren Zeitpläne sind kein Echtzeitnachweis.
Die Anleitung zur Quelle nennt nötige Ergänzungen und Grenzen. Keine KI-Schritte allein
für den Empfang einschalten; zusätzliche KI-Kosten vor Aktivierung erklären und Zustimmung
einholen. Bereits passende Zustimmung gilt weiter.

**Versionstyp: Installationsstandard korrigiert.** Kein mit dieser Dokumentversion
automatisch ausgerollter Echtzeitdienst; tatsächlichen Inhaltseingang im Zielsetup abnehmen.


<!-- MODUL-METADATEN
modul: buchhaltung
version: 1.0.1
status: RELEASED
released: 2026-06-09
requires: [kontext]
optional: [stimme, intelligenz-google, intelligenz-imap, daten]
phase: 4
category: Erweiterung
complexity: medium
api_keys: 0
setup_time: 25-40 Minuten
-->

---

## FÜR CLAUDE (Anleitung für dich, das Programm)

Du baust dem Member den **monatlichen Buchhaltungs-Ablauf** auf, ein Stück von "Die Hand". Ab jetzt sortiert dein Mitarbeiter jeden Monat die Belege, gleicht jede Kontobewegung gegen ihren Beleg ab, erfasst Privatauslagen, erzeugt die Buchungsliste und erinnert vor der Frist. Der lästige Monatsabschluss für den Steuerberater wird Routine.

**Die Theorie ist immer gleich, nur die Quelle variiert:** Du hast Buchungen, jede braucht einen Beleg. Die einzige offene Frage ist, woher die Buchungen kommen.

**Kernkonzepte, die du verstehen musst:**
- Das **Bank-CSV ist das Hauptbuch.** Jede Zeile bekommt einen Beleg oder gilt als belegfrei.
- Eine **Config-Datei** (`buchhaltung.config.json`) ist die einzige Stellschraube. Bank-Spalten, Kategorien, Steuerberater, Frist, Sprache, Ordnerpfad stehen dort. Engine, Reminder und Skill lesen daraus.
- Dieses Modul **baut keine Bankanbindung.** Es prüft nur, ob eine existiert, und fragt sonst nach manuellem Export. Die Anbindung ist Sache eines separaten Moduls.
- **Privatauslagen und Cash** (privat oder bar bezahltes Geschäftliches) haben keine Bankzeile, werden separat geführt und am Monatsende aktiv abgefragt.

**Verhalten:**
- Geh davon aus, dass der Member nicht technisch ist
- Erklär in Klartext, was du als Nächstes machst, bevor du es machst
- Feier kleine Wins ("Engine läuft, der Abgleich sitzt")
- Wenn was schiefgeht, kein Log-Dump. Erklär das Problem in einem Satz und schlag den Fix vor.
- Halt nach jedem Meilenstein kurz inne.

**Sicherheit (hart, nicht verhandelbar):**
- **Nie selbst ins Banking einloggen.** Logins gibt immer der Member ein.
- Nie nach Passwörtern, Codes oder Zugangsdaten im Chat fragen. Nur über sichere Share-Links.
- Die echte `.env` nie lesen. Dieses Modul braucht keine eigenen Geheimnisse. Sollte doch je eins nötig sein: nicht von Hand in die `.env`, sondern verdeckt über `python scripts/set_secret.py KEY` (harmlose Werte mit `--show`). Keine Platzhalter mehr anhängen.
- **Nicht als Steuerberater auftreten.** Kategorien sind Vorschläge, finale Kontierung und VAT setzt der Steuerberater.

**Fehlerbehandlung:**
- Python zu alt oder PyMuPDF fehlt? Genaue Schritte liefern, nicht "schau in die Logs".
- Engine findet keine Config? Heißt, die Config wurde noch nicht angelegt, Schritt davor nachholen.

---

## ÜBERSICHT (lies das dem Member vor dem Start vor)

Jetzt bauen wir deine Buchhaltung auf. Ab heute übernimmt dein Mitarbeiter den Monatsabschluss: Er ordnet jede Kontobewegung ihrem Beleg zu, sieht sofort was fehlt, hält Privatauslagen fest, erzeugt eine fertige Buchungsliste für deinen Steuerberater und erinnert dich rechtzeitig vor der Frist.

Das ist der Plan:

- Eine **saubere Ordnerstruktur** pro Monat (Rechnungen rein, Ausgaben, Kontoauszug, Privatauslagen)
- Eine **Engine**, die dein Bank-CSV gegen die abgelegten Belege abgleicht und dir sagt, was noch fehlt
- Eine **Buchungsliste** als fertiges Arbeitspapier für deinen Steuerberater
- Ein **Reminder** vor der Frist (optional, per Telegram, wenn die Stimme installiert ist)
- Ein **Playbook** (Skill), mit dem dein Mitarbeiter den Ablauf jeden Monat gleich sauber abzieht

**Setup-Zeit:** 25 bis 40 Minuten
**Kosten:** kostenlos, keine API Keys
**Datenschutz:** Alles bleibt lokal in deinem Workspace und deinem Buchhaltungsordner. Nichts wandert ungefragt raus.

---

## VORAUSSETZUNGEN

### Python 3.10+ und venv
```bash
python3 --version
ls .venv/bin/python 2>/dev/null && echo "venv da" || echo "venv fehlt"
```
Falls die venv fehlt: `python3 -m venv .venv`

### PyMuPDF (liest die Beleg-PDFs)
```bash
.venv/bin/python -c "import fitz; print('PyMuPDF OK')" 2>/dev/null || .venv/bin/pip install pymupdf
```

### Kontext
Check, ob `context/business-info.md` existiert. Falls nicht, empfiehl, erst `kontext` einzurichten (blockiert aber nicht).

### Optionale Module (nur Hinweis)
- **stimme**: für den Telegram-Reminder. Ohne sie läuft alles, nur ohne Push.
- **intelligenz-google / intelligenz-imap**: für E-Mail-Suche nach Belegen und Steuerberater-Entwürfe.
- **daten** oder ein Bankanbindungs-Modul: falls die Buchungen automatisch gezogen werden sollen.

[VERIFY] Python, venv und PyMuPDF sauber. "Alles steht, wir können loslegen."

---

## SCOPING (Fragen, die das Setup zuschneiden)

Stell diese Fragen nacheinander, in Klartext, und halt die Antworten fest. Sie füllen am Ende die Config.

### Frage 1: Woher kommen die Buchungen?
Lauf zuerst den Quellen-Check (nach dem Kopieren der Skripte, siehe unten), oder frag direkt: "Ist deine Bank schon ans CEO-GPT angebunden, oder exportierst du den Kontoauszug selbst?"
- Record: `SOURCE_MODE = auto | manual` (Default `manual`)

### Frage 2: Welche Bank, und wie sieht der Export aus?
"Welche Bank nutzt du fürs Geschäft?" Wenn es **Revolut** ist, gibt es ein fertiges Spalten-Preset. Sonst: lass dir die **Kopfzeile** einer Beispiel-CSV geben und ordne die Spalten zu (welche Spalte ist Datum, Betrag, Verwendungszweck, Referenz).
- Record: `BANK_NAME`, `BANK_PRESET = revolut | generic`, bei generic das `csv_column_map`
- Mehrere Konten/Karten? Pro Quelle einen Eintrag in `bank_sources`.

### Frage 3: Wo liegt dein Buchhaltungsordner?
"Wo sollen die Unterlagen liegen, lokal oder in einer Cloud (Google Drive, Dropbox)? Gib mir den Pfad." 
- Record: `FOLDER_ROOT` (absoluter Pfad)

### Frage 4: Dein Steuerberater
"Wie heißt dein Steuerberater, wie ist die E-Mail, und wie willst du übergeben (geteilter Ordner oder E-Mail-Entwurf)? Bis wann im Monat braucht er die Unterlagen?"
- Record: `STB_NAME`, `STB_EMAIL`, `HANDOVER = shared_folder | email`, `DEADLINE_DAY` (Default 10)

### Frage 5: Sprache
"In welcher Sprache läuft die Buchhaltung (Ordnernamen, Liste) und in welcher die Mails an den Steuerberater?"
- Record: `LANGUAGE = de | en`, `STB_LANGUAGE = de | en`

### Frage 6: Privatauslagen und Cash
"Kommt es vor, dass du Geschäftliches privat oder bar bezahlst? Dann erfassen wir das separat und ich frage am Monatsende aktiv danach."
- Record: `PRIVATE_ENABLED = true | false` (Default true)

### Frage 7: Reminder
Nur falls **stimme** installiert ist: "Soll ich dich per Telegram vor der Frist erinnern? An welchen Tagen im Monat?"
- Record: `REMINDER_CHANNEL = telegram | none`, `SEND_DAYS` (Default [1,5,8,10])

### Frage 8: Kategorien
"Sollen wir mit einem Standard-Satz Kategorien starten, oder hast du einen Kontenplan von deinem Steuerberater, an dem wir uns ausrichten?"
- Record: `CATEGORIES = default | custom`

Fass am Ende zusammen: "Plan: Bank {BANK_NAME}, Quelle {SOURCE_MODE}, Steuerberater {STB_NAME} bis zum {DEADLINE_DAY}., Sprache {LANGUAGE}, Privatauslagen {PRIVATE_ENABLED}, Reminder {REMINDER_CHANNEL}. Passt?"

---

## INSTALLATION

`MODULE_DIR` = der Pfad dieses Moduls (z.B. `module-installs/buchhaltung`). `WORKSPACE_ROOT` = Workspace-Wurzel.

### Schritt 1: Skill-Ordner und Skripte anlegen

"Ich lege das Buchhaltungs-Playbook und die Engine an."

```bash
mkdir -p .claude/skills/buchhaltung/scripts .claude/skills/buchhaltung/references
cp MODULE_DIR/skill/SKILL.md .claude/skills/buchhaltung/SKILL.md
cp MODULE_DIR/skill/references/beleg-beschaffung.md .claude/skills/buchhaltung/references/beleg-beschaffung.md
cp MODULE_DIR/scripts/buchungsliste.py .claude/skills/buchhaltung/scripts/buchungsliste.py
cp MODULE_DIR/scripts/check_buchungsquelle.py .claude/skills/buchhaltung/scripts/check_buchungsquelle.py
cp MODULE_DIR/templates/bank-presets.json .claude/skills/buchhaltung/scripts/bank-presets.json
```

[VERIFY] `ls .claude/skills/buchhaltung/scripts/` zeigt `buchungsliste.py`, `check_buchungsquelle.py`, `bank-presets.json`.

### Schritt 2: Config aus den Antworten bauen

"Jetzt trage ich deine Antworten in eine Konfigurationsdatei ein. Das ist die einzige Stellschraube, hier ändern wir später alles."

Kopier die Vorlage und füll sie mit den Scoping-Antworten:

```bash
cp MODULE_DIR/config/buchhaltung.config.example.json .claude/skills/buchhaltung/buchhaltung.config.json
```

Dann die Datei mit dem Edit-Tool füllen (alle `<...>`-Platzhalter ersetzen):
- `language` ← LANGUAGE, `folder_root` ← FOLDER_ROOT, `year` ← aktuelles Jahr
- `owner_name` ← Name des Inhabers/Gesellschafters (für Eigeneinlagen-Erkennung)
- `bank_sources[0]` ← BANK_NAME, BANK_PRESET; bei generic das `csv_column_map` aus Frage 2; sonst `csv_column_map: null` (Preset greift)
- `accountant` ← STB_NAME, STB_EMAIL, STB_LANGUAGE, HANDOVER, DEADLINE_DAY
- `reminder` ← REMINDER_CHANNEL, SEND_DAYS
- `private_expenses.enabled` ← PRIVATE_ENABLED
- `categories` ← bei `default` einen vernünftigen Satz eintragen (Umsatz aus Rechnungsnummer-Präfix, Software/SaaS, Abgaben & Versicherung als belegfrei); bei `custom` am Kontenplan ausrichten
- `company_keywords` ← die wiederkehrenden Anbieter des Members (für den Namens-Match), nur markante Firmennamen

[VERIFY] `.venv/bin/python -c "import json; json.load(open('.claude/skills/buchhaltung/buchhaltung.config.json')); print('Config valide')"`

### Schritt 3: Platzhalter im Skill füllen

Ersetz im `.claude/skills/buchhaltung/SKILL.md` die `{{...}}`-Platzhalter mit den echten Werten (FIRMA, BANK, STEUERBERATER, STB_EMAIL, FRIST_TAG, ORDNER_ROOT).

[VERIFY] `grep -c "{{" .claude/skills/buchhaltung/SKILL.md` ergibt `0`.

### Schritt 4: Ordnerstruktur anlegen

"Ich lege die Monatsstruktur in deinem Buchhaltungsordner an."

Erzeug unter `FOLDER_ROOT/{Jahr}/` den `00 Contracts & Records` und für jeden bisherigen Monat die fünf Unterordner (`1 Sales Invoices`, `2 Purchase Invoices`, `3 Expenses`, `4 Bank Statements`, `5 Private & Cash`, letzterer nur wenn PRIVATE_ENABLED). Monatsnamen je nach Sprache (`05 Mai` / `05 May`).

[VERIFY] Die Ordner stehen, der Member sieht sie in seinem Finder/Cloud.

### Schritt 5: Quellen-Check und Engine testen

"Jetzt prüfe ich, ob deine Bank schon angebunden ist, und teste den Abgleich."

```bash
.venv/bin/python .claude/skills/buchhaltung/scripts/check_buchungsquelle.py
```

- Quelle gefunden: kurz zeigen, dass automatisch gezogen werden kann.
- Keine Anbindung: den Member um eine Beispiel-CSV (ein Monat) bitten, in `4 Bank Statements` legen.

Dann die Engine gegen die CSV laufen lassen:

```bash
.venv/bin/python .claude/skills/buchhaltung/scripts/buchungsliste.py "PFAD/zur/Monat.csv" --split
```

[VERIFY] Es entsteht `Buchungsliste_{Jahr}.csv`, und der Audit zeigt pro Monat "mit Beleg / belegfrei / FEHLEN" plus "Kontoauszug CSV/PDF". Erklär dem Member, dass FEHLEN die Posten ohne Beleg sind, die er noch nachzieht.

### Schritt 6: Reminder (optional, braucht stimme)

Check, ob die Stimme da ist:
```bash
python3 -c "import os; from dotenv import load_dotenv; load_dotenv(); print('Telegram OK' if os.getenv('TELEGRAM_BOT_TOKEN') else 'Telegram FEHLT')"
```

**Wenn FEHLT:** Reminder-Teil überspringen, dem Member sagen, dass er ihn nach `/install module-installs/stimme` nachholen kann.

**Wenn OK:**
```bash
cp MODULE_DIR/scripts/buchhaltung_reminder.py scripts/buchhaltung_reminder.py
.venv/bin/python scripts/buchhaltung_reminder.py --dry-run --force
```
Die Dry-Run-Nachricht sollte sauber erscheinen (mit dem Namen des Steuerberaters und der Frist).

Dann die launchd-Vorlage mit echten Pfaden füllen und laden:
```bash
PYBIN="$(cd "$(pwd)" && pwd)/.venv/bin/python"
sed -e "s#__PYTHON__#${PYBIN}#g" -e "s#__WORKSPACE__#$(pwd)#g" \
    MODULE_DIR/config/com.ceogpt.buchhaltung-reminder.plist \
    > ~/Library/LaunchAgents/com.ceogpt.buchhaltung-reminder.plist
launchctl load ~/Library/LaunchAgents/com.ceogpt.buchhaltung-reminder.plist
```

[VERIFY] `launchctl list | grep buchhaltung` listet den Job. Optional Sofort-Test: `launchctl start com.ceogpt.buchhaltung-reminder` und Telegram prüfen.

### Schritt 7: CLAUDE.md aktualisieren

Trag in `CLAUDE.md` ein:
- Einen kurzen **Buchhaltungs-Abschnitt**: monatlicher Ablauf, Engine `.claude/skills/buchhaltung/scripts/buchungsliste.py`, Config `buchhaltung.config.json`, Buchungsliste als Deliverable, Frist.
- Falls Reminder aktiv: den launchd-Job `com.ceogpt.buchhaltung-reminder` (täglich, erinnert vor der Frist) in die Service-Liste.
- Den Skill `buchhaltung` als verfügbare Fähigkeit erwähnen.

[VERIFY] `grep -i buchhaltung CLAUDE.md` zeigt die neuen Einträge.

---

## TEST

- Engine läuft gegen die Beispiel-CSV, Buchungsliste und Audit stehen.
- Ein Test-Beleg in `5 Private & Cash` erscheint in der Auslagenliste, nicht im Bank-Audit.
- Falls Reminder: Dry-Run zeigt die richtige Nachricht.

"Dein Buchhaltungs-Setup läuft. Ab jetzt machen wir den Monatsabschluss zusammen, ich sage dir jeden Monat, was noch fehlt."

---

## WAS ALS NÄCHSTES

*"Deine Buchhaltung steht. Ich halte ab jetzt jeden Monat die Belege sauber und erinnere dich vor der Frist.*

*Wenn deine Bank noch nicht angebunden ist und du willst, dass ich die Buchungen selbst ziehe, ist das ein eigenes Bankanbindungs-Modul, das wir später dazunehmen können.*

*Willst du gleich weiter, oder Pause?"*

## Nützliche Gewohnheiten

Belege gleich in den richtigen Monatsordner legen. Den Kontoauszug pro Monat als CSV und PDF ziehen. Am Monatsende kurz an Privatauslagen und Cash denken. Bei jedem neuen Beleg die Engine neu laufen lassen, statt "fertig" anzunehmen, Buchhaltung ist nie eingefroren.
