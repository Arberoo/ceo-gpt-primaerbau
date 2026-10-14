# Fernzugriff-Onboarding: CEO-GPT in einer Linux-VM auf einem Windows-PC

> Wie du einen Windows-PC als immer-an-Basis aufsetzt, darin eine Ubuntu-VM betreibst und
> sie von deinem Mac aus per Fernzugriff bedienst. Gilt 1:1 für jede Windows-Kunden-Installation.
> Schwester-Dokument der Mac-Variante: `module-installs/remote-mac/references/fernzugriff-onboarding.md`.
> Stand: 2026-06-15

## Begriffe und die drei Schichten

- **Mac** = dein Rechner, von dem aus du dich verbindest und administrierst.
- **Windows-Host** = der PC des Kunden, der durchläuft. Er ist nur das **Chassis**. Auf ihm selbst läuft kein CEO-GPT, nur die VM.
- **VM** = eine Ubuntu-Linux-VM, die im Windows-Host läuft. **Hier liegt alles, hier laufen die Dienste, hier arbeitet Claude Code.** Das ist faktisch dein Hetzner-Server, nur auf dem Büro-PC.

**Ziel:** Die VM ist ein vollwertiger Server. Du erreichst sie von überall per SSH, der Bot läuft 24/7, nach Stromausfall kommt alles von selbst wieder.

## Warum eine VM und nicht WSL2

WSL2 wäre der einfachere Weg, ist aber für einen unbeaufsichtigten Dauerläufer baulich schwach: es startet erst beim Login eines Nutzers, macht sich im Leerlauf selbst aus, und der Auto-Start nach Reboot ohne Login läuft in eine bekannte, offene Windows-Schwachstelle (Session 0). Eine Hyper-V-VM dagegen wird vom Windows-Systemdienst (VMMS, läuft als Systemkonto) **beim Boot ohne jeden Login hochgefahren**. Genau das braucht ein Kundengerät. Quellen im Recherche-Dokument.

## Warum Tailscale, und warum nur in der VM

SSH ist der Zugang selbst (Tür plus Schlüssel). Tailscale ist die Straße dorthin, wenn die VM hinter dem Router des Kunden steht und von außen keine erreichbare Adresse hat. Tailscale baut einen privaten, verschlüsselten Tunnel zwischen deinen Geräten, ohne dass am Kunden-Router irgendein Port geöffnet werden muss.

**Wichtig: Tailscale läuft NUR in der VM, nie zusätzlich auf dem Windows-Host.** Auf beiden Schichten gleichzeitig bricht es (Tailscale-Pakete passen nicht in Tailscale-Pakete, doppelte Verkapselung). Die VM bekommt ihre eigene Tailscale-Adresse und ihren eigenen MagicDNS-Namen und verhält sich wie jeder andere Linux-Server im Tailnet.

**Merksatz: SSH = Tür + Schlüssel. Tailscale = die Straße. Beides endet in der VM, nicht auf Windows.**

## Vorab entscheiden (4 Punkte)

1. **Windows-Edition?** Hyper-V braucht **Pro/Enterprise/Education**, nicht Home. Bei Home: auf Pro upgraden (empfohlen) oder VirtualBox + VBoxVmService als VM-Weg, oder als letzter Ausweg WSL2 mit Babysitting.
2. **Steht der PC bei dir oder beim Kunden?** Beim Kunden (Normalfall) brauchst du Tailscale. Im selben Netz reicht theoretisch die lokale IP, aber Tailscale ist trotzdem der saubere Weg.
3. **Wessen Tailscale-Konto?** Am saubersten dein eigenes **Agentur-Konto**, das Kundengerät per getaggtem Auth-Key dazuholen. Nicht dauerhaft im Privat-Tailnet des Kunden hängen.
4. **BitLocker auf der Windows-Systemplatte?** TPM-only lassen (entsperrt unbeaufsichtigt). Nie TPM+PIN, das verlangt bei jedem Neustart eine Eingabe und blockiert den Auto-Start.

---

## Teil A: Am Windows-Host (einmalig, direkt davor / per Screen-Share)

Die ersten Schritte passieren einmal direkt am PC. Du sitzt davor, oder ein kurzer Video-Call, in dem der Kunde seinen Bildschirm teilt.

### A1. Host prüfen
PowerShell als Administrator, dann `windows-host-check.ps1` aus dem Modul laufen lassen. Es sagt: Edition, RAM, ob Hyper-V geht, BitLocker-Modus, Schlaf-/Fast-Startup-Stand. Daraus ergibt sich der Weg.

### A2. Host als immer-an Chassis härten
`windows-host-harden.ps1` (als Administrator) setzt Schlaf/Ruhezustand/Fast-Startup aus und zähmt die Windows-Update-Reboots. Drei Dinge bleiben Handarbeit am Gerät:
- **BIOS/UEFI: "Restore on AC Power Loss" auf Power On.** Firmware-Sache, kein Windows-Schalter. So kommt der PC nach Stromausfall von allein hoch.
- **Auto-Login:** per Sysinternals **Autologon** (speichert das Passwort verschlüsselt als LSA-Secret, nicht im Klartext). Eigenes Konto mit wenig Rechten, nicht das Admin-Konto.
- **BitLocker** auf TPM-only prüfen (oder, wenn er ständig nach dem Wiederherstellungs-Schlüssel fragt, auf der Systemplatte aus). Schlüssel außerhalb des PCs sichern.

### A3. Hyper-V einschalten und die VM anlegen
Hyper-V aktivieren (einmal Neustart), dann `create-vm.ps1` legt die Ubuntu-VM an: Gen 2, 2 vCPU, 2 GB RAM, ~40 GB Platte, **Auto-Start beim Boot an**, Stopp-Aktion "herunterfahren". Ubuntu aus der ISO installieren (Standard, OpenSSH-Server gleich mit anhaken).

### A4. In der VM: Tailscale + SSH
In der VM (über die Hyper-V-Konsole oder per lokalem SSH):
```bash
curl -fsSL https://tailscale.com/install.sh | sh
sudo systemctl enable --now tailscaled
sudo tailscale up --ssh --hostname=<kunde>-box --auth-key=tskey-... --unattended
```
- `--ssh` schaltet Tailscale-SSH an (kein Schlüssel-Gefummel, Zugriff komplett über ACL).
- `--unattended` hält den Knoten ohne interaktiven Login oben.
- Der `--auth-key` ist ein vorab genehmigter, **getaggter** Schlüssel aus deinem Agentur-Tailnet (siehe Teil C).

---

## Teil B: Wie du dich vom Mac verbindest

### B1. Tailscale auf dem Mac
Gleiche App, dein Agentur-Konto. Dann sieht der Mac die VM.

### B2. Verbinden
```bash
ssh <user>@<kunde>-box        # MagicDNS-Name, geht von überall
```
Tailscale-SSH prüft die ACL, kein SSH-Schlüssel-Austausch nötig. Drei Wege, die Verbindung zu nutzen:
- **Terminal pur:** `ssh <user>@<kunde>-box`, dann `claude`.
- **Cursor / VS Code:** "Connect via SSH", Adresse eingeben, Ordner öffnen, `claude`.
- **Claude-Desktop-App:** "Add SSH connection", Host `<user>@<kunde>-box`, Port 22.

### B3. Das Cockpit (falls installiert)
Das Aufgaben-Cockpit läuft in der VM auf `localhost:8787`. Vom Mac per Tunnel:
```bash
ssh -L 8787:localhost:8787 <user>@<kunde>-box
```
dann im Browser `localhost:8787`. Genau wie beim Hetzner-Server.

---

## Teil C: Agentur-Tailnet und ACL (der saubere Multi-Kunden-Weg)

Jede Kundenbox kommt als **getaggter Knoten in DEIN Tailnet**, nicht in das Privat-Tailnet des Kunden, und nicht per "Sharing" (Sharing nimmt Tags und Tailscale-SSH weg).

1. **Getaggten, wiederverwendbaren Auth-Key erzeugen** im Tailscale-Adminbereich (Settings → Keys), Tag z.B. `tag:kunde-box`, "pre-approved" an. Der Knoten nimmt beim Beitritt sofort die Tag-Identität an, die ACL greift sofort, und Tag-Geräte laufen nicht ab (kein Offline-Fallen).
2. **ACL deny-by-default**, nur dein Gerät kommt an die Kundenboxen, Kundenboxen sehen sich nicht gegenseitig:

```jsonc
{
  "tagOwners": { "tag:kunde-box": ["autogroup:admin"] },
  "grants": [
    {
      "src": ["dein-user@deine-agentur.de"],   // oder group:operators
      "dst": ["tag:kunde-box"],
      "ip":  ["tcp:22"]                          // nur SSH, bei Bedarf erweitern
    }
    // Kein Grant zwischen tag:kunde-box → Boxen sind voneinander isoliert
  ],
  "ssh": [
    {
      "action": "accept",
      "src":    ["dein-user@deine-agentur.de"],
      "dst":    ["tag:kunde-box"],
      "users":  ["root", "ubuntu"]
    }
  ]
}
```

3. **MagicDNS** an, dann sprichst du die Box per Name an (`ssh kunde-box`) statt per IP.

Wenn der Kunde unbedingt will, dass die Box in **seinem** Tailnet liegt (er besitzt das Konto), dann lädt er dich am besten als Nutzer ein (nicht "teilen"), sonst verlierst du Tags und Tailscale-SSH und fällst auf normales `sshd` + SSH-Schlüssel zurück.

---

## Teil D: Kunden-Härtung (Pflicht bei Kundengeräten)

1. **Kein `--dangerously-skip-permissions` als Standard.** Claude erst fragen lassen, bevor es Destruktives tut.
2. **Secrets in die `.env`, nie in den Chat.**
3. **Tailscale-SSH plus ACL** statt offener Ports. Nichts hängt offen im Internet.
4. **Konten klären:** Claude-Abo, Telegram-Bot, API-Keys auf den Kunden.
5. **VM-Snapshot vor riskanten Schritten** (Hyper-V-Checkpoint), plus das verschlüsselte Tarball-Backup von innen wie auf dem Hetzner.

---

## Spickzettel (die ganze Sequenz)

**Am Windows-Host (einmal, davor, PowerShell als Admin):**
```powershell
.\windows-host-check.ps1            # Edition, RAM, Hyper-V, BitLocker
.\windows-host-harden.ps1           # Schlaf/Fast-Startup aus, Update zähmen
# BIOS: Restore on AC Power Loss = Power On  (manuell)
# Autologon (Sysinternals)                    (manuell)
.\create-vm.ps1 -VMName "CEO-GPT" -MemoryGB 2 -CpuCount 2 -DiskGB 40 -IsoPath C:\ubuntu.iso
```

**In der VM:**
```bash
curl -fsSL https://tailscale.com/install.sh | sh
sudo systemctl enable --now tailscaled
sudo tailscale up --ssh --hostname=<kunde>-box --auth-key=tskey-... --unattended
# dann CEO-GPT aufbauen (Module) und verify_remote.py
```

**Auf dem Mac:**
```bash
ssh <user>@<kunde>-box        # Test
ssh -L 8787:localhost:8787 <user>@<kunde>-box   # Cockpit
```

---

## Troubleshooting

- **"Connection refused" / kommt nicht rein:** VM aus oder Tailscale in der VM nicht oben. Per Hyper-V-Konsole prüfen: `sudo systemctl status tailscaled`, `tailscale status`.
- **Über Tailscale nicht erreichbar:** Box online im Tailscale-Adminbereich? ACL erlaubt dein Gerät? Auth-Key noch gültig (getaggte Keys laufen nicht ab, aber ein abgelaufener Erst-Key verhindert den Beitritt)?
- **VM kommt nach Neustart nicht hoch:** Hyper-V Auto-Start-Aktion auf "immer starten"? VMMS-Dienst auf Automatisch? BIOS "Restore on AC Power Loss" auf Power On?
- **VM hängt an BitLocker/PIN:** TPM+PIN statt TPM-only. Auf TPM-only stellen, sonst kommt der Host nicht unbeaufsichtigt hoch.
- **Tailscale-SSH geht nicht:** läuft Tailscale wirklich in der VM (Linux), nicht auf dem Windows-Host? Tailscale-SSH gibt es nur auf Linux/Mac-Knoten.
- **Bot antwortet doppelt:** läuft das Setup noch woanders (alter Server/Mac)? Nur eine Maschine darf den Bot-Token bedienen.
