# Aufbau: offene Punkte (nur für Arber)

> **Diese Liste ist Arbers Baustelle.** Luljeta arbeitet *mit* dem CEO-GPT, Arber baut *am* CEO-GPT.
> Der Mitarbeiter zeigt diese Liste **nur**, wenn Arber sich meldet („Hier ist Arber“) oder jemand ausdrücklich danach fragt. Luljeta wird damit nicht konfrontiert.
> Erledigtes abhaken (nicht löschen), mit Datum. Neue Bau-Themen hier eintragen, nicht in Luljetas Briefings.

Stand: 15.10.2026, nachts

## 🔴 Zuerst

- [ ] **MUBA-Postfächer als PST sichern (Weg A).** Outlook lädt info@ und l.bajraktari@ (MUBA) seit 14.10. komplett nach (Stand 14.10. spät: info@ bis 06/2023, l.bajraktari@ bis 06/2025). Wenn fertig: Export nach `C:\MUBA-Sicherung`, dann eine Kopie auf eine externe Festplatte. Anleitung `docs/muba-postfaecher-sichern.md`. **Vor** dem Bau des Mail-Assistenten.
- [ ] **Mail an Herrn Festing senden.** Entwurf liegt in info@primaerbau.com unter „Entwürfe“ (Zugangsdaten fesel@, Salzberger, karl@). Für den Fall Kautz wichtig, Frist 23.10. Wenn die Zugangsdaten kommen: verdeckt hinterlegen und anbinden lassen (Akte `data/akten/2026-444-Bayrhof-Kautz/AKTE.md`).
- [ ] **Mail-Assistent bauen:** `/implement plans/2026-10-15-mail-assistent-posteingang.md` (nach dem PST-Export). Danach Luljeta kurz zeigen, wie sie `/posteingang` nutzt.

## 🟠 Wochenende

- [ ] **Insolvenzverwalter fragen:** Ist der neue Zugang „CEO-GPT PrimaerBau Mail“ im MUBA-Microsoft-Konto in Ordnung? (Entfernen: `docs/mail-muba-graph.md`)
- [ ] **MUBA vollständig über Purview sichern (Weg B)**, Anleitung `docs/muba-postfaecher-sichern.md`.
- [ ] **Unterlagen aus dem MUBA-OneDrive** (`Desktop`, `Dokumente`) als Kopie nach `C:\PrimaerBau-Unterlagen\MUBA-OneDrive-Kopie\` ziehen (nur kopieren), danach `config/posteingang.json` → `dokument_ordner` umstellen. Mit Luljetas Ja.
- [ ] **CEO-GPT-Ordner abschotten:** `C:\CEO-GPT-PrimaerBau` erbt von `C:\` Schreibrechte für alle angemeldeten Benutzer (darunter die fremden lokalen Konten `CodexSandboxOffline`/`CodexSandboxOnline`). Als Administrator die Vererbung brechen und nur Luljetas Konto „Muba“, SYSTEM und Administratoren Zugriff geben. Vorher prüfen, ob die Windows-Aufgaben (Sicherung, Mail-Sofort, Mail-Abruf) danach noch laufen. Bei Gelegenheit klären, woher die Codex-Konten stammen und ob sie weg können.
- [ ] **Windows-Anmeldung absichern** (Plan `plans/2026-10-14-fernzugang-und-mailzugriff.md`, Teil 1): Welches Microsoft-Konto trägt die Anmeldung? Handynummer zur Wiederherstellung, Notfall-Admin-Konto, ggf. auf lokales Konto umstellen, BitLocker-Schlüssel sichern.
- [ ] **Alte CEO-GPT-Kopie im MUBA-OneDrive löschen:** `…\OneDrive - MUBA Service GmbH\Dokumente\CEO-GPT-PrimaerBau`. Bedingung (Nacht-Sicherung lief) ist erfüllt.

## 🟡 Danach

- [ ] **Fernzugang** für Arber (Tailscale, eigenes PrimärBau-Konto, PC teilen) und Edona (Büronetz, feste IP am Router). Plan Teil 4, Skript `module-installs/remote-windows/scripts/weg-n-einrichten.ps1`.
- [ ] **PC als Haupt-PC:** Dauerbetrieb (ist im Weg-N-Skript), BIOS „Power On after AC loss“.
- [ ] **Ablage-Modul** (`/install module-installs/ablage`): Ordnersystem für Unterlagen, Scans, Mail-Anhänge; PDF-Volltextsuche.
- [ ] **Buchhaltung** mit Edona (`module-installs/buchhaltung`), TEAM3-Weg mit dem IT-Dienstleister klären.
- [ ] **Edonas Kontext** ergänzen (`/install module-installs/kontext`, nur ihr Teil).
- [ ] **Automatischer Morgen-Lauf** von `/posteingang` (v2): `claude setup-token`, Aufgabenplanung.
- [ ] Optional: `CLAUDE_CODE_OAUTH_TOKEN` für schönere Texte der nächtlichen Sicherung.

## Erledigt

- [x] 14.10. Absicherung (Git, GitHub privat mit fine-grained Token, nächtliche Sicherung)
- [x] 14.10. Kontext-Gespräch mit Luljeta
- [x] 14./15.10. Alle fünf Postfächer angebunden (IMAP + Graph), Sofort-Abruf per IDLE abgenommen
- [x] 15.10. Plan Mail-Assistent (zweimal geprüft)
