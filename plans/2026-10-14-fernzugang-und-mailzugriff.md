# Plan: Mailzugriff beim Anbieter und Fernzugang

**Status:** Entwurf (Entscheidungen stehen, Umsetzung offen)
**Angelegt:** 14.10.2026, Entscheidungen von Arber
**Umsetzen mit:** `/implement plans/2026-10-14-fernzugang-und-mailzugriff.md`, Teil für Teil

---

## Entscheidungen (Arber, 14.10.2026)

1. **Mails werden direkt beim Anbieter gelesen, nicht über das Outlook-Programm.** Damit funktioniert der Zugriff in jeder Sitzung (auch per SSH von Edona oder Arber) und nachts ohne angemeldeten Bildschirm.
   - **PrimärBau (HostedOffice AG):** l.bajraktari@, info@, rechnung@primaerbau.com → Modul `intelligenz-imap`
   - **MUBA Service GmbH (Microsoft 365):** l.bajraktari@, info@ (ggf. a./e./m.) muba-service-gmbh.de → Modul `intelligenz-outlook` (Microsoft Graph, eigene Entra-App im MUBA-Tenant, Admin-Zugang hat Arber)
   - Bis das läuft, bleibt der Zugriff über das Outlook-Programm (COM) der Rückfall, siehe `docs/mail-zugriff-outlook.md`.
2. **Tailscale bekommt ein eigenes, kostenloses Konto für PrimärBau**, nicht Arbers Konto. Nur Luljetas PC (MUBA-PC2) kommt in dieses Netz. Arber bekommt den PC über Tailscales **„Teilen“** (Node Sharing) in sein eigenes Netz freigegeben. Arber erreicht damit den PC, der PC kommt aber nicht an Arbers Netz.
3. **Edona braucht kein Tailscale.** Ihr PC steht im selben Büro, sie verbindet sich über das Büronetz per SSH auf MUBA-PC2.
4. **Der Fernzugang (Weg N, Modul `remote-windows`) wird heute noch nicht eingerichtet.** Das Skript `module-installs/remote-windows/scripts/weg-n-einrichten.ps1` liegt bereit, ist aber noch nicht gelaufen.
5. **Reihenfolge:** zuerst die MUBA-Postfächer sichern (läuft seit 14.10. abends), dann der Mailzugriff beim Anbieter, dann der Fernzugang.

## Befunde vom 14.10.2026

**Windows-Anmeldung (MUBA-PC2, Konto „Muba“):**
- Das Konto „Muba“ ist ein **Microsoft-Konto** (Anzeigename „Musli Bajraktari“), Administrator. Auf dem PC sind zwei private Microsoft-Konten bekannt: `ardoar@hotmail.de` und `m.bajraktari@muba-bau-gmbh.de`. **Welches davon die Anmeldung trägt, muss Arber prüfen** (Einstellungen → Konten → Ihre Infos).
- Der PC ist **nicht** in das Microsoft-365 der MUBA eingebunden (`AzureAdJoined: NO`) und hat **keine Fernverwaltung/Intune**. Die MUBA kann den PC also nicht sperren oder löschen.
- Es gibt nur eine lose Verknüpfung als „Arbeits- oder Schulkonto“ (`WorkplaceJoined: YES`, Tenant MUBA Service GmbH, l.bajraktari@muba-service-gmbh.de). Darüber laufen Office-Anmeldung und das MUBA-OneDrive. Fällt der Tenant weg, funktionieren diese beiden nicht mehr, die **PC-Anmeldung bleibt davon unberührt**.
- **Risiko:** Ist das Anmelde-Konto `m.bajraktari@muba-bau-gmbh.de` und fällt die Domain muba-bau-gmbh.de weg, lässt sich das Passwort nicht mehr per Mail zurücksetzen. Die Anmeldung selbst funktioniert weiter, solange das Passwort bzw. die PIN bekannt ist.

**MUBA-Sicherung (Weg A):** info@ lädt nach (14.10. abends: 12.123 Mails im Posteingang, bis 06/2023 zurück, 20,9 GB). l.bajraktari@ steht bei 06/2025 (prüfen, ob das schon alles ist). Export nach `C:\MUBA-Sicherung` am 15.10. Weg B (Purview, Arber) folgt am Wochenende.

## Teil 1: Windows-Anmeldung absichern (Arber, ca. 15 Min.)

1. In **Einstellungen → Konten → Ihre Infos** nachsehen, welches Microsoft-Konto die Anmeldung trägt.
2. Bei diesem Microsoft-Konto unter account.microsoft.com → Sicherheit eine **Handynummer als Wiederherstellung** eintragen (nicht nur die Mailadresse).
3. **Notfall-Konto anlegen:** ein lokales Administratorkonto (z. B. `PrimaerBau-Admin`) mit einem Passwort, das sicher notiert wird (Passwort-Manager). Damit kommt man an den PC, auch wenn mit dem Microsoft-Konto etwas schiefgeht. Das macht Arber selbst (Systemeinstellung).
4. Optional, wenn die Anmeldung an `m.bajraktari@muba-bau-gmbh.de` hängt: das Konto „Muba“ auf ein **lokales Konto** umstellen (Einstellungen → Konten → Ihre Infos → „Stattdessen mit einem lokalen Konto anmelden“). Danach braucht die Anmeldung kein Microsoft mehr. Vorher klären, ob OneDrive privat genutzt wird.
5. BitLocker-Status prüfen (nur als Administrator lesbar). Ist BitLocker an, den **Wiederherstellungsschlüssel** sichern (er hängt sonst am Microsoft-Konto).

## Teil 2: PrimärBau-Postfächer per IMAP (Modul `intelligenz-imap`)

> **Umgesetzt am 14.10.2026** (außer IDLE-Dauerläufer): Server `mail.de2.hostedoffice.ag:993`, Live-MCP je Postfach nur mit Entwürfen, 15-Min.-Abruf in die Datenbank. Details: `docs/mail-imap-primaerbau.md`, Abweichungen: `module-installs/intelligenz-imap/ANPASSUNGEN.md`. Offen: IDLE-Dauerläufer statt Takt.

**Geschätzter Aufwand:** 45–60 Min. (Windows-Anpassungen inklusive)

Offene Fragen vorab:
- Bietet HostedOffice IMAP für diese Postfächer an? In Outlook laufen sie als Exchange-Konten. Server, Port und Anmeldeweg (Passwort oder nur Modern Auth) klärt das Durchleuchten (`discover_imap.py`) bzw. die HostedOffice-Hilfe.
- Wer kennt die Passwörter? Luljeta oder Arber hinterlegt sie verdeckt mit `python scripts/set_secret.py IMAP_PW_<LABEL>`, nie im Chat.

Schritte (Windows statt Mac, Abweichungen in `module-installs/intelligenz-imap/ANPASSUNGEN.md`):
1. Python-Pakete (`imap-tools`, `IMAPClient`, `python-dotenv`) und `uv` per winget/pip.
2. Konten-Config `config/imap-accounts.json`, Passwörter verdeckt hinterlegen.
3. Durchleuchten, dann Live-Zugriff (MCP) einrichten, **nur Entwürfe, kein Senden**.
4. Nachts bzw. laufend abrufen: Windows-Aufgabenplanung statt LaunchAgent.
5. Test: Fall Bayrhof/Kautz über IMAP statt Outlook finden.

## Teil 3: MUBA-Postfächer über Microsoft Graph (Modul `intelligenz-outlook`)

> **Umgesetzt am 15.10.2026 (nachts, Arber):** Entra-App „CEO-GPT PrimaerBau Mail“ (Einzelmandant, kein Mail.Send), l.bajraktari@ angemeldet und Lesen getestet. info@ ebenfalls angemeldet. Offen: Abklärung mit dem Insolvenzverwalter. Details: `docs/mail-muba-graph.md`, Abweichungen: `module-installs/intelligenz-outlook/ANPASSUNGEN.md`.

**Geschätzter Aufwand:** 60–90 Min. Das Modul ist für den Mac gebaut (Node-Build eines gepatchten MCP-Servers, Keychain), auf Windows ist mehr anzupassen.

- Arber registriert mit dem MUBA-Admin eine eigene Entra-App (ca. 10 Min.).
- Node.js installieren, MCP-Server bauen und patchen.
- **Nur Lesen und Entwürfe.**
- Hinweis: Das funktioniert nur, solange es den MUBA-Tenant gibt. Die Sicherung (Teil Weg A/B) ist davon unabhängig und hat Vorrang.

## Teil 4: Fernzugang (Weg N)

1. Tailscale-Konto für PrimärBau anlegen. **Offene Frage:** mit welcher Identität? Tailscale braucht eine Anmeldung über Google, Microsoft, GitHub oder Apple. Vorschlag: ein neues Konto auf eine Firmenadresse (z. B. it@primaerbau.com, falls vorhanden), nicht auf eine MUBA-Adresse.
2. Am PC als Administrator: `weg-n-einrichten.ps1` (zuerst mit `-WhatIf`), Tailscale installieren und mit dem PrimärBau-Konto anmelden.
3. MUBA-PC2 an Arbers Tailscale-Konto **teilen** (Admin-Konsole → Maschine → Teilen).
4. Edona: über das Büronetz. Am Router für MUBA-PC2 eine **feste IP-Adresse** reservieren, damit die Verbindung nicht wegrutscht.
5. Je Gerät einmal `ssh muba@<adresse>` im Terminal (Fingerabdruck bestätigen), dann in der Claude-App eine SSH-Verbindung anlegen. Anmeldung mit dem Passwort des Microsoft-Kontos (nicht der PIN) oder per Schlüssel.
6. BIOS: „Restore on AC Power Loss = Power On“. Für Auto-Login gemeinsam entscheiden, ob es nötig ist.

## Erfolgskriterien

- Der Mitarbeiter findet eine Mail per IMAP bzw. Graph, ohne dass Outlook läuft.
- Edona öffnet vom Büro-PC eine Claude-Sitzung im CEO-GPT-Ordner auf MUBA-PC2, `/prime` funktioniert.
- Arber erreicht MUBA-PC2 von unterwegs über das geteilte Gerät.
- Die PC-Anmeldung hängt an keiner MUBA-Adresse mehr, und es gibt ein Notfall-Konto.
