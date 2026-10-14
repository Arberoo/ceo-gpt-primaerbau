# Remote-Windows: Stolpersteine und Fixes

> Die Dinge, die bei "CEO-GPT in einer Linux-VM auf einem Windows-PC" erfahrungsgemäß schiefgehen,
> jeweils mit dem Fix. Aus der Recherche (`plans/2026-06-15-remote-windows-pc-recherche.md`).

## Vor dem Bau: Host-Voraussetzungen

**Windows Home hat kein Hyper-V.**
Hyper-V braucht Pro/Enterprise/Education. Auf Home schlägt das Aktivieren fehl. `windows-host-check.ps1` meldet das vorab.
→ Fix: auf Pro upgraden (günstig, lohnt für die Robustheit), oder VirtualBox + VBoxVmService (eine Fremdkomponente mehr, startet die VM ebenfalls ohne Login), oder als letzter Ausweg WSL2 mit Babysitting.

**Virtualisierung im BIOS aus.**
`Get-ComputerInfo` zeigt `HyperVRequirementVirtualizationFirmwareEnabled = False`. Hyper-V startet keine VM.
→ Fix: im BIOS/UEFI Intel VT-x bzw. AMD-V (oft "SVM Mode") einschalten.

**Zu wenig RAM.**
Bei 4 GB Gesamt-RAM wird es eng, wenn die VM 2 GB nimmt und Windows den Rest will.
→ Fix: VM auf 1,5-2 GB, am besten Host mit 8 GB+. Bei wirklich knappem Gerät einen dedizierten Mini-PC mit Ubuntu direkt erwägen (ohne Windows-Schicht).

## Always-on: PC kommt nach Stromausfall nicht von selbst hoch

**BIOS steht auf "Power Off" nach Stromausfall.**
Häufigste Ursache. Das ist eine Firmware-Einstellung, kein Windows-Schalter, und steht auf vielen Consumer-Boards default auf "aus bleiben".
→ Fix: BIOS/UEFI → "Restore on AC Power Loss" / "After Power Failure" → **Power On**. Kleine USV gegen kurze Einbrüche.

**Kein Auto-Login, der PC hängt im Anmeldebildschirm.**
Ohne Auto-Login fährt zwar Windows hoch, aber alles, was eine Sitzung braucht, startet nicht.
→ Fix: Sysinternals **Autologon** (verschlüsselt als LSA-Secret, nicht Klartext-Registry). Eigenes Konto mit wenig Rechten.

**BitLocker verlangt eine PIN beim Boot.**
TPM+PIN blockiert den unbeaufsichtigten Start, der PC hängt vor Windows.
→ Fix: BitLocker auf **TPM-only** stellen (entsperrt transparent). Wenn er trotzdem ständig den Wiederherstellungs-Schlüssel will (z.B. nach BIOS-Update), auf der Systemplatte BitLocker aus. Schlüssel außerhalb sichern.

**Fast-Startup macht Kaltstarts inkonsistent.**
"Herunterfahren" ist mit Fast-Startup ein Fake-Ruhezustand, nach echtem Stromausfall verhalten sich Treiber/NIC mal anders.
→ Fix: `powercfg /hibernate off` (schaltet Fast-Startup gleich mit aus). Macht `windows-host-harden.ps1`.

## Hyper-V / VM

**VM startet nicht beim Boot.**
→ Fix: Pro-VM "Automatische Startaktion" auf **"Diese VM immer automatisch starten"** (`Set-VM -AutomaticStartAction Start`). Den Hyper-V-Dienst **VMMS** auf Startart "Automatisch" und Anmeldung "Lokales Systemkonto" prüfen (dessen Abhängigkeit WMI/Winmgmt ebenfalls Automatisch).

**Gen-2-VM bootet die Ubuntu-ISO nicht (Secure Boot).**
Gen 2 hat Secure Boot an, mit dem Microsoft-Windows-Template startet Ubuntu nicht.
→ Fix: `Set-VMFirmware -VMName <name> -SecureBootTemplate MicrosoftUEFICertificateAuthority` (das ist das Template für Linux), oder Secure Boot aus. `create-vm.ps1` setzt das Linux-Template automatisch.

**VM speichert beim Host-Neustart den Zustand statt sauber herunterzufahren.**
Ein gespeicherter Zustand kann nach Updates stale sein.
→ Fix: Stopp-Aktion auf **"Herunterfahren"** (`Set-VM -AutomaticStopAction ShutDown`). Macht `create-vm.ps1`.

**Hyper-V kollidiert mit VirtualBox/VMware.**
Aktiviertes Hyper-V setzt Windows in den Hypervisor-Modus, andere Hypervisoren laufen dann nicht mit voller Geschwindigkeit.
→ Fix: auf einem Gerät ein Lager wählen. Hyper-V (Pro) oder VirtualBox (Home).

## Fernzugriff (Tailscale / SSH)

**`tailscale up` schlägt fehl: "System has not been booted with systemd".**
In der VM ist systemd nicht aktiv (sollte es in einer echten VM aber sein, anders als bei WSL2).
→ Fix: in einer normalen Hyper-V-Ubuntu-VM ist systemd PID 1, das tritt nicht auf. Falls doch: prüfen, dass es eine echte VM ist und nicht versehentlich WSL.

**Tailscale-SSH antwortet nicht.**
→ Fix: läuft Tailscale wirklich **in der VM** (Linux), nicht auf dem Windows-Host? Tailscale-SSH gibt es nur auf Linux/Mac. Auf dem Windows-Host installiertes Tailscale kann kein SSH anbieten und kollidiert obendrein.

**Tailscale auf Host UND in der VM, nichts geht.**
Doppelte Verkapselung.
→ Fix: Tailscale auf dem Windows-Host deinstallieren, nur in der VM laufen lassen.

**MagicDNS-Name löst nicht auf.**
→ Fix: in der VM `/etc/resolv.conf` auf `100.100.100.100` zeigen lassen (systemd-resolved-Eigenheit), MagicDNS im Adminbereich an.

**Box fällt nach einer Weile offline.**
→ Fix: `tailscale up` mit `--unattended` gesetzt? Auth-Key getaggt (getaggte Geräte laufen nicht ab)? Der Knoten darf im Adminbereich nicht "key expiry" haben.

## CEO-GPT in der VM

**Bot antwortet doppelt.**
Das Setup läuft noch woanders (alter Mac/Server), zwei Prozesse am selben Bot-Token.
→ Fix: alle anderen Instanzen stoppen. Genau eine Maschine bedient den Bot.

**Dienste laufen nicht nach VM-Neustart.**
→ Fix: systemd-Units mit `systemctl enable` (nicht nur `start`) aktiviert? `systemctl list-unit-files 'ceo-gpt-*'` muss "enabled" zeigen. `verify_remote.py` deckt das auf.

**`pip install` bricht ab, Python-Version.**
→ Fix: in der VM Python 3.12 sicherstellen, venv damit neu bauen. Gleiche Hauptversion wie auf dem Quell-System.

## Weg N: Claude-Desktop-SSH auf einen Windows-Rechner

**App meldet, das Ziel müsse Linux oder macOS sein / Sitzung bricht sofort ab.**
Desktop-App zu alt oder Doku-Stand veraltet. Windows-Ziele sind seit 2.31226.0 (08.10.2026) unterstützt.
→ Fix: auf jedem Gerät Claude Desktop auf mindestens 2.31226.0 aktualisieren. Nicht auf WSL/VM ausweichen.

**„Verbinde dich einmal mit SSH in einem Terminal …“, meist fehlt der Schlüssel des Hosts.**
Das eingebaute SSH der App unter Windows fragt nicht selbst nach dem Fingerabdruck.
→ Fix: im selben Windows-Konto, unter dem die App läuft, einmal `ssh <benutzer>@<hostname>` und `yes`. Gilt je Gerät und je Benutzer.

**Schlüssel wird ignoriert, App fragt trotzdem nach Passwort oder scheitert.**
Schlüssel mit Passphrase überspringt die App still. Bei Admin-Konten liest Windows-OpenSSH den Schlüssel nur aus `C:\ProgramData\ssh\administrators_authorized_keys`.
→ Fix: Passwort-Anmeldung nutzen oder Schlüssel ohne Passphrase/über den SSH-Agenten, bei Admins in die richtige Datei.

**App hängt oder kann keine Dateien übertragen.**
→ Fix: `windows-ssh-check.ps1`: SFTP-Subsystem an, `MaxSessions` nicht 1, Standard-Shell cmd.exe oder PowerShell (nicht WSL-bash/Git Bash), git vorhanden, > 1 GB frei.

**NAS-Laufwerk fehlt in der SSH-Sitzung, am Bildschirm ist es da.**
SSH-Sitzungen (vor allem mit Schlüssel) bekommen keine weitergereichten Anmeldedaten und keine verbundenen Laufwerksbuchstaben.
→ Fix: UNC-Pfad nutzen oder Zugang ausdrücklich mitgeben; in der ersten Sitzung testen. Branchensoftware mit eigenem SQL-Login ist nicht betroffen, installiertes Outlook per COM schon (Microsoft-API stattdessen).

**Mit `localhost` meldet die App, man solle die lokale Umgebung nehmen.**
Nur ein Hinweis. → Fix: zum Testen gleich den echten Hostnamen eintragen, der auch auf den Arbeitsgeräten genutzt wird.

**Remote Control startet nicht auf dem Ziel-PC.**
→ Fix: dort mit `/login` anmelden; ein Setup-Token reicht für Remote Control nicht. Erste Rückfragen einmal im Terminal bestätigen.

**Cockpit auf dem iPhone ohne Standort/Mitteilungen.**
Fehlendes HTTPS. → Fix: MagicDNS + HTTPS-Zertifikate im Tailscale-Admin an, `tailscale serve --bg <port>`. Eigene Domain braucht ein eigenes Zertifikat (Tailscale-Zertifikate gelten nur für `*.ts.net`).
