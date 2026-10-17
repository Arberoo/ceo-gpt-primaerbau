# Scanner Brother → Scan-Eingang

**Gerät:** Brother MFC-J5740DW im Büro, WLAN-Netz, IP 172.17.1.134 (DHCP, Stand 17.10.2026; MAC AC:F2:3C:AD:51:38). Weboberfläche `https://172.17.1.134` (Admin-Passwort steht auf dem Aufkleber am Gerät, „Pwd“).
Nicht verwechseln: Der auf dem PC eingetragene „Brother MFC-L5750DW“ stammt aus einem anderen Netz und ist hier nicht erreichbar.

**Ziel:** `C:\PrimaerBau-Belege\Scan-Eingang` auf MUBA-PC2, freigegeben als `\MUBA-PC2\Scan-Eingang`.

## Einrichtung (einmalig, Arber)

1. PC: `scripts\scan_freigabe_einrichten.ps1` als Administrator. Legt das Konto `scanner` an (nur Schreibrecht im Scan-Eingang, nicht am Anmeldebildschirm), die Freigabe und eine Firewall-Regel nur für die Brother-IP. Die Netze bleiben „Öffentlich“.
2. Brother-Weboberfläche → **Scannen → Scan to Network** (Profil): Protokoll **SMB**, Profilname „PrimaerBau Belege“, Host `MUBA-PC2` (sonst die WLAN-IP des PCs), Zielordner `Scan-Eingang`, Dateiname „Scan“ mit Datum, Dateityp **PDF (mehrseitig)**, Auflösung 300 dpi, Farbe Auto, Authentifizierung Auto/NTLMv2, Benutzer `MUBA-PC2\scanner`.
3. Brother → **Administrator → Datum & Uhrzeit**: SNTP an (sonst schlägt die Anmeldung an der Freigabe fehl).
4. Testscan am Gerät: **Scannen → an Netzwerk → PrimaerBau Belege**.

## Danach

- Ändert sich die IP des Brother: Skript mit `-BrotherIP <neu>` erneut starten. Besser im Router eine feste Adresse für den Brother reservieren.
- `/prime` schaut in den Scan-Eingang und bietet an, neue Scans einzusortieren (Ablauf im Playbook Buchhaltung).
- Offen: Texterkennung für Bild-PDFs, Einsortieren ohne offene Sitzung (braucht den automatischen Claude-Lauf), Scan-Eingang in die Sicherung.
