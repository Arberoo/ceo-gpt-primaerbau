# Weg N: CEO-GPT direkt auf Windows, bedient per Claude-Desktop-SSH

> Für Kunden, deren CEO-GPT **direkt auf einem Windows-Rechner** läuft (kein Linux, keine VM),
> etwa weil die Branchensoftware, das NAS oder Outlook nur dort erreichbar sind.
> Der Kunde arbeitet von jedem anderen Gerät (Laptop, zweiter PC) per SSH-Sitzung der
> Claude-Desktop-App auf diesem Rechner. Im Kundenbetrieb belegt (Windows-Client → Windows-Rechner, Shell `cmd.exe`).
> Stand: 2026-10-10

## Warum das jetzt geht

Die allgemeine Desktop-Doku sagt noch „der entfernte Rechner muss Linux oder macOS sein“. Das ist veraltet:

- Anthropics Doku zu SSH-Sitzungen der Desktop-App nennt als Ziel ausdrücklich auch **Windows auf x64 oder arm64**, mit Microsofts OpenSSH-Server und PowerShell bzw. `cmd.exe` ([SSH remote sessions](https://claude.com/docs/third-party/claude-desktop/ssh-remote-sessions)).
- Im Änderungsprotokoll der Desktop-App stehen Fehlerbehebungen genau für diesen Fall ([Changelog](https://claude.com/docs/cowork/changelog)):
  - 24.09.2026, Version 2.9939.2: Verbindungen von Windows zu einem Windows-Rechner mit `cmd.exe` scheiterten.
  - 08.10.2026, Version 2.31226.0: Nachrichten gingen auf Windows-Rechnern mit `cmd.exe` oder PowerShell verloren.
- **Mindestversion der Desktop-App auf jedem Gerät: 2.31226.0.**

Behauptet ein Claude im Kundensetup, das gehe nur mit Linux, ist das der alte Doku-Stand. Nicht auf WSL oder eine Linux-VM ausweichen, bevor dieser Weg geprüft ist.

## Die zwei Rollen

- **ZIEL-PC** = der Windows-Rechner, auf dem das CEO-GPT liegt (Ordner, MCP-Server, Werkzeuge). Er läuft durch.
- **ARBEITSGERÄT** = jedes Gerät, von dem aus der Kunde arbeitet (Laptop, Büro-PC, Mac). Auf ihm läuft nur die Claude-Desktop-App.

Tailscale läuft hier **direkt auf beiden Windows-Rechnern** (es gibt keine VM). Die Regel „Tailscale nie zusätzlich auf dem Host“ gilt nur für Weg V mit Linux-VM.

## Teil 1: Ziel-PC prüfen (einmalig)

PowerShell als Administrator am ZIEL-PC:

```powershell
powershell -ExecutionPolicy Bypass -File .\windows-ssh-check.ps1
```

Liest nur. Muss alles grün zeigen:

| Punkt | Soll | Fix |
|---|---|---|
| `sshd` | läuft, Starttyp Automatisch | `Start-Service sshd`, `Set-Service sshd -StartupType Automatic` |
| SFTP | Zeile `Subsystem sftp sftp-server.exe` ohne `#` | ergänzen, `Restart-Service sshd` |
| `MaxSessions` | nicht 1 (Standard 10) | Zeile entfernen oder erhöhen |
| Passwort-Anmeldung | erlaubt (Standard) | sonst Schlüssel ohne Passphrase je Gerät |
| Standard-Shell | keine gesetzt (= `cmd.exe`) oder PowerShell | nie WSL-bash oder Git Bash |
| git | vorhanden, systemweit | Git for Windows |
| Speicher | > 1 GB frei | Die App legt ihren Teil unter `~/.claude/remote/` ab |
| Tailscale | verbunden | in der Tailscale-App anmelden |

**Auf dem Ziel-PC selbst testen**, bevor ein anderes Gerät dran ist: In PowerShell einmal `ssh <benutzer>@<hostname>` (den Namen, den auch die Arbeitsgeräte nutzen), Fingerabdruck mit `yes` bestätigen, Passwort, `exit`. Danach in der Desktop-App auf dem Ziel-PC dieselbe SSH-Verbindung anlegen. Läuft das, ist die Serverseite belegt.
Mit `localhost` als Host meldet die App „Dies stellt über SSH eine Verbindung zu diesem Computer her …“. Das ist nur ein Hinweis. Besser gleich den echten Hostnamen nehmen, dann ist der Test identisch mit dem der Arbeitsgeräte.

## Teil 2: Jedes Arbeitsgerät (je Gerät und je Windows-Benutzer einmalig)

1. **Tailscale an**, angemeldet im selben Tailnet wie der Ziel-PC.
2. **Claude Desktop** mindestens 2.31226.0 (Hilfe → Nach Updates suchen), mit dem Claude-Konto des Kunden angemeldet.
3. **Fingerabdruck einmal im Terminal bestätigen.** Das ist der häufigste Fehler. Die App nutzt unter Windows ein eingebautes SSH-Programm, das **nicht selbst nach dem Fingerabdruck fragt**. Er muss vorher in `known_hosts` stehen:

   ```powershell
   ssh <benutzer>@<hostname>
   ```

   `yes`, Passwort, dann `exit`. Muss in **dem Windows-Konto** passieren, unter dem die Desktop-App läuft. Ein anderer Rechner oder anderer Benutzer braucht den Schritt erneut.
4. **Verbindung in der App anlegen:** Code-Tab → Umgebung → **SSH-Verbindung hinzufügen**.

   | Feld | Eintrag |
   |---|---|
   | Name | frei, z. B. `CEO-GPT` |
   | SSH-Host | `<benutzer>@<hostname>` |
   | SSH-Port | leer (22) |
   | SSH-Schlüssel | leer bei Passwort-Anmeldung |
   | Worktree-Ordner | leer |

   Nach dem Passwort fragt die App selbst; es lässt sich speichern.
5. **Den CEO-GPT-Ordner auf dem Ziel-PC wählen** (der Ordner mit `CLAUDE.md`), `/prime`, kurze Testfrage.

**Schlüssel statt Passwort:** Nur Schlüssel **ohne Passphrase** oder über den SSH-Agenten; Schlüssel mit Passphrase überspringt die App ohne Meldung. Ist das Konto auf dem Ziel-PC lokaler Administrator, gehört der öffentliche Schlüssel in `C:\ProgramData\ssh\administrators_authorized_keys`, nicht in den Benutzerordner.

## Teil 3: Pflichtprüfung in der SSH-Sitzung

Eine SSH-Anmeldung ist nicht dasselbe wie eine Anmeldung am Bildschirm. Besonders bei Schlüssel-Anmeldung gibt Windows die eigenen Anmeldedaten nicht weiter ([Ansible zu Windows-SSH](https://docs.ansible.com/ansible/latest/os_guide/windows_ssh.html)). In der ersten Claude-Sitzung deshalb prüfen lassen:

- `whoami` zeigt das richtige Konto.
- **Netzlaufwerke/NAS:** Ordner auflisten. Verbundene Laufwerksbuchstaben fehlen in SSH-Sitzungen oft; dann den UNC-Pfad (`\\server\freigabe`) nutzen oder den Zugang ausdrücklich mitgeben.
- **Branchensoftware/Datenbank:** eine kleine Leseabfrage. Software mit eigenem SQL-Login ist nicht betroffen, Windows-Anmeldung (integrierte Sicherheit) eventuell schon.
- **Outlook:** Über die Microsoft-API (Entra-App) unproblematisch. Das installierte Outlook-Programm per COM läuft in einer SSH-Sitzung sehr wahrscheinlich nicht.

Was hier fehlt, merkt der Kunde sonst erst unterwegs.

## Teil 4: Hinweise für den Kunden

- **„Änderungen übernehmen“ und +/−-Zahlen unten in der App:** Das zeigt die App automatisch, sobald im Projektordner Git eingerichtet ist. Es sind die geänderten Zeilen. Muss der Kunde nicht drücken. Ohne Git-Sicherung kann Git im Ordner auch weg, wenn anderweitig gesichert wird.
- **Remote Control:** In der SSH-Sitzung lässt sich Remote Control einschalten (Schalter je Sitzung oder standardmäßig für jede neue Sitzung). Dann ist dieselbe Sitzung auch vom iPhone aus der Claude-App unter „Code“ bedienbar.
- **Gleicher Wissensstand überall:** Alle Geräte arbeiten im selben Ordner auf dem Ziel-PC, es gibt nichts zu synchronisieren.

## Rückfall: Remote Control ohne SSH

Klappt die SSH-Sitzung nicht, läuft Claude Code direkt auf dem Ziel-PC im normalen Windows-Konto mit allen Werkzeugen, bedient über claude.ai/code oder die iPhone-App ([Doku](https://code.claude.com/docs/en/remote-control)). Für Dauerbetrieb:
- Claude auf dem Ziel-PC mit `/login` anmelden. **Ein Setup-Token reicht für Remote Control nicht.**
- Beim ersten Start die Rückfragen einmal im Terminal bestätigen.
- Der Prozess muss nach Neustart oder Abbruch automatisch wieder hochkommen (geplante Aufgabe bei Anmeldung).

Erst wenn beides scheitert: WSL oder eigene Linux-VM (Weg V). WSL 2 in einer virtualisierten Windows-Maschine braucht verschachtelte Virtualisierung beim Host und mindestens Windows Server 2022.

## HTTPS fürs Cockpit über Tailscale

Ohne HTTPS gibt das iPhone weder Standort noch Mitteilungen frei.

- **Schnell:** Im Tailscale-Adminbereich MagicDNS und **HTTPS-Zertifikate** einschalten (nur Tailnet-Admin). Dann am Ziel-PC `tailscale serve --bg <cockpit-port>`. Das Cockpit ist unter `https://<rechner>.<tailnet>.ts.net` erreichbar, nur im Tailnet.
- **Eigene Domain:** Tailscale stellt Zertifikate nur für `*.ts.net` aus. Eine eigene Domain per DNS auf die Tailscale-Adresse zu zeigen genügt nicht, der Browser sieht dann das falsche Zertifikat. Dafür braucht es ein eigenes Zertifikat, z. B. Caddy vor dem Cockpit mit Let's Encrypt über DNS-Prüfung (einmalig ein CNAME `_acme-challenge.<domain>` auf eine selbst verwaltete Zone). Beide Adressen können parallel laufen; auf dem iPhone die App danach einmal mit der neuen Adresse anlegen.
- Prüfen, ob das Cockpit irgendwo eine feste Adresse eingetragen hat, bevor die Adresse wechselt.
