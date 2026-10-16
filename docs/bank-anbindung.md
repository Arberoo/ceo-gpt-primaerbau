# Bankanbindung (Volksbank, FinTS, nur lesen)

> Das CEO-GPT holt einmal am Tag Kontostand und Umsätze der PrimärBau-Konten bei der meine Volksbank Raiffeisenbank und legt sie lokal ab. **Nur lesen**, das Modul kann keine Überweisung auslösen.

## Was wo liegt

| Was | Wo |
|---|---|
| Code | `scripts/collect_banking.py`, `scripts/banking/` (Modul `module-installs/bank-anbindung` v1.3.1) |
| DataOS-Kern | `scripts/db.py`, `collect.py`, `generate_metrics.py`, `config.py` |
| Login + PIN | Windows-Anmeldeinformationsverwaltung, Dienst `ceogpt-banking` (nie `.env`, nie Datei) |
| Bank-Einstellungen, FinTS-Sitzung | `data/banking/` (nur Konto `Muba` + SYSTEM haben Zugriff) |
| Kontostände, Umsätze | `data/data.db`, Tabellen `banking_accounts`, `banking_balances`, `banking_transactions`, `banking_sync_state` |
| Übersicht | `data/kennzahlen/key-metrics.md` (Abschnitt „Bank“), lokal, nicht in GitHub |
| Protokoll Tageslauf | `data/daten_abruf.log` |
| Windows-Abweichungen | `module-installs/bank-anbindung/ANPASSUNGEN.md` |

## Befehle (im CEO-GPT-Ordner, PowerShell)

```
.venv\Scripts\python.exe -X utf8 scripts\banking\selbsttest.py          # 118 Prüfungen ohne Bank
.venv\Scripts\python.exe -X utf8 scripts\banking\setup.py assistent     # Konto einrichten (Login, PIN, Freigabe)
.venv\Scripts\python.exe -X utf8 scripts\banking\setup.py list          # Was ist eingerichtet, wie lange gilt die Freigabe
.venv\Scripts\python.exe -X utf8 scripts\banking\setup.py reauth <BLZ>  # Erneuern (etwa alle 180 Tage)
.venv\Scripts\python.exe -X utf8 scripts\collect.py --sources banking   # Ein Abruf von Hand
.venv\Scripts\python.exe -X utf8 scripts\generate_metrics.py            # Übersicht neu erzeugen
powershell -ExecutionPolicy Bypass -File scripts\setup_daten_abruf_windows.ps1   # Täglichen Abruf einrichten
```

Einrichten und Erneuern brauchen **Luljeta am Handy** (Freigabe in VR SecureGo plus) und laufen in einem echten Terminal, weil die PIN verdeckt abgefragt wird. Der Mitarbeiter fragt nie im Chat nach PIN oder TAN.

## Tageslauf

Windows-Aufgabe „CEO-GPT PrimaerBau Daten-Abruf“, 06:30, holt nach, wenn der PC aus war. Fragt nie nach einer TAN. Verlangt die Bank eine neue Bestätigung, steht `needs_tan` in `banking_sync_state` und ein Hinweis in der Übersicht → `setup.py reauth <BLZ>` mit Luljeta.

## Wenn es klemmt

Die Tabelle „Wenn es klemmt“ in `module-installs/bank-anbindung/INSTALL.md`. Wichtigste Regeln: **kein TAN-Verfahren setzen**, bei einem Fehler **die PIN nicht mehrfach eingeben** (sperrt den Zugang), erst Server-Adresse und Produkt-Kennung prüfen, dann den Bankfehlercode recherchieren.
