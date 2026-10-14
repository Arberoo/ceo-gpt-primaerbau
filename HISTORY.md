# CEO-GPT Historie

> Zeitliches Logbuch aller Arbeiten in diesem CEO-GPT. Wird jede Session aktualisiert.
> Neueste Einträge oben. Jeder Eintrag hat Datum, Titel und Bullet Points.
>
> **So läuft's:** Wenn du `/commit` nach einer sinnvollen Arbeit ausführst, trägt dein
> Mitarbeiter hier automatisch ein. Du musst diese Datei nicht selbst schreiben.

---

## 2026-10-14

### Absicherung eingerichtet (Arber und Luljeta)
- CEO-GPT aus dem MUBA-OneDrive nach `C:\CEO-GPT-PrimaerBau` kopiert (unabhängig vom MUBA-Microsoft-Konto); alte Kopie liegt noch im OneDrive
- Python 3.12 und GitHub CLI installiert (winget); GitHub CLI ist bewusst NICHT angemeldet
- Git eingerichtet, Speicherpunkte unter dem Namen „PrimärBau“
- Privates Repo `Arberoo/ceo-gpt-primaerbau`; Zugriff nur über fine-grained Token (nur dieses Repo, Contents: Read and write, läuft nie ab), hinterlegt in der Windows-Anmeldeinformationsverwaltung via `scripts/github_token_hinterlegen.ps1`
- Schutzliste (.gitignore) erweitert: .pst/.msg/.eml, PDFs, Office-Dateien, Bilder, `context/import/` bleiben lokal
- Nächtliche Sicherung 23:45 über die Windows-Aufgabenplanung („CEO-GPT PrimaerBau Sicherung“), Probelauf erfolgreich
- HISTORY.md, docs/-System und `/commit` Befehl angelegt, `/prime` liest Logbuch und Doku-Index
