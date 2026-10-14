# Anpassungen für Windows (PrimärBau / MUBA, 15.10.2026)

Abweichungen von INSTALL.md, weil dieses CEO-GPT auf Windows 11 läuft und nur die MUBA Service GmbH angebunden wird. Betrieb: `docs/mail-muba-graph.md`.

| Original (Mac) | Hier auf Windows | Grund |
|---|---|---|
| `brew install node` | `winget install OpenJS.NodeJS.LTS` (Node 24), Starter nutzt `C:\Program Files\nodejs\node.exe` | kein Homebrew |
| Build: `npm install && npm run build` | zusätzlich **`npm run generate`** vor dem Build (lädt die Graph-OpenAPI von github.com/microsoftgraph und erzeugt `src/generated/client.ts`) | ohne fehlt `dist/generated/client.js` |
| offline_access-Patch „konzeptionell“ | konkret in `tools/ms-365-mcp/src/auth.ts`, Konstruktor `AuthManager`: `this.scopes = scopes.includes('offline_access') ? scopes : [...scopes, 'offline_access'];` (Kommentar „CEO-GPT-Patch“) | Bug 1 aus INSTALL.md |
| Entra-App „Multitenant“, Tenant `common` | **Einzelmandant** „Nur MUBA Service GmbH“, `MS365_MCP_TENANT_ID` = MUBA-Mandanten-ID | nur ein Tenant nötig, kleinere Angriffsfläche |
| Rechte Mail + Kalender (+ Teams) | nur `User.Read`, `offline_access`, `Mail.ReadWrite` (delegiert, Admin-Zustimmung erteilt 15.10.2026). **Kein `Mail.Send`** | Leitregel: nur Lesen und Entwürfe |
| `claude mcp add ms365 … --org-mode` | `.mcp.json` → `mail_muba` → `scripts/intel/ms365_mcp_run.py`, der `--org-mode --enabled-tools <Liste>` setzt | nur Lese- und Entwurfswerkzeuge sichtbar; Login und Betrieb nutzen dieselbe Liste (gleiche Scopes) |
| Tokens in der macOS-Keychain | Windows-Anmeldeinformationsverwaltung (keytar, vorgebaut) | Windows-Gegenstück |
| `export MS365_MCP_CLIENT_ID …` | Kennungen in `.env` (`MS365_MCP_CLIENT_ID`, `MS365_MCP_TENANT_ID`), gesetzt über `scripts/muba_postfach_anmelden.ps1` | ein Weg für alle Zugänge |
| Kontoverwaltungs-Werkzeuge (login/logout/remove-account) | in `.claude/settings.local.json` verboten | Anmeldung nicht versehentlich verlieren |
| Phase 2 Collector (LaunchAgent) | noch nicht eingerichtet | zuerst Sicherung (Purview) und Klärung Insolvenzverwalter |
