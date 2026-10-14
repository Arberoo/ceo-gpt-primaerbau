# IMAP/SMTP Intel

> Beliebige Postfächer (jeder IMAP/SMTP-Anbieter) an Claude anbinden. Erst durchleuchten, was da liegt, dann alles rückwirkend lokal extrahieren, dazu Live-Zugriff per MCP. Lesen, suchen, Entwürfe, senden.

## What This Does

Drei Stufen:

1. **Durchleuchten** (`discover_imap.py`): Welche Server, welche Ordner, wie viele Mails, welche Spezial-Ordner, welcher Zeitraum. Du siehst die Landschaft, bevor irgendetwas gezogen wird. Markiert nichts als gelesen.
2. **Rückwirkend lokal extrahieren** (`collect_imap.py`): Alle Mails aller Ordner in die CEO-GPT-Datenbank, wiederaufnehmbar, mit Vollständigkeits-Check. Das Setup gilt erst als fertig, wenn alles lokal ist.
3. **Live per MCP** (`mcp-email-server`): lesen, suchen, Entwürfe schreiben, senden, direkt aus Claude.

- **Dein eigener Zugang, lokal:** Server-Daten in einer Config, Passwörter in der `.env`, nichts verlässt deinen Mac.
- **Mehrere Konten** in einem Setup.
- **Entwürfe by default:** Senden ist ein bewusster Schalter.

## What You Need

- Ein Mac
- **`uv`** (liefert `uvx`, startet den MCP-Server): `brew install uv`
- **Python 3.10+** plus `imap-tools` und `IMAPClient` (für Durchleuchten und Backfill)
- Ein oder mehrere **IMAP/SMTP-Postfächer**. Auth: **App-Passwort** (mit 2FA) für die meisten Anbieter. Microsoft 365 braucht 2026 **OAuth2/XOAUTH2** (Basic-Auth wird abgeschaltet).
- Ein Claude-Client (Code oder Desktop)
- CEO-GPT-Workspace

## How to Install

1. Pack diesen Ordner in dein CEO-GPT
2. Sag zum Mitarbeiter: "Lies INSTALL.md und richte das ein"
3. Folge der geführten Installation (Konten anlegen, durchleuchten, extrahieren, MCP)

## Running Cost

- MCP-Server (`mcp-email-server`, Open Source) und `imap-tools`: kostenlos, lokal
- IMAP/SMTP: im Postfach-Tarif enthalten
- **Total: 0 $/Monat**

## What's Inside

| Datei | Zweck |
|------|---------|
| `INSTALL.md` | Geführte Installation (liest der Mitarbeiter) |
| `scripts/imap_common.py` | Gemeinsame Helfer: Konten-Config, Verbindung, DB-Schema |
| `scripts/discover_imap.py` | Stufe 1: Postfächer durchleuchten |
| `scripts/collect_imap.py` | Stufe 2: rückwirkende Voll-Extraktion, resumable, Vollständigkeits-Check |
| `scripts/verify_imap_pipeline.py` | Pflicht-Verify (Config, Pakete, Login-Test) |
| `scripts/imap-mcp-run.sh` | Wrapper: gibt dem MCP-Server die `.env`-Zugangsdaten mit |
| `config/com.ceogpt.imap-collect.plist` | Zeitplan für den Sammler |

## Architecture

```
        beliebige IMAP/SMTP-Server (Cloud / eigener Host)
           ▲                          ▲
  live     │ (Server-Daten aus        │ Discovery + Voll-Backfill
           │  config + .env)          │
           ▼                          ▼
  mcp-email-server (uvx, lokal)   discover_imap.py / collect_imap.py
           ▲                          │ schreibt
  Claude   │                          ▼
           ▼                    data.db (mail_accounts, mail_folders,
  Claude Code / Desktop          mail_messages, mail_discovery)
                                       │
                                       ▼
                              Daily Brief / SQL-Suche
```

**Konten-Config:** `config/imap-accounts.json` (Server, Port, Username, Provider, kein Passwort). **Secrets:** verdeckt über `python scripts/set_secret.py KEY` in die `.env` (`IMAP_PW_<LABEL>` für den Sammler, `MCP_EMAIL_SERVER_PASSWORD` für den Live-Server; Host/Port/Adresse als harmlose Config mit `--show`). Nie im Repo, nie in der Datenbank, KI tippt sie nie selbst.

## Inhaltseingang

IMAP IDLE je freigegebenem Postfach/Ordner mit direktem Abruf neuer Inhalte.

Einrichtungsstandard und Grenzen: [reference/dateneingang.md](reference/dateneingang.md).
Dieses Patch-Update korrigiert die Installationsvorgaben; zusätzliche Dienste werden
dadurch nicht automatisch eingerichtet. KI-Schritte sind separat zu aktivieren.
