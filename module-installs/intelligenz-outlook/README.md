# Outlook Intel

> Deine Outlook-Mails und Kalender, live durch Claude. Lesen, suchen, Entwürfe schreiben, Termine managen, über mehrere Microsoft-365-Firmen hinweg. Optional: E-Mails in deine CEO-GPT-Datenbank ziehen.

## What This Does

- **Live Mail, Kalender und optional Teams durch Claude** über den Microsoft-365-MCP-Server (Softeria, Open Source, lokal gebaut + gepatcht)
- **Dein eigener Microsoft-App-Schlüssel** (Entra-App in DEINEM Tenant) - keine Abhängigkeit von uns und nicht von Softerias App
- **Multi-Account** - mehrere Microsoft-365-Konten (z.B. eins pro Firma) in einem Server, pro Anfrage wählbar
- **Entwürfe by default** - Claude schreibt Entwürfe, du sendest selbst (Senden ist opt-in)
- **Phase 2 (optional)** - ein Collector zieht deine E-Mails in die CEO-GPT-Datenbank für Suche + Daily Brief

## What You Need

- Ein Mac (dieses Modul zielt auf macOS / eine Always-on-Maschine wie einen iMac)
- **Node.js 20+** und **git** (für den lokalen Build des MCP-Servers, siehe INSTALL.md Step 2)
- Ein Claude-Client (Claude Desktop oder Claude Code)
- Ein oder mehrere **Microsoft-365-Konten** (Business/Work)
- **Admin-Rechte in mindestens einem Microsoft-365-Tenant**, um einmalig eine App zu registrieren (5-Minuten-Schritt)
- Python 3.10+ (nur für den Phase-2-Collector)
- CEO-GPT-Workspace (für Phase 2 + CLAUDE.md-Update)

## How to Install

1. Pack diesen Ordner in dein CEO-GPT
2. Sag zum Mitarbeiter: "Lies INSTALL.md und richte das ein"
3. Folge der geführten Installation

**Install-Ort des MCP-Servers:** `tools/ms-365-mcp/` im Workspace (lokaler Build, von `.gitignore` geschützt). Tokens liegen auf macOS in der Keychain, nicht im Repo.

**Wichtig:** Softeria v0.113.0 hat zwei Token-Bugs (offline_access fehlt im Login-Scope, `--read-only` Scope-Mismatch). Das Modul nutzt deshalb einen lokal gebauten + gepatchten Build statt `npx`. Details + Patch in INSTALL.md Step 2.

**Geschätzte Setup-Zeit:** 30-40 Minuten (Phase 1, inkl. lokalem Build)

## Running Cost

- **MCP-Server (Softeria):** kostenlos, Open Source, läuft lokal
- **Microsoft Graph API:** im M365-Abo enthalten, keine Extrakosten
- **Total: 0 $/Monat**

## What's Inside

| Datei | Zweck |
|------|---------|
| `INSTALL.md` | Geführte Installation (liest der Mitarbeiter) |
| `scripts/verify_outlook_pipeline.py` | Verifikations-Skript (Pflicht-Lauf nach Phase 1) |
| `scripts/collect_outlook.py` | E-Mail-Collector für die DB (Phase 2, optional) |
| `config/com.ceogpt.outlook-collect.plist` | macOS LaunchAgent für den Collector-Cron (Phase 2) |

## Architecture

```
              Microsoft 365 (Cloud, Graph API)
               ▲                         ▲
 live Mail+Kal │ (dein Entra-App-        │ Mail-Pull (Phase 2)
               │  Schlüssel)             │
               ▼                         ▼
     ms-365-mcp-server            collect_outlook.py
     (Softeria, lokal, stdio)     (Cron, Phase 2)
               ▲                         │ schreibt
   Claude nutzt│                         ▼
               ▼                   data.db (CEO-GPT)
     Claude Desktop / Code               │
                                         ▼
                               Daily Brief / SQL-Suche
```

**Zwei Zugriffspfade (wie bei WhatsApp Intel):**
- **MCP-Server → Claude** - live: Mail lesen/suchen, Entwürfe, Kalender managen (real-time, on demand)
- **Collector → Datenbank** - historische Mail-Suche, Daily Brief (Phase 2, Cron, nur E-Mails)

**Kein lokaler Bridge-Dienst nötig:** anders als bei WhatsApp ist Microsoft Graph die immer-laufende Cloud-API. Der MCP-Server wird vom Claude-Client bei Bedarf gestartet (stdio), es läuft kein KeepAlive-Hintergrunddienst.

## Inhaltseingang

Microsoft-Graph-Benachrichtigungen für freigegebene Postfächer und Kalender.

Einrichtungsstandard und Grenzen: [reference/dateneingang.md](reference/dateneingang.md).
Dieses Patch-Update korrigiert die Installationsvorgaben; zusätzliche Dienste werden
dadurch nicht automatisch eingerichtet. KI-Schritte sind separat zu aktivieren.
