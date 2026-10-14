# Outlook Intel - CEO-GPT Module Installer

## Verbindlicher Standard für den Inhaltseingang · 1.1.1

**Vor der Einrichtung [reference/dateneingang.md](reference/dateneingang.md) lesen und anwenden.**
Empfohlen: Microsoft-Graph-Benachrichtigungen für freigegebene Postfächer und Kalender.

Diese Vorgabe ergänzt die bisherige Anleitung: automatische Übernahme der ausgewählten
Nachrichten und Termine gehört zur Grundeinrichtung. Frühere optionale Collector-Phasen
beschreiben nur noch zusätzliche Historienkopien; deren Zeitpläne sind kein Echtzeitnachweis.
Die Anleitung zur Quelle nennt nötige Ergänzungen und Grenzen. Keine KI-Schritte allein
für den Empfang einschalten; zusätzliche KI-Kosten vor Aktivierung erklären und Zustimmung
einholen. Bereits passende Zustimmung gilt weiter.

**Versionstyp: Installationsstandard korrigiert.** Kein mit dieser Dokumentversion
automatisch ausgerollter Echtzeitdienst; tatsächlichen Inhaltseingang im Zielsetup abnehmen.


<!-- MODULE METADATA
module: outlook-intel
version: 1.1.1
status: BETA
released: 2026-05-28
requires: []
phase: 3
category: Intelligence Extension
complexity: medium
api_keys: 0
setup_time: 30-40 minutes
note: Nutzt einen LOKAL GEBAUTEN + GEPATCHTEN Softeria-Build. Softeria v0.113.0 hat zwei
      bestaetigte Bugs (offline_access fehlt im Login-Scope; --read-only Scope-Mismatch),
      die ein npx-Install funktionsunfaehig machen. Siehe Step 2.
-->

---

## FOR CLAUDE

You are helping a user connect their Microsoft 365 (Outlook) mail and calendar (optional: Teams) to Claude via an MCP server. The setup uses the open-source **Softeria `ms-365-mcp-server`**, but **built locally from source with a small patch**, running LOCALLY (stdio), authenticated with the customer's OWN Microsoft Entra app registration. It supports MULTIPLE Microsoft accounts at once (one per company). Phase 1 = the live MCP server. Phase 2 (optional) = an email collector into the CEO-GPT database.

**WICHTIG - zwei bestaetigte Bugs in Softeria v0.113.0 (live verifiziert):**
1. **`offline_access` fehlt im Login-Scope.** Softeria baut die Login-Scopes aus den Tool-Scopes (`Mail.ReadWrite` etc.). `offline_access` ist ein OAuth-Sonder-Scope und landet NIE in der Liste. Ohne ihn gibt Microsoft KEINEN Refresh-Token. Folge: Login klappt, der Access-Token laeuft kurz danach aus, JEDER Tool-Call scheitert mit "expired". → Fix in Step 2: 3-Zeilen-Patch in `src/auth.ts`, der `offline_access` immer hinzufuegt.
2. **`--read-only` erzeugt Scope-Mismatch.** Read-only mappt `Mail.ReadWrite` runter auf `Mail.Read`. Der gecachte/granted Token hat aber `Mail.ReadWrite`. MSAL macht exact-match (kennt die Graph-Hierarchie `ReadWrite > Read` nicht) → "expired". → Fix: `--read-only` NIE verwenden. Schreibschutz kommt stattdessen aus den Entra-App-Permissions (kein `Mail.Send` granted = kein Senden moeglich, egal was Claude versucht).

Deshalb wird NICHT `npx` genutzt, sondern ein lokaler Build (Step 2). Sobald eine neuere Softeria-Version diese Bugs fixt, kann man wieder auf `npx -y @softeria/ms-365-mcp-server@<neue version>` umstellen.

**Behavior:**
- User ist non-technical, ausser er sagt was anderes. Jeden Schritt vorher in Klartext erklaeren.
- Kleine Wins feiern. Keine Error-Logs dumpen, Probleme einfach erklaeren und Fix vorschlagen.
- Verifikation nie ueberspringen. Der Entra-App-Schritt passiert im Browser, leite Klick fuer Klick an.
- IMMER `MS365_MCP_CLIENT_ID` auf die EIGENE Entra-App setzen. Ohne sie nutzt Softeria seine Default-App (= Abhaengigkeit, und keine eigenen Collectors/Automationen moeglich).
- Lokal, kein Hosting: stdio, vom Claude-Client gestartet, KEIN LaunchAgent in Phase 1.

---

## OVERVIEW

Read this to the user:

Wir verbinden dein **Outlook (Microsoft 365)** mit Claude. Wenn wir fertig sind:
- E-Mails lesen, durchsuchen, zusammenfassen, **Antwort-Entwuerfe** schreiben (du sendest selbst)
- Kalender lesen und managen, optional auch **Teams**-Nachrichten lesen
- ueber **mehrere Firmen** hinweg, in einem Setup, du sagst einfach welches Konto
- mit **deinem eigenen App-Schluessel**, **lokal**, kein Hosting, du haengst an niemandem

**Setup-Zeit:** 30-40 Minuten (inkl. lokalem Build). **Kosten:** 0 $. **Datenschutz:** Tokens bleiben lokal (macOS Keychain), der App-Schluessel gehoert dir.

---

## SCOPING

### Frage 1: Welche Microsoft-Konten?
"Welche Microsoft-365-Konten sollen ran? Gib mir die E-Mail-Adressen, eins pro Firma reicht."
Record: `ACCOUNTS = [list]`

### Frage 2: Welche Dienste? (steuert die Permissions)
"Was soll Claude koennen? Waehl aus: **E-Mail**, **Kalender**, **Teams** (Mehrfachauswahl). Danach richtet sich, welche Berechtigungen die App bekommt."
- **Mail** → `Mail.ReadWrite` (+ `Mail.Send` nur wenn Senden erlaubt)
- **Kalender** → `Calendars.ReadWrite`
- **Teams** → `Chat.Read` (1:1/Gruppen), optional `ChannelMessage.Read.All` + `Team.ReadBasic.All` (Kanaele, brauchen i.d.R. Admin-Consent)
Record: `SERVICES = [mail, calendar, teams]`

### Frage 3: Nur Entwuerfe oder auch senden? (nur falls Mail gewaehlt)
"Soll Claude Mails nur als **Entwurf** vorbereiten (du sendest selbst) oder auch direkt **senden**? Empfehlung: erst nur Entwuerfe."
- **A) Nur Entwuerfe** (empfohlen) → `Mail.Send` NICHT granten
- **B) Senden erlaubt** → `Mail.Send` mit granten
Record: `ALLOW_SEND = false | true`
Hinweis: Drafts-only wird ueber die **Entra-Permissions** erzwungen (kein Mail.Send), NICHT ueber ein `--read-only`-Flag (das ist in 0.113.0 kaputt).

### Frage 4: Welcher Claude-Client?
Record: `CLIENT = desktop | code | both`

### Frage 5: Phase 2 (E-Mail-Collector in die DB) jetzt oder spaeter?
Record: `DO_PHASE2 = later | now`

Zusammenfassen: "Plan: {n} Konten, Dienste {…}, {Entwuerfe-only | Senden erlaubt}, Client {…}, Collector {später | jetzt}. Passt?"

---

## PREREQUISITES

```bash
node --version    # >= 20, sonst: brew install node
git --version     # fuer den Softeria-Clone
```
- Claude-Client installiert (Desktop und/oder Code)
- Microsoft-365-Admin-Zugang in mindestens einem Tenant (App registrieren)
- CEO-GPT-Workspace (`ls CLAUDE.md`)

[VERIFY] Versionen ohne Fehler. "Alles da, los?"

---

## INSTALL (Phase 1 - der MCP-Server)

### Step 1: Eigene Microsoft-App registrieren (Entra)

"5 Minuten im Browser, kein Code. Die App gehoert dir."

1. https://entra.microsoft.com → **Identity → Applications → App registrations → New registration**.
2. **Name:** z.B. `CEO-GPT Outlook Connector`.
3. **Supported account types:** **"Accounts in any organizational directory (Any Microsoft Entra ID tenant - Multitenant)"**.
4. **Redirect URI:** leer lassen → **Register**.
5. **Application (client) ID** kopieren → `CLIENT_ID`. Record.
6. **Authentication → Advanced settings → Allow public client flows → Yes → Save.** (Pflicht fuer device-code.)
7. **API permissions → Add a permission → Microsoft Graph → Delegated permissions** → je nach `SERVICES` anhaken:
   - immer: `offline_access`, `User.Read`
   - Mail: `Mail.ReadWrite` (+ `Mail.Send` nur wenn `ALLOW_SEND = true`)
   - Kalender: `Calendars.ReadWrite`
   - Teams: `Chat.Read` (+ optional `ChannelMessage.Read.All`, `Team.ReadBasic.All`)
   → **Add permissions**.
8. Falls noetig: **Grant admin consent for [Org]** (ein Klick, User ist Admin). Teams-Channel-Scopes brauchen das fast immer.

`TENANT_ID = common` (deckt alle Firmen-Tenants ab).

[VERIFY] CLIENT_ID notiert, gewuenschte Permissions in der Liste, public client flows = Yes.

### Step 2: Softeria lokal bauen + patchen (wegen der 0.113.0-Bugs)

"Wir bauen den Server einmal selbst und setzen einen kleinen Fix, weil die fertige Version einen Token-Bug hat."

```bash
# tools/ aus Git heraushalten (Build + spaeter Tokens)
grep -qxF "tools/" .gitignore 2>/dev/null || echo "tools/" >> .gitignore

mkdir -p tools && cd tools
git clone --depth 1 --branch v0.113.0 https://github.com/softeria/ms-365-mcp-server.git ms-365-mcp 2>/dev/null \
  || git clone --depth 1 https://github.com/softeria/ms-365-mcp-server.git ms-365-mcp
cd ms-365-mcp
```

**Patch (Bug 1, offline_access):** In `src/auth.ts` im Konstruktor / dort wo die Login-Scope-Liste aus den Tool-Scopes gebaut wird, `offline_access` IMMER hinzufuegen. Konzeptionell:
```ts
// in src/auth.ts, beim Zusammenbauen der scopes-Liste fuer den Login:
const scopes = [ ...toolScopes ];
if (!scopes.includes('offline_access')) scopes.push('offline_access');
```
> Den exakten, erprobten 3-Zeilen-Patch hier 1:1 eintragen (vom Modul-Autor). Wenn unklar: nach der Stelle suchen, an der `acquireTokenByDeviceCode` / `initiateDeviceFlow` die `scopes` bekommt, und `offline_access` der Liste hinzufuegen.

Dann bauen:
```bash
npm install
npm run build      # erzeugt dist/index.js
ls dist/index.js   # muss existieren
```
[VERIFY] `node dist/index.js --help` zeigt die Hilfe (Flags gegenchecken: `--login`, `--list-accounts`, `--org-mode`).

Merke den absoluten Pfad: `SERVER_ENTRY = <WORKSPACE>/tools/ms-365-mcp/dist/index.js`.

### Step 3: Umgebung konfigurieren

```bash
export MS365_MCP_CLIENT_ID="<CLIENT_ID>"
export MS365_MCP_TENANT_ID="common"
```
**macOS-Hinweis:** Softeria legt die Tokens automatisch in der **Keychain** ab (keytar). Ein `MS365_MCP_TOKEN_CACHE_PATH` ist auf dem Mac NICHT noetig (die JSON-Datei wird gar nicht erst angelegt). Nur auf Systemen ohne Keychain (Linux ohne Secret-Service) einen Datei-Pfad in `data/` setzen.

**`.env`-Hinweis:** Werte mit Leerzeichen MUESSEN in Anfuehrungszeichen. `KEY=A B C` bricht beim `source`. Richtig: `KEY="A B C"`.

(Kein `MS365_MCP_ALLOWED_SCOPES` noetig. Der Schreibschutz kommt aus den Entra-Permissions, nicht aus einer Scope-Restriktion, das vermeidet den gleichen Mismatch wie `--read-only`.)

### Step 4: Konten verbinden (device-code)

Fuer JEDES Konto aus `ACCOUNTS`:
```bash
node tools/ms-365-mcp/dist/index.js --login --org-mode
```
(KEIN `--read-only`.) Es zeigt eine URL (microsoft.com/devicelogin) + einen Code. Sag dem User:
"Oeffne die Seite, gib den Code ein, melde dich mit dem Konto von **[Firma]** an, bestaetige den Zugriff."
Pro Firma wiederholen.

[VERIFY]
```bash
node tools/ms-365-mcp/dist/index.js --list-accounts
```
Erwartet: alle Konten gelistet. Danach ein schneller Token-Test:
```bash
node tools/ms-365-mcp/dist/index.js --list-mail-folders 2>/dev/null || echo "(falls Tool-Name abweicht: --help checken)"
```
Wenn das OHNE "expired" durchlaeuft, sitzt der offline_access-Patch.

### Step 5: MCP-Server in Claude registrieren

**Claude Desktop** (`~/Library/Application Support/Claude/claude_desktop_config.json`):
```json
{
  "mcpServers": {
    "ms365": {
      "command": "node",
      "args": ["<WORKSPACE>/tools/ms-365-mcp/dist/index.js", "--org-mode"],
      "env": {
        "MS365_MCP_CLIENT_ID": "<CLIENT_ID>",
        "MS365_MCP_TENANT_ID": "common"
      }
    }
  }
}
```
`<WORKSPACE>` absolut ersetzen. KEIN `--read-only` in den args. Den `"ms365"`-Key in vorhandenes `mcpServers` einfuegen, andere nicht ueberschreiben.

**Claude Code:**
```bash
claude mcp add ms365 -- node <WORKSPACE>/tools/ms-365-mcp/dist/index.js --org-mode
```
Env-Vars (`MS365_MCP_CLIENT_ID`, `MS365_MCP_TENANT_ID`) im Config-Eintrag sicherstellen.

Danach **Client neu starten.**

### Step 6: Verifizieren

```bash
cp module-installs/intelligenz-outlook/scripts/verify_outlook_pipeline.py scripts/intel/verify_outlook_pipeline.py 2>/dev/null || cp module-installs/intelligenz-outlook/scripts/verify_outlook_pipeline.py ./verify_outlook_pipeline.py
python3 scripts/intel/verify_outlook_pipeline.py 2>/dev/null || python3 ./verify_outlook_pipeline.py
```
Dann live in Claude: "Liste meine letzten 5 Outlook-Mails." / "Was steht heute im Kalender?" / bei mehreren Konten "...fuer konto@firma-b.com".

[VERIFY] Claude liefert echte Mails/Termine ueber die ms365-Tools, KEIN "expired".

---

## TEST

- **Pflicht-Verify:** `python3 scripts/intel/verify_outlook_pipeline.py` → "Verifikation erfolgreich".
- **Mail lesen:** "Zeig die letzten Mails von [Person] aus [Firma]."
- **Entwurf:** "Schreib [Person] einen kurzen Antwort-Entwurf." → Entwurf erscheint im echten Outlook, KEIN Versand.
- **Kalender:** "Was habe ich morgen?" + "Leg morgen 16 Uhr 'Fokus' (30 Min) an."
- **Teams (falls gewaehlt):** "Fass meine letzten Teams-Chats zusammen."
- **Nur wenn ALLOW_SEND:** Testmail an dich selbst.

Wenn alles laeuft: "Outlook Intel Phase 1 steht, lokal und unabhaengig."

---

## UPDATE CLAUDE.md

```markdown
## Outlook Intel - Microsoft 365 (MCP)

### MCP Server (live)
- Server: `ms365` (Softeria, LOKAL gebaut + gepatcht unter tools/ms-365-mcp/, Start via `node tools/ms-365-mcp/dist/index.js --org-mode`)
- Grund fuer lokalen Build: v0.113.0 Bugs (offline_access fehlt; --read-only Scope-Mismatch). offline_access-Patch in src/auth.ts.
- Auth: eigene Entra-App (Client-ID im Kunden-Tenant), delegated, device-code, multi-account. Tokens in macOS-Keychain.
- Dienste/Scopes: {Mail.ReadWrite | Calendars.ReadWrite | Chat.Read ...}{, Mail.Send falls Senden}
- Senden: {nur Entwuerfe | erlaubt} (gesteuert ueber Entra-Permissions, NICHT --read-only)
- Konten: {ACCOUNTS}; pro Call via `account`-Param waehlbar
- Konto neu einloggen: `node tools/ms-365-mcp/dist/index.js --login --org-mode`
- Konten listen: `node tools/ms-365-mcp/dist/index.js --list-accounts`

### Email Collector (Phase 2, falls aktiv)
- scripts/intel/collect_outlook.py → Tabelle `outlook_messages` in data/data.db (nur E-Mails)
- Schedule: alle {interval} via com.ceogpt.outlook-collect
```

---

## HOW TO USE IT

**Mail:** "Was kam diese Woche von [Name]?" · "Fass die ungelesenen Mails in [Firma] zusammen." · "Such Mails zum Thema [Projekt]."
**Entwuerfe:** "Schreib [Name] einen Antwort-Entwurf: sag zu, schlag Dienstag 15 Uhr vor."
**Kalender:** "Was steht morgen an?" · "Leg Donnerstag 10 Uhr einen Termin mit [Name] an." · "Wann habe ich naechste Woche 60 Min frei?"
**Teams (falls aktiv):** "Was lief in meinen Teams-Chats heute?"
**Mehrere Firmen:** "Zeig die Termine aus [Firma B] morgen." · "Antworte aus dem Konto von [Firma C]."

---

## TROUBLESHOOTING

### Jeder Tool-Call scheitert mit "expired" direkt nach dem Login
**Bug 1 (offline_access).** Microsoft gab keinen Refresh-Token, weil `offline_access` nicht im Login-Scope war. Den Patch in `src/auth.ts` setzen (Step 2), `npm run build`, ein Konto neu einloggen. Pruefen: `--list-mail-folders` darf nicht "expired" werfen.

### "expired" obwohl frisch eingeloggt, und `--read-only` ist gesetzt
**Bug 2 (Scope-Mismatch).** `--read-only` entfernen (aus den MCP-Args und allen Login-Aufrufen). Schreibschutz kommt aus den Entra-Permissions (kein Mail.Send = kein Senden).

### `.env` wirft Fehler beim Laden
Whitespace-Wert ohne Quotes. `KEY="A B C"` statt `KEY=A B C`.

### Token-Cache-Datei fehlt (macOS)
Kein Fehler. macOS nutzt die Keychain, die JSON-Datei wird nicht angelegt. `MS365_MCP_TOKEN_CACHE_PATH` auf dem Mac weglassen.

### Claude zeigt keine ms365-Tools
MCP-Config pruefen (Pfad auf `dist/index.js` korrekt, `env` vollstaendig, kein `--read-only`), Client neu starten. Bei Claude Code `claude mcp list`.

### Falsches Postfach antwortet
Bei mehreren Konten den `account`-Parameter mitgeben ("...fuer konto@firma-b.com"). `--list-accounts` zeigt die gueltigen Bezeichner.

### Flag/Tool-Name weicht ab
`node tools/ms-365-mcp/dist/index.js --help`. Stabil: `--login`, `--list-accounts`, `--org-mode`, Env-Vars `MS365_MCP_*`.

---

## PHASE 2 (optional, spaeter) - E-Mail-Collector in die Datenbank

Nur wenn `DO_PHASE2 = now`. Bringt E-Mails in `data/data.db` (Tabelle `outlook_messages`) fuer Suche + Daily Brief. **Nur E-Mails, kein Kalender.**

Der Collector authentifiziert sich selbst (eigener MSAL-Login mit DERSELBEN Client-ID, eigener Token-Cache), also pro Konto ein zweiter device-code-Login. Unvermeidbar, weil MCP-Server und Collector getrennte Prozesse sind.

```bash
pip install msal requests python-dotenv
cp module-installs/intelligenz-outlook/scripts/collect_outlook.py scripts/intel/collect_outlook.py
```
Die drei Werte (alle nicht geheim) ueber das Werkzeug setzen statt von Hand in die `.env` zu tippen. Stell sicher, dass `scripts/set_secret.py` im Workspace liegt (liegt diesem Modul bei), dann:
```bash
python scripts/set_secret.py MS365_MCP_CLIENT_ID --show
python scripts/set_secret.py MS365_MCP_TENANT_ID --show
python scripts/set_secret.py OUTLOOK_COLLECTOR_TOKEN_CACHE --show
```
```bash
python3 scripts/intel/collect_outlook.py --login     # Konto per device-code
python3 scripts/intel/collect_outlook.py --days 7    # Mails der letzten 7 Tage in die DB
```
[VERIFY] `python3 -c "import sqlite3;print('outlook_messages:', sqlite3.connect('data/data.db').execute('SELECT COUNT(*) FROM outlook_messages').fetchone()[0])"`

Zeitplan (macOS): Plist `config/com.ceogpt.outlook-collect.plist` mit Python befuellen (`__VENV_PYTHON__`, `__SCRIPTS_DIR__`, `__WORKSPACE_ROOT__`, `__INTERVAL__`) nach `~/Library/LaunchAgents/`, dann `launchctl load`.

---

## WHAT'S NEXT

1. **Daily Brief** - nach Phase 2 Outlook-Mail als Quelle aufnehmen.
2. **Senden freischalten** - wenn der User dem Entwurfs-Flow vertraut, `Mail.Send` in den Entra-Permissions ergaenzen (App-Permission, kein Flag).
3. **Zurueck auf npx** - sobald eine Softeria-Version die zwei Bugs fixt, kann der lokale Build durch `npx -y @softeria/ms-365-mcp-server@<version> --org-mode` ersetzt werden (App-Setup bleibt identisch).
4. **Corporate-GPT (ganze Firma)** - org-weiter Zugriff braucht app-only ueber den Companion `okapi-ca/ms-365-admin-mcp-server`, anderer Modus.
