# IMAP/SMTP Intel - CEO-GPT Module Installer

## Verbindlicher Standard für den Inhaltseingang · 1.0.1

**Vor der Einrichtung [reference/dateneingang.md](reference/dateneingang.md) lesen und anwenden.**
Empfohlen: IMAP IDLE je freigegebenem Postfach/Ordner mit direktem Abruf neuer Inhalte.

Diese Vorgabe ergänzt die bisherige Anleitung: automatische Übernahme der ausgewählten
Nachrichten und Termine gehört zur Grundeinrichtung. Frühere optionale Collector-Phasen
beschreiben nur noch zusätzliche Historienkopien; deren Zeitpläne sind kein Echtzeitnachweis.
Die Anleitung zur Quelle nennt nötige Ergänzungen und Grenzen. Keine KI-Schritte allein
für den Empfang einschalten; zusätzliche KI-Kosten vor Aktivierung erklären und Zustimmung
einholen. Bereits passende Zustimmung gilt weiter.

**Versionstyp: Installationsstandard korrigiert.** Kein mit dieser Dokumentversion
automatisch ausgerollter Echtzeitdienst; tatsächlichen Inhaltseingang im Zielsetup abnehmen.


<!-- MODULE METADATA
module: imap-intel
version: 1.0.1
status: BETA
released: 2026-06-03
requires: []
phase: 3
category: Intelligence Extension
complexity: medium-high
api_keys: 1+ pro Konto (IMAP/SMTP-Passwort in .env)
setup_time: 30-45 minutes (haengt von der Postfach-Groesse beim Backfill ab)
note: Drei Stufen: durchleuchten -> rueckwirkend lokal extrahieren -> live per MCP.
      Live-Server = ai-zerolab/mcp-email-server via uvx (lokal, Wrapper liest .env).
      Sammler = eigener imap-tools-Collector, resumable ueber UID+UIDVALIDITY.
      Default Entwuerfe; Senden ist ein Schalter. M365 braucht XOAUTH2 (2026), v1 deckt
      App-Passwort-Provider ab.
-->

---

## FOR CLAUDE

You are helping a user connect arbitrary **IMAP/SMTP mailboxes** to Claude, mirroring the Google module but at the raw-protocol level. Three stages: **discover** (illuminate what's there), **backfill** (pull everything into the local DB, resumable, complete-or-not gate), **live MCP** (read/draft/send via `ai-zerolab/mcp-email-server`).

**Kernprinzipien:**
- **Durchleuchten zuerst.** Immer erst `discover_imap.py` laufen lassen und dem User die Landschaft zeigen (Server, Ordner, Mengen), bevor extrahiert wird. Das ist explizit so gewuenscht.
- **Vollstaendig heisst vollstaendig.** `collect_imap.py` ist erst "fertig", wenn der Vollstaendigkeits-Check gruen ist (lokal >= Server pro Ordner). Exit 2 = nochmal laufen (resumiert sauber).
- **Read-only Extraktion.** Sammler und Discovery markieren NICHTS als gelesen (`BODY.PEEK`/`mark_seen=False`).
- **Wrapper Pflicht bei Claude Code.** Wie beim Google-Modul startet Claude Code `uvx` aus dem Cache-Verzeichnis, der MCP-Server findet die `.env` nicht selbst. Darum `scripts/intel/imap-mcp-run.sh` (exportiert nur `MCP_EMAIL_SERVER_*` aus der `.env`), `.mcp.json` `command` zeigt darauf. PRIMAERER Weg, nicht Fallback.
- **`.env`-Regel (Hook):** NIE Passwoerter im Chat erfragen, NIE `.env` lesen. Geheimnisse gehen verdeckt ueber `python scripts/set_secret.py KEY`; KI liest/tippt sie nie selbst, fragt sie nie im Chat ab. Stelle vor dem ersten `set_secret.py`-Befehl sicher, dass `scripts/set_secret.py` existiert (Schritt "Eingabe-Werkzeug sicherstellen"), kopiere es nur falls es fehlt.
- **Default Entwuerfe.** Senden nur, wenn der User es will (beim MCP-Server: SMTP konfigurieren = senden moeglich; SMTP weglassen = read-only).
- **Auth 2026:** App-Passwort (mit 2FA beim Anbieter) ist der Standard-Einstieg. **Microsoft 365 braucht XOAUTH2** (Basic-Auth/App-Passwoerter sterben Maerz-April 2026), das ist ein v2-Thema, hier ehrlich ansagen statt mit Basic-Auth zu basteln.

**Behavior:** User non-technical. Schritt fuer Schritt erklaeren, kleine Wins feiern, keine Error-Logs dumpen. Verify nie ueberspringen.

---

## OVERVIEW

Read this to the user:

Wir binden deine **Postfächer** an Claude an, egal bei welchem Anbieter. Wenn wir fertig sind:
- Wir haben zuerst **durchleuchtet**, welche Server und Ordner es gibt und wie viel da liegt.
- Deine **komplette Mail-Historie liegt lokal** in der CEO-GPT-Datenbank, durchsuchbar.
- Claude kann **live** lesen, suchen, Entwürfe schreiben, optional senden.
- Alles **lokal**, Passwörter in der `.env`, nichts verlässt deinen Mac.

**Setup-Zeit:** 30-45 Minuten (Backfill je nach Postfach-Größe). **Kosten:** 0 $.

---

## SCOPING

### Frage 1: Welche Postfächer?
"Welche Postfächer sollen rein? Pro Konto brauche ich: Anbieter, IMAP-Server + Port, SMTP-Server + Port, Benutzername. Das App-Passwort legst du später verdeckt über `set_secret.py` ab, ich sehe es nie."
Record: `ACCOUNTS = [{label, imap_host, imap_port, smtp_host, smtp_port, username, provider}]`

### Frage 2: Senden oder nur Entwürfe?
"Soll Claude nur **lesen + Entwürfe** können, oder auch **senden**? Empfehlung: erst ohne Senden."
- Nur lesen/Entwürfe → beim MCP-Server SMTP NICHT konfigurieren.
- Senden → SMTP konfigurieren.
Record: `ALLOW_SEND = false | true`

### Frage 3: Gmail/Workspace dabei?
Wenn ein Konto Gmail/Workspace ist und schon über das Google-Modul läuft, hier i.d.R. weglassen (Doppelung). Falls doch via IMAP: `provider: "gmail"` setzen (dann zieht der Sammler nur All Mail + Spam + Trash, um Label-Dubletten zu vermeiden).

Zusammenfassen: "Plan: {n} Konten {…}, {nur Entwürfe | senden}. Passt?"

---

## PREREQUISITES

```bash
uv --version       # liefert uvx; sonst brew install uv
python3 --version  # >= 3.10
```
- Claude-Client (Code und/oder Desktop)
- Pro Konto ein **App-Passwort** (beim Anbieter erstellen, meist 2FA nötig)
- CEO-GPT-Workspace (`ls CLAUDE.md`)

[VERIFY] `uv` da, Workspace erkannt.

---

## INSTALL

### Step 1: Skripte + Pakete + Konten-Config

```bash
mkdir -p scripts/intel
cp module-installs/intelligenz-imap/scripts/*.py scripts/intel/
cp module-installs/intelligenz-imap/scripts/imap-mcp-run.sh scripts/intel/
chmod +x scripts/intel/imap-mcp-run.sh
.venv/bin/pip install imap-tools IMAPClient python-dotenv
```

Konten-Datei anlegen (nicht geheim, nur Server-Daten). `config/imap-accounts.json`:
```json
[
  {
    "label": "info",
    "imap_host": "imap.deinhost.de", "imap_port": 993, "imap_ssl": true,
    "smtp_host": "smtp.deinhost.de", "smtp_port": 465,
    "username": "info@deinedomain.de",
    "provider": "generic",
    "password_env": "IMAP_PW_INFO"
  }
]
```
Config-Datei vor Git schützen:
```bash
grep -qxF "config/imap-accounts.json" .gitignore 2>/dev/null || echo "config/imap-accounts.json" >> .gitignore
```
**Eingabe-Werkzeug sicherstellen (nur falls es fehlt):**
```bash
[ -f scripts/set_secret.py ] || cp module-installs/intelligenz-imap/scripts/set_secret.py scripts/set_secret.py
```
Nur falls `scripts/set_secret.py` noch nicht da ist (ältere Setups), wird es angelegt; ein vorhandenes bleibt unangetastet.

App-Passwort verdeckt hinterlegen (nichts erscheint auf dem Schirm, landet direkt in der `.env`), pro Postfach ein eigener Schlüssel `IMAP_PW_<LABEL>`:
```bash
python scripts/set_secret.py IMAP_PW_INFO
```

[VERIFY] `config/imap-accounts.json` gültig, Passwörter in `.env` gesetzt.

### Step 2: Verify

```bash
python3 scripts/intel/verify_imap_pipeline.py
```
Prüft Config, Pakete, und macht einen Login-Test je Konto (zählt Ordner). 

[VERIFY] Jedes Konto "OK, N Ordner erreichbar".

### Step 3: Durchleuchten (Stufe 1)

```bash
python3 scripts/intel/discover_imap.py
```
Zeigt pro Konto: Capabilities, alle Ordner mit Rolle, Anzahl, ungelesen, Zeitraum. Lies dem User die Übersicht vor: "Hier liegen deine Server und Ordner, so viel ist drin." Der Stand landet in `data/data.db` (`mail_discovery`).

[VERIFY] Ordner-Übersicht erscheint, plausible Zahlen.

### Step 4: Rückwirkend alles lokal (Stufe 2)

```bash
python3 scripts/intel/collect_imap.py
```
Zieht alle Ordner aller Konten, resumable. Bei großen Postfächern dauert es, ggf. im Hintergrund laufen lassen und erneut starten, bis es **VOLLSTÄNDIG** meldet (Exit 0). Exit 2 = noch Lücken, einfach nochmal.

[VERIFY] "VOLLSTÄNDIG: alle Mails aller Ordner liegen lokal." Gegencheck:
```bash
.venv/bin/python -c "import sqlite3;c=sqlite3.connect('data/data.db');print('mails lokal:',c.execute('SELECT COUNT(*) FROM mail_messages').fetchone()[0])"
```

### Step 5: Live-Server (MCP)

Zugangsdaten für den Live-Server setzen (Single-Account-Variante). Das einzige Geheimnis ist das Passwort, verdeckt:
```bash
python scripts/set_secret.py MCP_EMAIL_SERVER_PASSWORD
```
Die übrigen Werte sind keine Geheimnisse (Adresse, Host, Port), offen mit `--show`:
```bash
python scripts/set_secret.py MCP_EMAIL_SERVER_EMAIL_ADDRESS --show
python scripts/set_secret.py MCP_EMAIL_SERVER_IMAP_HOST --show
python scripts/set_secret.py MCP_EMAIL_SERVER_IMAP_PORT --show
python scripts/set_secret.py MCP_EMAIL_SERVER_SMTP_HOST --show
python scripts/set_secret.py MCP_EMAIL_SERVER_SMTP_PORT --show
```
Für read-only: `MCP_EMAIL_SERVER_SMTP_HOST`/`MCP_EMAIL_SERVER_SMTP_PORT` weglassen, dann verschwinden die Sende-Tools. Mehrere Konten: stattdessen die TOML-Config des Servers nutzen (`~/.config/zerolib/mcp_email_server/config.toml`).

Wrapper-Pfad setzen (`__WORKSPACE__` ersetzen):
```bash
sed -i '' "s|__WORKSPACE__|$(pwd)|g" scripts/intel/imap-mcp-run.sh
```
`.mcp.json` Eintrag (Server `command` zeigt auf den Wrapper, kein Geheimnis in der Datei):
```json
{
  "mcpServers": {
    "imap_email": {
      "command": "<WORKSPACE>/scripts/intel/imap-mcp-run.sh",
      "args": ["mcp-email-server@latest", "stdio"]
    }
  }
}
```
`<WORKSPACE>` absolut ersetzen. Andere Server-Einträge nicht überschreiben. Danach Client neu starten bzw. `/mcp` neu verbinden.

[VERIFY] In Claude: "Liste die Postfächer / zeig die letzten Mails aus [Konto]." Echte Daten, kein Fehler.

---

## TEST

- `python3 scripts/intel/verify_imap_pipeline.py` → grün.
- Discovery zeigt deine Ordner.
- Backfill meldet VOLLSTÄNDIG.
- Live in Claude: "Letzte 5 Mails aus [Konto]", "Schreib einen Entwurf an [X]".
- Nur wenn ALLOW_SEND: Testmail an dich selbst.

---

## UPDATE CLAUDE.md

```markdown
## IMAP/SMTP Intel

### Live (MCP)
- Server: `imap_email` (ai-zerolab/mcp-email-server via uvx, Wrapper scripts/intel/imap-mcp-run.sh, Creds aus .env MCP_EMAIL_SERVER_*)
- Senden: {nur Entwürfe | erlaubt}

### Sammler + Discovery
- scripts/intel/discover_imap.py (durchleuchten) · scripts/intel/collect_imap.py (Voll-Backfill, resumable)
- Konten: config/imap-accounts.json, Passwörter .env (IMAP_PW_*)
- Tabellen in data/data.db: mail_accounts, mail_folders, mail_messages, mail_discovery
- Schedule: com.ceogpt.imap-collect (falls aktiv)
```

---

## HOW TO USE IT

**Suche lokal (DB):** "Such alle Mails von [Person] aus 2025." · "Was kam in [Ordner]?"
**Live:** "Zeig die letzten Mails aus [Konto]." · "Schreib [X] einen Entwurf." · "Fass den Thread mit [Y] zusammen."

---

## TROUBLESHOOTING

### Login schlägt fehl
App-Passwort statt normalem Passwort nutzen (beim Anbieter erstellen, meist 2FA Pflicht). Host/Port prüfen (IMAP 993 SSL, SMTP 465 SSL oder 587 STARTTLS).

### Microsoft 365 / Outlook geht nicht mit Passwort
M365 schaltet Basic-Auth + App-Passwörter 2026 ab, IMAP/SMTP brauchen dort **OAuth2/XOAUTH2**. Das ist v2 dieses Moduls, nicht mit Basic-Auth erzwingen.

### Backfill meldet nie VOLLSTÄNDIG
Erneut laufen lassen (resumiert). Bleibt eine kleine Lücke: einzelne Mails können zwischen Auflisten und Laden gelöscht worden sein. Bei UIDVALIDITY-Reset zieht der Sammler den Ordner automatisch neu.

### Gmail zieht alles doppelt
`provider: "gmail"` im Konto setzen, dann nur All Mail + Spam + Trash.

### MCP-Server findet die Zugangsdaten nicht
Wrapper als `command` gesetzt und `__WORKSPACE__` ersetzt? `MCP_EMAIL_SERVER_*` in der `.env` gefüllt? Client neu gestartet?

### Claude zeigt keine imap_email-Tools
`.mcp.json` prüfen, Client neu starten, bei Claude Code `claude mcp list`.

---

## WHAT'S NEXT

1. **Zeitplan** - `config/com.ceogpt.imap-collect.plist` füllen (`__VENV_PYTHON__`, `__SCRIPTS_DIR__`, `__WORKSPACE_ROOT__`, `__INTERVAL__`) nach `~/Library/LaunchAgents/`, `launchctl load`.
2. **Daily Brief** - `mail_messages` als Quelle in `briefing.py`/`prompt.py` aufnehmen.
3. **XOAUTH2** - für Microsoft 365 und als sicherere Gmail-Variante (statt App-Passwort).
4. **Voll-Body/Roh-Mail** - bei Bedarf body_text/html + .eml-Rohdaten zusätzlich ablegen (v1 speichert Metadaten + Snippet).
5. **Senden freischalten** - SMTP im MCP-Server konfigurieren, wenn dem Entwurfs-Flow vertraut wird.
