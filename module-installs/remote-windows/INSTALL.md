# Remote-Windows: Installation

<!-- MODUL-METADATEN
modul: remote-windows
version: 2.0.0
status: RELEASED
released: 2026-10-10
requires: []
optional: [absicherung, kontext, stimme]
phase: 4
category: Erweiterung
complexity: complex
api_keys: 0
setup_time: 60-120 Minuten
-->

---

## FÜR CLAUDE (Anleitung für dich, das Programm)

**Zuerst die Wegwahl (seit Version 2.0.0 gibt es zwei Wege):**

- **Weg N, nativ auf Windows:** Das CEO-GPT liegt direkt auf einem Windows-Rechner (weil Branchensoftware, NAS oder Outlook nur dort erreichbar sind, oder weil es dort schon läuft). Der Kunde arbeitet von Laptop oder zweitem PC per **SSH-Sitzung der Claude-Desktop-App** auf diesem Rechner. Kein Linux, keine VM. Komplette Anleitung: `MODULE_DIR/references/claude-desktop-ssh-windows.md`, Prüfskript `scripts/windows-ssh-check.ps1`. Das ist der Weg, wenn der Kunde mit Windows-Werkzeugen arbeitet.
- **Weg V, Linux-VM auf Windows:** Der Rest dieser Anleitung (Teil 0 bis 5). Für Kunden, deren CEO-GPT als Linux-Server mit systemd-Diensten laufen soll und der Windows-PC nur das immer-an Gehäuse ist.

Frag den Member: "Läuft dein CEO-GPT schon auf dem Windows-Rechner, oder muss es an Programme ran, die es nur unter Windows gibt?" Ja → Weg N. Nein → Weg V.

**Nicht verwechseln:** Die allgemeine Claude-Doku sagt noch, SSH-Ziele müssten Linux oder macOS sein. Das ist veraltet, Windows-Ziele sind seit Desktop-Version 2.31226.0 (08.10.2026) unterstützt und im Kundenbetrieb belegt. Nicht deswegen auf eine VM ausweichen.

---

**Weg V:** Du richtest ein, dass das CEO-GPT auf einem **immer-an Windows-PC** läuft, den der Member von seinem Mac aus **fern bedient**. Der CEO-GPT läuft dabei **nicht nativ auf Windows**, sondern in einer schlanken **Ubuntu-Linux-VM** auf dem PC. Das ist bewusst so: der ganze Stack ist Linux (systemd, bash, `.venv/bin/python`), und eine echte VM fährt beim Boot **ohne Login von selbst hoch**, was ein Kundengerät zwingend braucht. Volle Begründung: `plans/2026-06-15-remote-windows-pc-recherche.md`.

**Die wichtigste Regel: drei Schichten sauber auseinanderhalten.**
- **MAC** = der Rechner des Members, von dem aus er arbeitet und administriert. Hier sitzt du am Anfang.
- **WINDOWS-HOST** = der immer-an PC des Kunden. Nur das Chassis. Befehle hier laufen in **PowerShell**.
- **VM** = die Ubuntu-VM im Windows-Host. **Hier lebt das CEO-GPT.** Befehle hier sind normales **Linux/bash**, genau wie auf dem Hetzner-Server.
- **Bei JEDEM Schritt klar ansagen, ob er auf dem MAC, am WINDOWS-HOST (PowerShell) oder in der VM (Linux) läuft.** Verwechsle das nie.

**Du sitzt am Mac.** Sobald der Fernzugriff steht, klinkst du dich per SSH in die VM ein und arbeitest dort wie auf jedem Linux-Server. Manche Dinge kann nur der Member direkt am Windows-PC tun (BIOS, Auto-Login, Hyper-V einschalten, Ubuntu durch den Installer klicken). Sag dann klar: "Das machst du jetzt bitte selbst am Windows-PC."

**Sicherheit (hart, nicht verhandelbar):**
- **`.env` nie lesen.** Sicher in die VM übertragen (per rsync über die schon stehende SSH-Verbindung), nie über Git, nie in den Chat.
- **Nie ein Passwort des Members erfragen oder eintippen.** Logins gibt der Member selbst ein.
- **Weg V: Tailscale läuft NUR in der VM, nie auf dem Windows-Host.** Auf beiden bricht es (doppelte Verkapselung). Bei Weg N (keine VM) läuft Tailscale direkt auf dem Windows-Rechner, das ist richtig so.
- **BitLocker auf TPM-only**, nie TPM+PIN auf einem Gerät, das unbeaufsichtigt hochkommen soll.
- **Der Bot und alle Dienste dürfen nur auf EINER Maschine laufen.** Läuft das Setup noch woanders (alter Mac/Server), dort erst abschalten.
- **Auf Kundengeräten kein `--dangerously-skip-permissions`.**

**Die eine Weiche, zuerst klären: Windows-Edition.** Hyper-V (der empfohlene Weg) braucht **Windows 11 Pro/Enterprise/Education**, nicht Home. Das prüfst du in Teil 0, bevor irgendetwas anderes passiert. Bei Home: Fallback-Pfad (siehe Teil 0).

**Chicken-and-Egg, einplanen:** Fernzugriff klappt erst, wenn er in der VM eingeschaltet ist. Die ersten Schritte am Windows-PC (Host härten, Hyper-V an, Ubuntu installieren, Tailscale in der VM) muss jemand direkt am Gerät machen, entweder der Member sitzt davor, oder per Video-Call mit Bildschirmfreigabe.

**Verhalten:**
- Geh davon aus, dass der Member nicht technisch ist. Erklär in Klartext, was du als Nächstes machst, bevor du es machst.
- Feier Meilensteine ("Fernzugriff steht, die VM ist jetzt dein Server").
- Kein Log-Dump bei Fehlern. Problem in einem Satz, dann der Fix. `references/troubleshooting.md` nutzen.
- Halt nach jedem Teil kurz inne.

`MODULE_DIR` = der Pfad dieses Moduls (`module-installs/remote-windows`). Die PowerShell-Skripte liegen in `MODULE_DIR/scripts/` und müssen einmal auf den Windows-PC kopiert werden (per Taildrop, USB oder die Hyper-V-Konsole).

---

## WEG N: NATIV AUF WINDOWS MIT CLAUDE-DESKTOP-SSH (Kurzfassung)

> Vollständig in `MODULE_DIR/references/claude-desktop-ssh-windows.md`. Hier die Reihenfolge.

1. **Am ZIEL-PC (PowerShell als Administrator):** `windows-ssh-check.ps1` laufen lassen. Alles grün? Sonst die gemeldeten Fixes (sshd automatisch, SFTP an, MaxSessions nicht 1, Standard-Shell cmd/PowerShell, git, > 1 GB frei, Tailscale verbunden).
2. **Am ZIEL-PC selbst testen:** `ssh <benutzer>@<hostname>` → `yes` → Passwort → `exit`. Dann Claude Desktop (mind. 2.31226.0) dort öffnen und dieselbe SSH-Verbindung anlegen. Klappt das, ist die Serverseite belegt.
3. **An jedem ARBEITSGERÄT** (Laptop, zweiter PC), je Gerät und Windows-Benutzer einmal:
   1. Tailscale an, im selben Tailnet.
   2. Claude Desktop mindestens 2.31226.0.
   3. In PowerShell `ssh <benutzer>@<hostname>`, Fingerabdruck mit `yes`, Passwort, `exit`. **Ohne diesen Schritt scheitert die App**, sie fragt selbst nicht nach dem Fingerabdruck.
   4. Code-Tab → SSH-Verbindung hinzufügen: Name frei, SSH-Host `<benutzer>@<hostname>`, Port/Schlüssel/Worktree leer.
   5. CEO-GPT-Ordner wählen, `/prime`.
4. **Pflichtprüfung in der SSH-Sitzung:** `whoami`, NAS-Ordner auflisten, kleine Leseabfrage in der Branchensoftware. SSH-Sitzungen sehen verbundene Netzlaufwerke oft nicht.
5. **Dem Kunden erklären:** Remote Control in der Sitzung einschalten (dann auch vom iPhone bedienbar); „Änderungen übernehmen“ unten kommt von Git und muss nicht gedrückt werden.

[VERIFY] Vom Arbeitsgerät aus läuft eine Claude-Sitzung im CEO-GPT-Ordner des Ziel-PCs, `/prime` funktioniert, NAS und Branchensoftware sind in der Sitzung erreichbar. "Du kommst jetzt von jedem Gerät an dein CEO-GPT."

Rückfall, falls SSH nicht klappt: Remote Control direkt auf dem Ziel-PC (siehe Referenz, braucht `/login`, kein Setup-Token).

---

## ÜBERSICHT WEG V (lies das dem Member vor dem Start vor)

Jetzt bringen wir dein CEO-GPT auf den Windows-PC, der bei dir im Büro durchläuft. Wichtig zu verstehen: dein CEO-GPT ist ein Linux-System. Damit es stabil und immer-an läuft, setzen wir auf dem PC eine kleine, unsichtbare Linux-Maschine auf (eine VM) und bauen das CEO-GPT da hinein. Der Windows-PC ist nur der Untergrund, der durchläuft.

Der Vorteil: diese Linux-Maschine startet nach einem Neustart oder Stromausfall von ganz allein wieder, auch wenn niemand davorsitzt. Du erreichst sie von überall, der Bot läuft rund um die Uhr.

Das läuft in fünf Schritten:
1. **PC prüfen:** passt die Windows-Version, ist genug Speicher da.
2. **PC fürs Dauerlaufen einstellen:** kein Schlaf, kommt nach Stromausfall von selbst hoch.
3. **Die Linux-Maschine anlegen.**
4. **Fernzugriff einrichten,** damit du und ich von überall drankommen.
5. **Das CEO-GPT in die Linux-Maschine bauen** und einmal hart testen.

**Setup-Zeit:** 60 bis 120 Minuten.
**Kosten:** keine. Alles ist in Windows und Tailscale (privat) enthalten.
**Datenschutz:** alles bleibt auf deinem PC. Die Maschine hängt über Tailscale nie offen im Internet, nur deine eigenen Geräte sehen sie.

---

## TEIL 0: WINDOWS-EDITION PRÜFEN (die Weiche)

> Erst die eine Frage, die den Weg bestimmt. Das passiert am WINDOWS-HOST.

Sag dem Member: "Wir prüfen zuerst kurz, ob dein PC die passende Windows-Version und genug Speicher hat. Öffne bitte am PC die PowerShell als Administrator."

Die Skripte dieses Moduls auf den Windows-PC bringen (Taildrop/USB/Hyper-V-Konsole), dann am WINDOWS-HOST:

```powershell
# PowerShell als Administrator, im scripts-Ordner
powershell -ExecutionPolicy Bypass -File .\windows-host-check.ps1
```

Das liest nur (ändert nichts) und meldet: Edition, RAM, ob Hyper-V geht, BitLocker-Modus, Schlaf-/Fast-Startup-Stand.

**Weiche:**
- **Windows 11 Pro/Enterprise/Education + genug RAM (idealerweise 8 GB+):** → Hauptweg, weiter mit Teil 1.
- **Windows 11 Home:** Hyper-V geht nicht. Optionen mit dem Member klären: (a) auf Pro upgraden (empfohlen, günstig, dann Hauptweg), (b) VirtualBox + VBoxVmService als VM-Weg ohne Hyper-V, (c) als letzter Ausweg WSL2 mit Babysitting. Bei (b)/(c) Teil 2 entsprechend anpassen, der Rest bleibt gleich.
- **Virtualisierung im BIOS aus** (Skript meldet es): Member bittet, im BIOS Intel VT-x / AMD-V (SVM) einzuschalten, dann erneut prüfen.

[VERIFY] Das Skript hat gelaufen und du kennst Edition, RAM und Hyper-V-Fähigkeit. "Dein PC ist {geeignet für den Standard-Weg / Windows Home, wir nehmen den Fallback-Weg}."

---

## TEIL 1: WINDOWS-HOST ALS IMMER-AN CHASSIS HÄRTEN

> Das passiert am WINDOWS-HOST. Drei Dinge per Skript, drei per Hand am Gerät.

### Per Skript (PowerShell als Administrator)

```powershell
# erst Vorschau, ändert nichts:
powershell -ExecutionPolicy Bypass -File .\windows-host-harden.ps1 -WhatIf
# dann echt:
powershell -ExecutionPolicy Bypass -File .\windows-host-harden.ps1
```

Das setzt: Schlaf aus, Festplatten-Schlaf aus, Ruhezustand und Fast-Startup aus, hohe-Leistung-Plan, und zähmt die Windows-Update-Reboots (kein Auto-Reboot bei angemeldetem Nutzer, weite aktive Stunden). Es fasst BIOS, Auto-Login und BitLocker bewusst NICHT an, das sind die drei Handgriffe unten.

### Per Hand am Gerät (sag dem Member klar an)

1. **BIOS: nach Stromausfall hochfahren.** "Starte den PC neu und tippe beim Hochfahren die BIOS-Taste (oft Entf, F2 oder F10). Such die Einstellung 'Restore on AC Power Loss' oder 'After Power Failure' und stell sie auf **Power On**. Speichern und raus." Das ist Firmware, kein Windows-Schalter. Eine kleine USV davor ist sinnvoll.
2. **Auto-Login.** "Lade Sysinternals Autologon (Microsoft), starte es, trag dein Konto und Passwort ein, klick Enable." Speichert das Passwort verschlüsselt, nicht im Klartext. Am besten ein eigenes Konto mit wenig Rechten.
3. **BitLocker prüfen.** Wenn die Systemplatte verschlüsselt ist, auf **TPM-only** lassen (entsperrt beim Boot von allein). Wenn der PC nach Neustart ständig den Wiederherstellungs-Schlüssel will, auf der Systemplatte BitLocker aus. Den Wiederherstellungs-Schlüssel außerhalb des PCs sichern.

[VERIFY] `windows-host-harden.ps1` lief sauber, BIOS steht auf Power On, Auto-Login ist aktiv, BitLocker entsperrt unbeaufsichtigt. "Der PC läuft jetzt durch und kommt nach Stromausfall von selbst wieder hoch."

---

## TEIL 2: HYPER-V EINSCHALTEN UND DIE UBUNTU-VM ANLEGEN

> Das passiert am WINDOWS-HOST (PowerShell als Administrator) und einmal in der Hyper-V-Konsole.

### Hyper-V einschalten (einmal, mit Neustart)

```powershell
Enable-WindowsOptionalFeature -Online -FeatureName Microsoft-Hyper-V -All
```
Danach den PC einmal neu starten. (Bei Windows Home stattdessen der Fallback aus Teil 0.)

### Ubuntu-ISO bereitlegen

Eine **Ubuntu Server LTS** ISO (oder Desktop, Server reicht und ist schlanker) herunterladen und den Pfad merken, z.B. `C:\Users\<user>\Downloads\ubuntu.iso`.

### VM anlegen

```powershell
powershell -ExecutionPolicy Bypass -File .\create-vm.ps1 -VMName "CEO-GPT" -MemoryGB 2 -CpuCount 2 -DiskGB 40 -IsoPath "C:\Users\<user>\Downloads\ubuntu.iso"
```

Das legt eine Gen-2-VM an, setzt das Linux-Secure-Boot-Template, hängt die ISO ein, und stellt **Auto-Start beim Boot** plus **sauberes Herunterfahren** ein.

### Ubuntu installieren (in der Hyper-V-Konsole)

Member öffnet den Hyper-V-Manager, startet die VM und verbindet sich (Doppelklick). Den Ubuntu-Installer durchklicken:
- Benutzer anlegen (Name merken, z.B. `ceogpt`).
- **OpenSSH-Server mit anhaken** (wichtig, sonst kein SSH).
- Rest Standard.

Nach der Installation die ISO aushängen (sonst bootet sie wieder hinein):
```powershell
Get-VMDvdDrive -VMName "CEO-GPT" | Set-VMDvdDrive -Path $null
```

[VERIFY] Die VM läuft, Ubuntu ist installiert, du kennst den VM-Benutzernamen. In der VM `whoami` und `systemctl is-system-running` (sollte "running" oder "degraded" zeigen, nicht "offline"). "Die Linux-Maschine steht."

---

## TEIL 3: FERNZUGRIFF ÜBER TAILSCALE (IN DER VM)

> Das passiert in der VM. Volle Referenz: `MODULE_DIR/references/windows-fernzugriff-onboarding.md`.

### Auth-Key vorbereiten (auf dem MAC, im Tailscale-Adminbereich)

Einen **wiederverwendbaren, getaggten, vorab genehmigten** Auth-Key erzeugen (Settings → Keys), Tag z.B. `tag:kunde-box`. Vorher einmal die ACL aus der Referenz setzen (deny-by-default, nur dein Gerät kommt an die Boxen).

### In der VM (Hyper-V-Konsole oder lokales SSH)

```bash
curl -fsSL https://tailscale.com/install.sh | sh
sudo systemctl enable --now tailscaled
sudo tailscale up --ssh --hostname=<kunde>-box --auth-key=tskey-... --unattended
```

`--ssh` schaltet Tailscale-SSH an (kein Schlüssel-Gefummel), `--unattended` hält den Knoten ohne Login oben.

### Vom MAC testen

```bash
ssh <vm-user>@<kunde>-box "echo verbunden mit $(hostname)"
```

[VERIFY] Vom Mac kommt "verbunden mit ..." zurück, ohne Passwort. Einmal aus einem anderen Netz testen (Handy-Hotspot), muss genauso gehen. "Fernzugriff steht. Du erreichst die VM von überall."

---

## TEIL 4: CEO-GPT IN DER VM AUFBAUEN

> Das passiert in der VM, per Claude Code über die SSH-Verbindung. Zwei Wege.

**Claude Code in der VM bereitstellen** (nativer Installer, kein Node nötig):
```bash
curl -fsSL https://claude.ai/install.sh | bash
claude   # einmal einloggen (Konto des Kunden), Ordner vertrauen
```

### Weg A, frischer Aufbau (der Normalfall, z.B. Karl)

Wie eine normale Erstinstallation, nur eben fern in der VM:
1. `/install module-installs/absicherung` (Versionskontrolle, Backup, Doku)
2. `/install module-installs/kontext` (das Gehirn)
3. dann weiter nach Bedarf: Daten, Intelligenz, Stimme, Ordnung
4. Secrets direkt in die `.env` der VM schreiben (nie in den Chat).

### Weg B, bestehendes Setup hineinziehen

Wenn schon ein CEO-GPT auf einem anderen Linux-Rechner (Server/VM) läuft und in diese VM soll:
1. Auf dem Quell-Rechner `pip freeze > requirements.txt`, sauber committen.
2. Workspace rüberziehen, ohne die `.venv`:
   ```bash
   rsync -av --exclude '.venv' <quelle>:~/CEO-GPT/ ~/CEO-GPT/
   ```
3. In der VM venv neu bauen: `python3 -m venv .venv && .venv/bin/pip install -r requirements.txt`.
4. systemd-Units übertragen und aktivieren (`systemctl enable --now ceo-gpt-*`). Pfade prüfen, falls der Benutzername abweicht.
5. Auf der Quelle alle Dienste abschalten, damit nichts doppelt läuft.

### Dienste als systemd (genau wie auf dem Hetzner)

Der Telegram-Bot braucht keine offenen Ports (er wählt raus), das Cockpit läuft auf `localhost:8787` und wird per SSH-Tunnel erreicht. Die `ceo-gpt-*`-Units mit `systemctl enable` aktivieren, damit sie nach VM-Neustart von selbst kommen.

### Endkontrolle in der VM

```bash
python3 MODULE_DIR/scripts/verify_remote.py
```
Prüft Workspace, venv, Datenbank, `.env`, systemd-Dienste und Tailscale.

[VERIFY] `verify_remote.py` zeigt den Kern grün. Eine Telegram-Testnachricht bringt **genau eine** Antwort (von der VM). "Das CEO-GPT läuft jetzt in der VM."

---

## TEIL 5: ALLES-VON-SELBST-TEST (der echte Always-on-Test)

> Der wichtigste Test. Am WINDOWS-HOST.

1. Den Windows-PC **hart neu starten** (oder kurz den Strom ziehen, wenn die BIOS-Einstellung getestet werden soll).
2. **Nicht einloggen, nichts anfassen.** Ein paar Minuten warten.
3. Vom Mac aus testen: `ssh <vm-user>@<kunde>-box` geht, der Telegram-Bot antwortet, `verify_remote.py` ist grün.

Das beweist die ganze Kette: Strom kommt → PC fährt hoch (BIOS) → Windows loggt automatisch ein → Hyper-V startet die VM (VMMS, ohne Login) → systemd fährt die Dienste hoch → Tailscale ist wieder da.

[VERIFY] Nach einem harten Neustart kommt alles von selbst wieder, ohne dass jemand etwas tut. **Das Always-on steht.**

---

## UPDATE CLAUDE.md (in der VM)

Trag in die `CLAUDE.md` der VM einen kurzen Abschnitt ein:

```markdown
## Standort: Windows-PC (Linux-VM)

Das CEO-GPT läuft in einer Ubuntu-VM (Hyper-V) auf einem immer-an Windows-PC, erreichbar per SSH über Tailscale. Alle systemd-Dienste laufen in der VM. Der Windows-Host ist nur das Chassis.

- Verbinden: `ssh {vm-user}@{kunde}-box` (Tailscale-SSH)
- Cockpit: `ssh -L 8787:localhost:8787 {vm-user}@{kunde}-box`, dann localhost:8787
- Setup-Modul: `module-installs/remote-windows`
- Playbook Fernzugriff: `references/windows-fernzugriff-onboarding.md`
```

[VERIFY] `grep -i remote-windows CLAUDE.md` zeigt den Eintrag.

---

## TROUBLESHOOTING

Die häufigsten Stolpersteine mit Fix stehen in `MODULE_DIR/references/troubleshooting.md` (Host-Voraussetzungen, Always-on, Hyper-V/VM, Tailscale/SSH, CEO-GPT in der VM). Kurzform der Klassiker:

- **VM kommt nach Neustart nicht hoch:** Auto-Startaktion auf "immer starten"? BIOS auf Power On? VMMS auf Automatisch?
- **PC hängt beim Boot:** BitLocker TPM+PIN (auf TPM-only stellen) oder kein Auto-Login.
- **Tailscale-SSH geht nicht:** läuft Tailscale wirklich in der VM (Linux), nicht auf Windows? Nie auf beiden.
- **Bot antwortet doppelt:** Setup läuft noch woanders, dort abschalten.
- **Weg N, App bricht beim Verbinden ab ("Verbinde dich einmal mit SSH in einem Terminal …"):** Fingerabdruck fehlt in `known_hosts` dieses Windows-Kontos. Einmal `ssh <benutzer>@<hostname>` im Terminal, `yes`.
- **Weg N, App kennt nur Linux/macOS:** Desktop-App zu alt. Auf mindestens 2.31226.0 aktualisieren.

---

## WAS ALS NÄCHSTES

*"Dein CEO-GPT läuft jetzt in einer Linux-Maschine auf deinem Windows-PC, der durchläuft, und du erreichst ihn von überall. Nach Stromausfall kommt alles von selbst wieder.*

*Wenn du das für einen Kunden gemacht hast, ist genau dieser Ablauf dein Onboarding für jeden Windows-Kunden: Host härten, VM anlegen, Fernzugriff, CEO-GPT rein.*

*Willst du gleich einen Probelauf von unterwegs machen, oder Pause?"*
