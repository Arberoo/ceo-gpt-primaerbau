# Anpassungen PrimärBau (Windows) – Bankanbindung v1.3.1 + DataOS-Kern

Stand 16.10.2026, eingebaut für Arber. Das Modul ist für macOS geschrieben, das CEO-GPT läuft auf Windows 11 (PC „MUBA-PC2“, Konto `Muba`). Hier steht jede Abweichung vom Original, damit ein späteres Modul-Update sauber nachgezogen werden kann.

## Voraussetzung DataOS

DataOS war **nicht** installiert (kein `scripts/db.py`, `collect.py`, `generate_metrics.py`). Aus `module-installs/daten` wurde **nur der Kern** übernommen, ohne Workshop, ohne Beispiel-Sammler, ohne Wechselkurs-Starter:

| Datei | Herkunft | Änderung |
|---|---|---|
| `scripts/db.py` | daten | **Kein `journal_mode=WAL`**, dafür `timeout=30`. `data/data.db` gehört auch dem Mail-Abruf (IDLE-Dauerläufer, Modus `delete`); ein Umschalten hätte dessen Betrieb verändert. |
| `scripts/config.py` | daten | unverändert |
| `scripts/collect.py` | daten | unverändert |
| `scripts/generate_metrics.py` | daten | Ausgabe nach **`data/kennzahlen/key-metrics.md`** statt `context/group/` (Kontostände sind vertraulich, `context/` geht nachts zu GitHub, `data/` nicht). `section_banking` neu geschrieben (die im Modul erwähnte Vorlage lag nicht bei), Beträge im deutschen Format, nur `status='BOOK'`. Datenfrische ohne `mail_*`-Tabellen, Banking-Tabellen mit ihrer echten Datumsspalte. Schreiben mit `encoding="utf-8"`. |
| `scripts/requirements.txt` | neu | dotenv, requests, fints 5.0.0, mt-940, keyring |
| `scripts/set_secret.py` | – | **nicht** überschrieben, die vorhandene Fassung bleibt |

## Bankanbindung

| Mac (Original) | Windows (hier) |
|---|---|
| macOS-Schlüsselbund | **Windows-Anmeldeinformationsverwaltung**. Kein Code-Umbau: `keyring` wählt unter Windows von selbst `WinVaultKeyring`. Einträge: Dienst `ceogpt-banking`, Konto `<BLZ>:login` / `<BLZ>:pin`, nur für das Windows-Konto `Muba` lesbar. |
| `os.chmod(0o600/0o700)` | Neu `scripts/banking/rechte.py`: `schuetze()` setzt unter Windows echte Zugriffsrechte (Vererbung gebrochen, nur eigenes Konto + SYSTEM), auf Mac/Linux weiter `chmod`. Alle 8 `chmod`-Stellen in `session.py`, `config_store.py`, `psd2.py`, `tan.py` rufen jetzt `rechte.schuetze()` auf (markiert mit „Windows-Anpassung“). |
| Selbsttest prüft `st_mode == 0o600` | prüft über `rechte.nur_besitzer()` die echten Zugriffsrechte (Gegenprobe: ungeschützte Datei → schlägt an). |
| `reference/` im Modul | `welche-bank-welcher-weg.md` und `enable-banking.md` nach `reference/` im CEO-GPT kopiert (der Selbsttest und die Hinweise im Code erwarten sie dort). |
| launchd (`com.ceogpt.daten-collect`, `com.ceogpt.bank-collect`) | Windows-Aufgabe **„CEO-GPT PrimaerBau Daten-Abruf“**, täglich 06:30, als angemeldetes Konto (sonst kommt die Aufgabe nicht an die Anmeldeinformationen), nachholen wenn verpasst. Einrichten: `scripts/setup_daten_abruf_windows.ps1`, Lauf über `scripts/daten_abruf_windows.py`, Protokoll `data/daten_abruf.log`. |
| `.venv/bin/python` | `.venv\Scripts\python.exe -X utf8` |

Nur der **FinTS-Weg** ist eingerichtet (Volksbank). Der PSD2-Weg (Enable Banking) ist mitkopiert, aber ungenutzt; `cryptography` ist ohnehin schon installiert.

**Selbsttest:** 118 von 118 Prüfungen grün (16.10.2026).

## Bank

- **meine Volksbank Raiffeisenbank eG** (Rosenheim, Domain vb-rb.de). Im Verzeichnis unter BLZ 71160000 (früher „VR Rosenheim-Chiemsee“, GENODEF1VRR), FinTS-Server Atruvia `https://fints2.atruvia.de/cgi-bin/hbciservlet`. Die BLZ kommt beim Einrichten aus der IBAN.
- Anmeldung: VR-NetKey oder Alias + PIN, Freigabe in **VR SecureGo plus** (App-Freigabe, nichts abzutippen).
- Lehnt die Bank die mitgelieferte Produkt-Kennung ab (Fehler 9078 oder 3079): eigene, kostenlose FinTS-Registrierung bei der Deutschen Kreditwirtschaft (fints.org), dann `python scripts/set_secret.py BANK_FINTS_PRODUCT_ID`.

## Bei einem Modul-Update

1. Neue Dateien aus `scripts/` des Moduls drüberkopieren.
2. `rechte.py` behalten und die `chmod`-Stellen wieder auf `rechte.schuetze()` umbiegen (`grep -n "os.chmod" scripts/banking/*.py`).
3. Die Prüfung „Grafik ist nur für den Besitzer lesbar“ im Selbsttest wieder auf `rechte.nur_besitzer()` setzen.
4. Selbsttest laufen lassen, erst dann weiter.
