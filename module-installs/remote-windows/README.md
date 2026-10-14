# Remote-Windows

> Bring dein CEO-GPT auf einen Windows-PC, der durchläuft, und bediene ihn von jedem Gerät aus, von überall. Seit Version 2.0.0 zwei Wege:
>
> - **Weg N, nativ auf Windows:** Das CEO-GPT liegt direkt auf dem Windows-Rechner, gearbeitet wird von Laptop oder zweitem PC per **SSH-Sitzung der Claude-Desktop-App**. Richtig, wenn Branchensoftware, NAS oder Outlook nur unter Windows erreichbar sind. Seit Desktop-Version 2.31226.0 unterstützt und im Kundenbetrieb belegt.
> - **Weg V, Linux-VM:** Das CEO-GPT läuft in einer schlanken Linux-VM auf dem PC, technisch wie ein immer-an Server im Büro.

## Weg V: Warum eine Linux-VM statt nativ (wenn der Stack Linux ist)

Der ganze CEO-GPT-Stack ist Linux: systemd-Dienste und Timer, bash-Skripte, `.venv/bin/python`, die Sammler, der Telegram-Bot. Genau das, was auf dem Hetzner-Server läuft. Drei Wege, ihn auf einen Windows-PC zu bringen, einer gewinnt:

- **Nativ auf Windows:** für einen bestehenden Linux-Stack ein Neubau jedes Dienstes und Skripts. Läuft das CEO-GPT dagegen schon auf Windows oder muss es an Windows-Software, ist Weg N richtig.
- **WSL2:** behält den Code, startet aber nicht verlässlich unbeaufsichtigt nach Neustart/Stromausfall (bekannte, offene Windows-Schwachstelle). Nur Fallback mit Babysitting.
- **Echte Linux-VM (Hyper-V):** fährt beim Boot **ohne Login von selbst hoch**, läuft als ganz normaler Ubuntu-Server, deine Dienste laufen unverändert. **Der empfohlene Weg.**

Volle Begründung mit Quellen: `plans/2026-06-15-remote-windows-pc-recherche.md`.

## Was das Modul tut

Der geführte Installer bringt das CEO-GPT in vier Schichten auf den Windows-PC und sagt bei **jedem Schritt klar, wo er läuft**: auf deinem Mac, auf dem **Windows-Host** (PowerShell) oder **in der Linux-VM** (Linux).

1. **Windows-Host prüfen:** Edition, RAM, Hyper-V-Fähigkeit, BitLocker. Entscheidet Hauptweg (Pro) vs. Fallback (Home).
2. **Windows-Host als immer-an Chassis härten:** Schlaf/Ruhezustand aus, Strom-Wiederkehr, Auto-Login, Windows-Update-Reboots zähmen.
3. **Ubuntu-VM anlegen** (Hyper-V), auf Auto-Start beim Boot.
4. **Fernzugriff** über Tailscale + Tailscale-SSH **in der VM**, in dein Agentur-Tailnet, abgeriegelt per ACL.
5. **CEO-GPT in der VM aufbauen** (frisch über die Module, oder ein bestehendes Setup hineinziehen), dann der Always-on-Test.

## Was du brauchst

- Einen Windows-PC, der am Strom durchläuft, idealerweise **Windows 11 Pro/Enterprise** (für Hyper-V) und **8 GB RAM+**
- Eine Ubuntu-LTS-ISO (lädt der Installer hin)
- Für den Zugriff von unterwegs: ein kostenloses Tailscale-Konto (am besten dein eigenes Agentur-Konto)
- Keine API-Keys, keine laufenden Kosten

## So installierst du

1. Dieser Ordner liegt in `module-installs/`
2. `/install module-installs/remote-windows`
3. Dem geführten Setup folgen (erst Host prüfen, dann Schritt für Schritt)

## Laufende Kosten

Keine. Hyper-V ist Teil von Windows Pro, Tailscale ist im Privatgebrauch gratis.

## Was drin ist

| Datei | Zweck |
|---|---|
| `INSTALL.md` | Geführter Installer: Wegwahl N/V, klare Trennung Mac / Windows-Host / VM, Verifikation pro Schritt |
| `references/claude-desktop-ssh-windows.md` | Weg N komplett: Ziel-PC prüfen, Arbeitsgeräte einrichten, Pflichtprüfung NAS/Software in der SSH-Sitzung, Remote Control, HTTPS übers Tailnet |
| `scripts/windows-ssh-check.ps1` | Weg N: liest nur, prüft sshd, SFTP, MaxSessions, Shell, git, Speicher, Tailscale |
| `scripts/windows-host-check.ps1` | Liest nur: Edition, RAM, Hyper-V-Fähigkeit, BitLocker, Schlaf-/Fast-Startup-Stand. Sagt, welcher Weg geht |
| `scripts/windows-host-harden.ps1` | Setzt die sicheren Always-on-Einstellungen (Schlaf/Ruhezustand/Fast-Startup aus, Update-Reboots zähmen). `-WhatIf` für Vorschau |
| `scripts/create-vm.ps1` | Legt die Hyper-V-Ubuntu-VM an (Gen 2, RAM/CPU/Platte, Auto-Start beim Boot) |
| `scripts/verify_remote.py` | Endkontrolle **in der VM**: Workspace, venv, Datenbank, .env, systemd-Dienste, Tailscale |
| `references/windows-fernzugriff-onboarding.md` | Volle Referenz Tailscale-in-VM, Tailscale-SSH, Agentur-Tailnet und ACL |
| `references/troubleshooting.md` | Die teuer gelernten Stolpersteine, mit Fix |

## Setup-Zeit

Weg N: 15 bis 30 Minuten plus 5 Minuten je Arbeitsgerät. Weg V: 60 bis 120 Minuten, je nach Internet und ob der Host schon Windows Pro ist.

## Sicherheit

- Die `.env` wird nie gelesen, sondern sicher in die VM übertragen (über die schon stehende SSH-Verbindung), nie über Git.
- Weg V: Tailscale läuft **nur in der VM**, nie zusätzlich auf dem Windows-Host (doppelte Verkapselung bricht). Weg N: Tailscale direkt auf den Windows-Rechnern.
- Weg N: Anmeldung per Passwort oder Schlüssel ohne Passphrase; den Fingerabdruck des Ziel-PCs auf jedem Gerät selbst bestätigen, nie blind übernehmen.
- Die VM hängt über Tailscale nie offen im Internet, nur deine eigenen Geräte sehen sie, abgeriegelt per deny-by-default ACL.
- Auf Kundengeräten kein `--dangerously-skip-permissions`. Normalen Genehmigungs-Modus lassen.
- BitLocker auf **TPM-only** (entsperrt unbeaufsichtigt), nie TPM+PIN auf einem Gerät, das von selbst hochkommen soll.
