# Mail-Zugriff MUBA (Microsoft 365, Graph)

> Eingerichtet in der Nacht zum 15.10.2026 (Arber). Der Mitarbeiter liest die MUBA-Postfächer direkt bei Microsoft, ohne Outlook. Das funktioniert in jeder Sitzung, auch per SSH.

## Überblick

- **Entra-App** im MUBA-Mandanten: „CEO-GPT PrimaerBau Mail“, nur dieser Mandant, Anwendungs-ID `fd0a6d4e-5c52-413e-a839-2e1b5e4e7965`, Mandant `db85f637-1f68-4796-aaae-199db56428d4`. Angelegt von Luljetas Konto (Globaler Administrator).
- **Rechte (delegiert, Admin-Zustimmung erteilt):** `User.Read`, `offline_access`, `Mail.ReadWrite`. **Kein `Mail.Send`**: Senden ist bei Microsoft gar nicht erlaubt.
- **Baustein:** Softeria `ms-365-mcp-server` v0.113.0, lokal gebaut und gepatcht in `tools/ms-365-mcp/` (geht nicht zu GitHub). Gestartet über `scripts/intel/ms365_mcp_run.py` (MCP-Server `mail_muba` in `.mcp.json`).
- **Werkzeuge für den Mitarbeiter:** Mails, Ordner und Unterordner auflisten, Mail lesen, Anhänge auflisten, Entwurf / Antwort-Entwurf / Antwort-an-alle-Entwurf anlegen, **Entwürfe ändern** (`update-mail-message`, z. B. Empfänger, CC, Text) und **Entwürfe löschen** (`delete-mail-message`, verschiebt nach „Gelöschte Elemente“). Ändern und Löschen gehen **nur bei Entwürfen**: Der gepatchte Server holt vorher `isDraft` und lehnt alles andere ab (Patch in `tools/ms-365-mcp/src/graph-tools.ts`, Kommentar „CEO-GPT PrimaerBau“; nach einem Update von Softeria neu einbauen). Abmelden und Konto-Entfernen sind verboten.
- **Anmeldung** liegt in der Windows-Anmeldeinformationsverwaltung.

## Angemeldete Postfächer

| Postfach | Stand |
|---|---|
| l.bajraktari@muba-service-gmbh.de | angemeldet 15.10.2026, Lesen getestet |
| info@muba-service-gmbh.de | eigenes Konto, angemeldet 15.10.2026, Lesen getestet |

Bei mehreren Postfächern im Werkzeug immer `account` angeben (z. B. `"account": "info@muba-service-gmbh.de"`). Ohne Angabe gilt das als „selected“ markierte Postfach (l.bajraktari@).

## Pflege

- Weiteres Postfach anmelden: `powershell -ExecutionPolicy Bypass -File scripts\muba_postfach_anmelden.ps1`, Code auf microsoft.com/devicelogin eingeben.
- Angemeldete Postfächer: `.venv\Scripts\python.exe scripts\intel\ms365_mcp_run.py --list-accounts`
- Werkzeuge erweitern: Liste `ERLAUBT` in `scripts/intel/ms365_mcp_run.py`. **Danach neu anmelden**, weil sich die angeforderten Rechte ändern.
- Werkzeuge fehlen in Claude: Sitzung neu starten.
- Fehler „expired“ direkt nach dem Login: Patch in `tools/ms-365-mcp/src/auth.ts` prüfen, neu bauen (`npm run generate`, `npm run build`).

## Wichtig

- Für die MUBA ist ein **Insolvenzantrag** gestellt. Die App wurde auf Arbers Entscheidung hin angelegt. Mit dem Insolvenzverwalter abklären, dass das in Ordnung ist. Entfernen: Entra → App-Registrierungen → „CEO-GPT PrimaerBau Mail“ → Löschen.
- Funktioniert nur, solange der MUBA-Mandant besteht. Die Sicherung (`docs/muba-postfaecher-sichern.md`) ist davon unabhängig und hat Vorrang.

## History

| Datum | Änderung |
|---|---|
| 2026-10-15 | Eingerichtet, l.bajraktari@ angemeldet, Lesen getestet |
| 2026-10-17 | Entwürfe ändern und löschen freigeschaltet (nur isDraft, Arber). Rechte unverändert (Mail.ReadWrite), kein neuer Login nötig |
