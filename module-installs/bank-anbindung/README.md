# Bankanbindung

> Dein KI-Mitarbeiter sieht deine Kontostände und Umsätze. Read-only, 100% lokal, kein Cloud-Dienst.

## Was das macht

- Verbindet deine Bankkonten read-only, auf **zwei Wegen**, damit auch das geht, was ein einzelner Standard nicht abdeckt.
- Holt täglich **Salden + Umsätze** und schreibt sie in deine lokale `data/data.db` — beide Wege in **dieselben** Tabellen, also eine Summe, nicht zwei.
- Macht die **Liquidität** sichtbar in `/prime` und im Daily Brief (Gesamtsaldo, Ein/Ausgang, Top-Empfänger).
- Läuft **komplett auf deinem Rechner**. Nichts geht in eine Cloud, die dir nicht gehört.

## Die zwei Wege

| Weg | Für wen | Wie du dich ausweist |
|---|---|---|
| **FinTS/HBCI** | deutsche Banken: Sparkasse, Volksbank, DKB, ING, Comdirect, Commerzbank, Deutsche Bank, Postbank … | dein Online-Banking-Login + PIN (im macOS-Schlüsselbund) und eine TAN |
| **PSD2** über Enable Banking | Neobanken (Revolut, N26, Trade Republic, Wise), Konten im EU-Ausland, PayPal, deutsche Banken ohne FinTS | eine einmalige Freigabe in deiner Bank-App, kein Passwort bei uns |

**Du musst das nicht auseinanderhalten.** Beim Einrichten fragt der Assistent,
welche Konten du hast, und entscheidet je Konto selbst. FinTS bekommt den
Vorzug, wo er geht: kein Dritter dazwischen, keine Drosselung, volle Historie.

**Was auf keinem Weg geht:** Sparkonten, Festgeld und Depots. Die sind keine
Zahlungskonten und fallen nicht unter die Richtlinie. Das Modul sagt dir das
beim Einrichten und schlägt vor, den Stand von Hand zu pflegen — ein fehlendes
Konto fehlt sonst in jeder Summe, ohne dass es auffällt.

## Was du brauchst

- Mac mit Claude Code (der macOS-Schlüsselbund wird für den FinTS-Weg gebraucht)
- **DataOS** installiert (dieses Modul nutzt dieselbe Datenbank und den Collector)
- Für **FinTS**: Online-Banking-Zugang mit aktiviertem FinTS/HBCI, Login + PIN und dein TAN-Gerät bzw. deine Banking-App
- Für **PSD2**: einen kostenlosen Enable-Banking-Zugang auf deinen Namen. Einmalig etwa zehn Minuten, Anleitung liegt bei (`reference/enable-banking.md`)

Kein TAN-Verfahren aussuchen: das Modul nimmt die Vorgabe deiner Bank. Rechne damit, dass die Bank schon **beim Anmelden** eine TAN will, nicht erst beim Kontoabruf.

## Wie installieren

1. Gib Claude Code diesen Ordner.
2. Sag: "Read INSTALL.md und richte das ein."
3. Folge mit: Claude fragt dich, welche Konten du hast, sagt dir für jedes, wie es angebunden wird, und geht sie dann mit dir durch.

**Setup-Zeit:** etwa 10 Minuten pro Bank, plus einmalig 10 Minuten für den Enable-Banking-Zugang, falls du ihn brauchst.

## Laufende Kosten

- **0 €.** FinTS ist kostenlos. Der PSD2-Weg läuft über den dauerhaft kostenlosen Modus von Enable Banking, mit deinem eigenen Zugang. Kein Abo.

## Was drin ist

| Datei | Zweck |
|-------|-------|
| `INSTALL.md` | Geführte Installation (Claude liest das) |
| `scripts/collect_banking.py` | Headless Collector (Salden + Umsätze) |
| `scripts/banking/` | FinTS-Logik (Registry, Keychain, Session, Client, TAN, Setup) |
| `scripts/banking/psd2.py` | Der zweite Weg: Enable Banking (Freigaben, Konten, Salden, Umsätze) |
| `scripts/banking/psd2_setup.py` | PSD2-Verbindung einrichten und erneuern |
| `scripts/banking/assistent.py` | Fragt ab, was du hast, und wählt je Konto den Weg |
| `scripts/banking/data/fints_institutes.properties` | Gebündelte BLZ-zu-Server-Datei (Auto-Auflösung) |
| `scripts/banking/selbsttest.py` | 115 Prüfungen ohne Bank und ohne Netz (vor dem Einrichten laufen lassen) |
| `reference/enable-banking.md` | Was Enable Banking ist und wie du deinen kostenlosen Zugang anlegst |
| `reference/welche-bank-welcher-weg.md` | Nachschlagetabelle: welche Bank läuft über welchen Weg |
| `config/com.ceogpt.bank-collect.plist` | Optionaler eigener Zeitplan (Standard: Piggyback auf den DataOS-Lauf) |

## Sicherheit + Recht

- **Read-only.** Das Modul kann nur lesen, keine Überweisungen auslösen.
- **FinTS: eigene Zugangsdaten, eigenes Konto, lokal.** Das ist rechtlich Selbstzugriff (wie StarMoney, MoneyMoney, Hibiscus), kein lizenzpflichtiger Kontoinformationsdienst.
- **PSD2: dein eigener Zugang bei einem lizenzierten Dienst.** Du legst ihn auf deinen Namen an, der Schlüssel liegt bei dir. Er ist auf „nur lesen" (`AIS`) beschränkt — Zahlungsauslösung wird gar nicht erst freigeschaltet.
- **Erneuerung alle ~180 Tage.** Beide Wege verlangen regelmäßig eine frische Bestätigung. Das Modul meldet sich rechtzeitig, der PSD2-Weg warnt zwei Wochen vorher.
- **Ein Abruf pro Tag beim PSD2-Weg.** Die Banken drosseln, wenn du nicht selbst davorsitzt. Das ist eine Eigenschaft des Wegs, kein Defekt.

## Änderungen

**Fassung 1.3 (31.08.2026)** — zweiter Anbindungsweg im selben Modul:

- **PSD2 über Enable Banking** kommt neben FinTS dazu. Damit sind Neobanken, EU-Ausland und PayPal anbindbar, die vorher gar nicht gingen. Beide Wege schreiben in **dieselben** Tabellen — ein Kunde mit Sparkasse und Revolut sieht eine Summe, nicht zwei.
- **Anbinde-Assistent** (`setup.py assistent`): fragt ab, was du hast, entscheidet je Konto den Weg und sagt bei jedem Konto, warum. Auch bei denen, die gar nicht gehen.
- `setup.py add` ist keine Sackgasse mehr: trifft es auf eine Bank ohne FinTS, bietet es den anderen Weg an, statt abzubrechen.
- Vier Spalten kamen additiv dazu (`weg`, `status`, `art`, `iban_klar` und die Sitzungs-Restlaufzeit). **Eine bestehende Installation merkt vom Umbau nichts**: kein Wert ändert sich, keine Historie geht verloren, nichts muss neu eingerichtet werden.
- Selbsttest von 52 auf **115 Prüfungen**, weiterhin ohne Bank und ohne Netz. Die neuen decken die fünf Datenfallen des PSD2-Wegs ab, die sonst still falsche Zahlen erzeugen: zwei Konten mit derselben IBAN, ein Konto ganz ohne IBAN, vorgemerkte Buchungen, fehlende Datumsfelder und mehrere Saldo-Arten am selben Tag.

**Fassung 1.1 (22.08.2026)** — vier Fehler behoben, die das Modul bei Sparkassen und Volksbanken unbrauchbar machten:

1. Leere Eingaben werden nicht mehr angenommen, und Login/PIN wandern erst **nach** einer erfolgreichen Verbindung in den Keychain. Vorher konnte ein leerer Anmeldename gespeichert werden, und der Fehler tauchte später als „Keine Credentials im Keychain" auf.
2. Das TAN-Verfahren wird nicht mehr **im laufenden Dialog** gesetzt (FinTS verbietet das).
3. Es wird überhaupt kein Verfahren mehr gesetzt, es gilt die Vorgabe der Bank. Die Auswahl vor den Dialog zu ziehen wäre genauso falsch, weil Sparkassen ihre Verfahren erst nach der Anmeldung nennen. Erzwingen geht weiter über `setup.py verfahren <BLZ> <ID>`.
4. Die **Anmelde-TAN** wird abgefragt. Sie liegt in `client.init_tan_response` und wurde vorher nie gelesen, der Dialog brach ab. Der headless-Abruf meldet sie jetzt sauber als `needs_tan` statt zu scheitern.

Dazu: `selbsttest.py` (damals 26 Prüfungen, ohne Bank und ohne Netz, inklusive statischer Sperre gegen die Rückkehr von Fehler 2).

**Fassung 1.0 (28.05.2026)** — erste Fassung.

Der Paketname bleibt bewusst `bank-anbindung-v1.zip`, damit der Link in der Modulbibliothek und im Modul-Katalog stabil bleibt. Die Fassung steht im `manifest.json` und im Kopf der `INSTALL.md`.

## Inhaltseingang

Bestmögliche Anbieterfrische ohne unnötige Abrufe oder TAN-Abfragen.

Einrichtungsstandard und Grenzen: [reference/dateneingang.md](reference/dateneingang.md).
Dieses Patch-Update korrigiert die Installationsvorgaben; zusätzliche Dienste werden
dadurch nicht automatisch eingerichtet. KI-Schritte sind separat zu aktivieren.
