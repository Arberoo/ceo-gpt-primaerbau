# Bankanbindung (FinTS + PSD2) — Modul-Installer

## Verbindlicher Standard für den Inhaltseingang · 1.3.1

**Vor der Einrichtung [reference/dateneingang.md](reference/dateneingang.md) lesen und anwenden.**
Empfohlen: Bestmögliche Anbieterfrische ohne unnötige Abrufe oder TAN-Abfragen.

Diese Vorgabe ergänzt die bisherige Anleitung: automatische Übernahme der ausgewählten
Nachrichten und Termine gehört zur Grundeinrichtung. Frühere optionale Collector-Phasen
beschreiben nur noch zusätzliche Historienkopien; deren Zeitpläne sind kein Echtzeitnachweis.
Die Anleitung zur Quelle nennt nötige Ergänzungen und Grenzen. Keine KI-Schritte allein
für den Empfang einschalten; zusätzliche KI-Kosten vor Aktivierung erklären und Zustimmung
einholen. Bereits passende Zustimmung gilt weiter.

**Versionstyp: Installationsstandard korrigiert.** Kein mit dieser Dokumentversion
automatisch ausgerollter Echtzeitdienst; tatsächlichen Inhaltseingang im Zielsetup abnehmen.


<!-- MODULE METADATA
module: bank-anbindung
version: 1.3.1
revision: 1.3
status: RELEASED
released: 2026-05-28
updated: 2026-08-31
requires: [data-os]
phase: 2
category: Gehirn
complexity: medium
api_keys: 0 (FinTS: Login/PIN im Keychain. PSD2: eigener kostenloser Enable-Banking-Zugang, Schluessel als Datei)
setup_time: 10 Minuten pro Bank (plus einmalig ~10 Minuten fuer den PSD2-Zugang, falls gebraucht)
-->

---

## FOR CLAUDE

Du hilfst dem User, seine Bankkonten read-only anzubinden, damit sein KI-Mitarbeiter Salden + Umsätze kennt. Regeln:

**Es gibt zwei Wege, und der User soll den Unterschied nicht lernen müssen:**
- **FinTS/HBCI** für deutsche Banken. Bevorzugt, wo es geht.
- **PSD2 über Enable Banking** für Neobanken, EU-Ausland, PayPal und deutsche Banken ohne FinTS.

Starte immer mit `setup.py assistent`. Der fragt ab, was der User hat, entscheidet je Konto den passenden Weg, zeigt den Plan und arbeitet ihn ab. Erklär dem User das Ergebnis in seinen Worten ("deine Sparkasse geht direkt, für Revolut brauchen wir einmal eine Freigabe in der App"), nicht die Technik dahinter.

**Die Entscheidung fällt beim Einrichten, nicht zur Laufzeit.** Ein automatischer Rückfall im Tageslauf ist unmöglich, weil beide Wege einen Menschen brauchen (TAN bzw. Freigabe in der Bank-App). Bau das nicht ein.

**Verhalten:**
- Nimm an, der User ist nicht-technisch. Erklär jeden Schritt in einfachem Deutsch BEVOR du ihn machst.
- Bank-Zugangsdaten sind sensibel. PIN immer über `getpass` (nie sichtbar), niemals in eine Datei oder ins `.env` schreiben, niemals zurück anzeigen.
- Feier kleine Wins ("Verbindung steht, das war der schwierigste Teil").
- Bei Fehlern keine Stacktraces dumpen, sondern in einem Satz erklären und den Fix vorschlagen.

**Selbstheilung (wichtig):**
- Wirft eine Bank beim Verbinden einen Fehler, ist das normal (jede Bank setzt FinTS leicht anders um). Recherchiere den konkreten Fehlercode + Bankname im Web (z.B. "FinTS 9942 <Bank>"), passe an (korrekte Server-URL, Segment-Version, ggf. eigene DK-Product-ID) und versuch es erneut. Brich nicht beim ersten Fehler ab.
- **Nicht am TAN-Verfahren drehen.** Das ist die naheliegendste und zugleich falscheste Fährte, sie hat hier schon zweimal Tage gekostet. Es gilt die Vorgabe der Bank. Siehe die Tabelle "Wenn es klemmt" ganz unten.

**Wichtige Konzepte:**
- **Read-only:** nur Salden + Umsätze. Keine Überweisungen.
- **180-Tage-SCA:** PSD2 verlangt etwa halbjährlich eine frische TAN. Der tägliche Abruf läuft headless; wenn die Bank eine TAN verlangt, meldet das Modul `needs_tan`, ohne zu crashen. Dann `setup.py reauth <BLZ>`.
- **Auto-Server-Auflösung:** Der User gibt nur seine IBAN. Die FinTS-Server-URL kommt aus der gebündelten Registry. Pro Bank ein eigener Server.
- **~4 Abrufe pro Tag (nur PSD2):** Die Banken drosseln, wenn der User nicht selbst davorsitzt. Deshalb genau ein Lauf pro Tag. Stoß den Sammler beim Einrichten **nicht** mehrfach an, sonst ist das Tagesbudget weg und der erste echte Lauf scheitert.
- **Was gar nicht geht:** Sparkonten, Festgeld und Depots sind keine Zahlungskonten und fallen unter keinen der beiden Wege. Sag das dem User klar und schlag vor, den Saldo von Hand zu pflegen — ein fehlendes Konto fehlt in jeder Summe, ohne dass es auffällt.

---

## PHASE 1: VORAUSSETZUNGEN

### Schritt 1: DataOS prüfen

Dieses Modul nutzt DataOS (gleiche Datenbank + Collector). Prüfe, dass diese Dateien im Workspace existieren:
- `scripts/db.py`, `scripts/collect.py`, `scripts/generate_metrics.py`

Fehlt DataOS, installiere zuerst DataOS (`module-installs/AIOS Data OS`).

### Schritt 2: Dateien kopieren

Kopiere aus diesem Modul in den Workspace:
- `scripts/collect_banking.py` -> `scripts/collect_banking.py`
- `scripts/banking/` -> `scripts/banking/` (inkl. `data/fints_institutes.properties`)

### Schritt 3: Abhängigkeiten installieren

Je nach Weg. Frag den User vorher, was er anbinden will, und installier nur, was er braucht.

**Für den FinTS-Weg** (deutsche Banken):
```
.venv/bin/pip install "fints==5.0.0" "mt-940>=4.30.0" "keyring>=24.0.0"
```

**Für den PSD2-Weg** (Neobanken, EU-Ausland, PayPal):
```
.venv/bin/pip install "cryptography>=41.0.0"
```

Trage ein, was du installiert hast, auch in `scripts/requirements.txt` (falls noch nicht vorhanden). Beide Wege importieren ihre Bibliotheken erst bei Bedarf: wer nur Revolut anbindet, braucht `fints` nicht, und umgekehrt. Fehlt eine, meldet der Sammler das für den betroffenen Weg und läuft für den anderen weiter.

**Optionale Einstellung:** `BANK_FINTS_PRODUCT_ID` in der `.env` überschreibt die mitgelieferte FinTS-Produkt-Kennung. Braucht man nur, wenn eine Bank die öffentliche Kennung mit 9078 oder 3079 ablehnt, dann ist eine eigene DK-Registrierung nötig. Das Modul liefert dafür bewusst keine `.env`-Vorlage mehr mit: Pakete enthalten grundsätzlich keine `.env`-Dateien.

### Schritt 4: Metrics-Sektion ergänzen

Wenn `scripts/generate_metrics.py` noch keine `section_banking`-Funktion hat: füge sie hinzu (Vorlage siehe die `section_banking`-Funktion in der Workspace-Version dieses Moduls) und registriere sie in der `SECTIONS`-Liste. Dadurch erscheint die Liquidität in `key-metrics.md` und im Daily Brief.

### Schritt 4b: Selbsttest laufen lassen

```
.venv/bin/python scripts/banking/selbsttest.py
```

115 Prüfungen, ohne Bank, ohne Netz, ohne Keychain-Zugriff. Muss grün sein, **bevor** echte Zugangsdaten ins Spiel kommen. Ist er rot, erst das reparieren: sonst debuggt man später mit echten Bankdaten etwas, das schon vorher kaputt war.

---

## PHASE 2: BANK ANBINDEN

### Schritt 5: Assistent starten

```
.venv/bin/python scripts/banking/setup.py assistent
```

Der Assistent fragt zuerst ab, **was der User überhaupt hat** (eine Angabe pro
Zeile, am besten IBANs), entscheidet je Konto den passenden Weg, zeigt den Plan
und arbeitet ihn dann Punkt für Punkt ab. Der User kann jederzeit einzelne
Punkte überspringen oder anhalten.

Zeig ihm den Plan in seinen Worten, bevor es losgeht. Zum Beispiel: „Deine
Sparkasse geht direkt über die Bank. Für Revolut brauchen wir einmal eine
Freigabe in deiner App. Dein Sparkonto geht auf keinem Weg, dafür tragen wir
den Stand später von Hand ein."

Einzeln geht auch weiterhin: `setup.py add` (FinTS) und `setup.py psd2-add`
(PSD2). `setup.py add` bietet von selbst PSD2 an, wenn die Bank kein FinTS
kann — es ist keine Sackgasse mehr.

### Schritt 5a: FinTS-Konten

Der User gibt ein:
1. **IBAN** des Kontos (daraus werden BLZ + Server automatisch aufgelöst).
2. **Online-Banking-Login** (Anmeldename / Legitimations-ID).
3. **PIN** (verdeckt via getpass).
4. **TAN**, sobald die Bank danach fragt (bei pushTAN: in der Banking-App freigeben, dann Enter).

Bei Erfolg: Konten + Testsaldo werden angezeigt, erst dann wandern Login und PIN in den Keychain und die Session wird gespeichert.

**Kein TAN-Verfahren auswählen.** Seit Fassung 1.1 setzt das Modul bewusst keins mehr, es gilt die Vorgabe der Bank. Wer trotzdem eins erzwingen muss, nimmt `setup.py verfahren <BLZ> <ID>`. Warum das so ist, steht im Kopf von `scripts/banking/tan.py`, und es ist kein Detail: die frühere Auswahl war der Grund, warum das Modul bei jeder Sparkasse scheiterte.

**Die TAN kommt oft schon fürs Anmelden**, nicht erst für den Kontoabruf. Das ist normal. Wenn der User sagt "in meiner App ist eine Freigabe aufgepoppt", ist genau das gemeint.

Wird die IBAN-Bank nicht in der Registry gefunden (leere URL): recherchiere die aktuelle FinTS-PIN/TAN-URL der Bank und gib sie ein. Findest du keine, bietet das Modul von selbst den PSD2-Weg an.

### Schritt 5b: PSD2-Konten (nur beim ersten Mal)

Braucht der User mindestens ein PSD2-Konto, muss **einmalig** ein kostenloser
Enable-Banking-Zugang stehen. Geh dafür mit ihm `reference/enable-banking.md`
durch. Dauert etwa zehn Minuten.

Die drei Punkte, an denen es sonst hakt:

1. **Services nur `AIS`** (Kontoinformation, also lesen). Ausdrücklich **kein**
   `PIS`. Was nicht freigeschaltet ist, kann auch nicht missbraucht werden.
2. **Redirect-Adresse.** Empfohlen ist `http://localhost:8899/callback` — dann
   fängt das Modul den Code beim Einrichten selbst, ganz ohne Kopieren. Nimmt
   der Anbieter keine localhost-Adresse an, geht auch jede andere; der Browser
   landet dann auf einer Seite, die womöglich nicht lädt (**das ist normal**),
   und der User fügt die Adresszeile ins Terminal ein.
3. **„Link accounts" im Control Panel.** Ohne diesen Schritt liefert die
   Schnittstelle eine **leere Kontoliste ohne jede Fehlermeldung**. Das ist mit
   Abstand die häufigste Stolperfalle. Wenn das Modul meldet „Freigabe steht,
   aber die Bank gibt kein Konto heraus", ist fast immer genau das der Grund.

Danach je Bank:

```
.venv/bin/python scripts/banking/setup.py psd2-add
```

Wie eine Bank bei Enable Banking genau heißt, sagt
`setup.py psd2-banken <LAND> [TEXT]`. Der Name muss exakt passen.

### Schritt 6: Weitere Banken (optional)

`setup.py assistent` erneut ausführen oder einzeln `add` / `psd2-add`. Mehrere
Banken auf beiden Wegen sind möglich, alle landen in denselben Tabellen.
`setup.py list` zeigt, was eingerichtet ist, mit Weg und Restlaufzeit.

---

## PHASE 3: ABRUF + ZEITPLAN

### Schritt 7: Ersten Abruf testen

```
.venv/bin/python scripts/collect.py --sources banking
.venv/bin/python scripts/generate_metrics.py
```

Zeig dem User den Banking-Abschnitt in `context/group/key-metrics.md` (Gesamtsaldo, Ein/Ausgang, Top-Empfänger).

**Genau EINEN Lauf.** Beim PSD2-Weg drosseln die Banken auf ~4 Abrufe pro Tag. Mehrfaches Anstoßen zum Ausprobieren verbrennt das Tagesbudget, und der erste echte Lauf scheitert dann mit einer Fehlermeldung, die wie ein Defekt aussieht.

**Vorgemerkte Buchungen nie in eine Summe.** Der PSD2-Weg liefert auch Buchungen, die noch nicht gebucht sind (`status = 'PDNG'`). Sie werden gespeichert, damit man sie sehen kann, dürfen aber in keiner Summe auftauchen — sonst stimmt der Saldo nicht mit dem der Bank überein. In jeder Auswertung also:

```sql
SELECT SUM(amount) FROM banking_transactions WHERE status = 'BOOK';
```

FinTS liefert ausschließlich gebuchte Umsätze und schreibt konstant `BOOK`, für den FinTS-Teil ändert sich dadurch nichts.

### Schritt 8: Zeitplan

Standard: **kein eigener Job nötig.** Der DataOS-Tageslauf (`com.ceogpt.daten-collect`) nimmt `collect_banking.py` automatisch mit.

Optional, falls ein eigener Zeitpunkt gewünscht: `config/com.ceogpt.bank-collect.plist` anpassen (Pfade einsetzen) und mit `launchctl load` aktivieren.

### Schritt 9: Re-Auth erklären

Sag dem User: etwa alle 180 Tage verlangt die Bank eine frische Bestätigung. Beide Wege melden das rechtzeitig, der PSD2-Weg warnt zwei Wochen vorher.

```
.venv/bin/python scripts/banking/setup.py reauth <BLZ>        # FinTS
.venv/bin/python scripts/banking/setup.py psd2-reauth <NAME>  # PSD2
```

`setup.py list` zeigt jederzeit, wie lange jede Freigabe noch gilt.

---

## ABSCHLUSS

Fass zusammen, was jetzt läuft: read-only Salden + Umsätze, lokal, täglich, sichtbar in `/prime` und Daily Brief. Sag dazu, welche Konten über welchen Weg laufen und welche **nicht** angebunden werden konnten (Sparkonto, Depot) — was fehlt, muss der User wissen, sonst hält er eine unvollständige Summe für vollständig.

Erinnere an die Erneuerung (~halbjährlich) und daran, dass nur gelesen und nie überwiesen wird. Beim PSD2-Weg gehört noch dazu: ein Lauf pro Tag, mehr geben die Banken nicht her.

---

## WENN ES KLEMMT (FinTS: die sieben bekannten Fälle)

Die ersten vier haben das Modul zwischen Mai und August 2026 bei **Sparkassen** unbrauchbar gemacht (behoben in Fassung 1.1), die nächsten zwei bei **photoTAN-Banken** wie Commerzbank und Deutsche Bank, der letzte bei **Firmenzugängen mit mehreren Konten** (beide behoben in Fassung 1.2). Taucht einer wieder auf, ist es eine Regression, kein Bank-Sonderfall.

| Was der User sieht | Was es wirklich ist |
|---|---|
| `Keine Credentials im Keychain` direkt nach dem Einrichten | Ein leerer Anmeldename wurde gespeichert, meist weil beim Einfügen ein Zeilenumbruch mitkam und die nächste Eingabeaufforderung ihn verschluckt hat. Fassung 1.1 nimmt leere Eingaben nicht mehr an und speichert erst nach erfolgreicher Verbindung. |
| `Cannot change TAN mechanism with a standing dialog` | Es wurde ein TAN-Verfahren **im laufenden Dialog** gesetzt. FinTS verbietet das. Fassung 1.1 setzt gar keins mehr. |
| Bankfehler **9340** (Signatur abgelehnt) | Ein TAN-Verfahren wurde **vor** dem Dialog gesetzt, obwohl die Bank vor der Anmeldung gar keine nennt. Es wurde also keins gesetzt und die Bank weist ab. Auch hier: nicht setzen, Vorgabe der Bank nehmen. |
| Dialog bricht ab, obwohl in der Banking-App eine TAN aufpoppte | Die **Anmelde-TAN** wurde nicht abgefragt. Sie liegt in `client.init_tan_response`, nicht in der Rückgabe von `get_sepa_accounts()`. Fassung 1.1 arbeitet sie als Erstes im Dialog ab. |
| Nur der Satz „Dies ist Ihre photoTAN Challenge.", **nichts zu scannen**, danach Bankfehler **9340** | Die Grafik-Challenge wurde nicht angezeigt. Eine Challenge hat drei Formen: Text, Flickercode (`challenge_hhduc`, chipTAN) und **Bild** (`challenge_matrix`, photoTAN/QR). Nur die ersten beiden wurden ausgewertet, das Bild fiel weg, und ohne Bild gibt es keine gültige TAN. Fassung 1.2 schreibt es heraus und öffnet es. **Das ist ein anderer Fall als die 9340-Zeile darüber**, auch wenn der Bankcode derselbe ist. |
| Nach `add`/`reauth` verlangt die Bank **bei jedem Abruf wieder eine TAN**, obwohl die Sitzung gültig gespeichert ist | `reauth` hat den gespeicherten Zustand nicht mitgegeben (`build_client(bank)` statt `from_data=…`). Ohne ihn ist die Kundensystem-Kennung unbelegt, python-fints fordert per `HKSYN3` eine **neue** an, und für die Bank ist das jedes Mal ein fremder Client. Ein fremder Client bekommt keine SCA-Ausnahme. Fassung 1.2 gibt den Zustand mit. |
| Die Bank gibt **nur eines von mehreren Konten** heraus, direktes Adressieren scheitert mit **9010** | Zwei Ursachen, beide behoben. (1) Die Kontenliste kam nur aus `get_sepa_accounts()`, und python-fints wirft dort jedes Konto weg, das die Bank nicht als SEPA-fähig markiert. Das passiert **lautlos**, es gibt keine Meldung. Jetzt werden zusätzlich die Nutzerdaten der Bank (UPD) gelesen und beide Listen zusammengeführt. (2) `9010` heißt „Konto nicht vorhanden oder unzulässig" und kommt fast immer von einer **unvollständigen Kontoadresse**. Zur Adresse gehört das **Unterkontomerkmal** (bei der Commerzbank z. B. `EUR100`), und das lässt sich **aus einer IBAN nicht ableiten**. Wer ein Konto aus der IBAN baut, wird abgewiesen. Es kommt jetzt aus der Bank und wird nie geraten. |

**Beim Suchen die Reihenfolge einhalten:** erst Server-URL und Product-ID prüfen, dann den Bankfehlercode recherchieren. Ein TAN-Verfahren **nie auf Verdacht** setzen, das war schon zweimal die falsche Fährte.

**Die Meldung `Refusing to use PIN after block` ist nie die Ursache.** Schlägt die Anmeldung fehl, sperrt `python-fints` die PIN im Speicher; beim Schließen des Dialogs wird erneut darauf zugegriffen und diese zweite Meldung **überschreibt die erste** samt echtem Bankcode. Erschwerend deutet `python-fints` **jeden** 9xxx-Code vor dem Öffnen des Dialogs als „PIN wrong?" — das ist eine Annahme der Bibliothek, keine Auskunft der Bank (`client.py`, Kommentar „Assume all 9xxx errors … refer to the PIN"). **Die PIN deswegen nicht mehrfach neu eingeben, das sperrt den Zugang.** Stattdessen den echten Bankcode suchen.

**`revision: 1.2` (26.08.2026)**, Anlass war ein Fehlerbericht aus einer Kundeninstallation (Commerzbank, photoTAN und ein Firmenzugang mit fünf Konten).


## WENN ES KLEMMT (PSD2)

Diese Fälle sind keine Defekte, sondern die Eigenheiten des Wegs. Die volle
Erklärung steht in `reference/enable-banking.md`.

| Was der User sieht | Was es wirklich ist |
|---|---|
| „Freigabe steht, aber die Bank gibt kein Konto heraus" | **„Link accounts" im Control Panel fehlt.** Der kostenlose Modus gibt ausschließlich selbst verknüpfte Konten heraus. Nachholen, dann `psd2-reauth`. Mit Abstand der häufigste Fall. |
| „Der Code wurde abgelehnt" | Der Ablauf hat **drei** Stationen (Bank → Enable Banking → eigene Adresse). Nur der Code aus dem letzten Sprung gilt. Der User hat die Adresse der Zwischenseite kopiert. |
| „Die Freigabe ist abgelaufen" | 180 Tage um. `setup.py psd2-reauth <name>`. |
| „Die Bank hat gedrosselt" | Tagesbudget (~4 Abrufe) verbraucht. **Keinen zweiten Lauf hinterherschicken.** Morgen läuft es wieder. |
| „Zugriff verweigert" | Application nicht aktiv, oder der Dienst `AIS` fehlt. |
| Die Seite nach der Freigabe lädt nicht | Normal, wenn keine localhost-Adresse eingetragen ist. Es zählt allein die Adresszeile mit `?code=`. |
| „Die Bibliothek cryptography fehlt" | Nur der PSD2-Weg braucht sie: `pip install cryptography`. Der FinTS-Weg läuft weiter. |
| Bank taucht in der Suche nicht auf | Der Name muss **exakt** dem Eintrag bei Enable Banking entsprechen. `setup.py psd2-banken <LAND> <TEXT>` zeigt die Schreibweise. |

**Was auf keinem Weg geht:** Sparkonten, Festgeld und Depots sind keine
Zahlungskonten und fallen nicht unter die Richtlinie. Das ist mehrfach
nachgeprüft — bitte nicht erneut durchprobieren. Saldo von Hand pflegen.

**`revision: 1.3` (31.08.2026)**: zweiter Anbindungsweg (PSD2 über Enable
Banking) im selben Modul, dieselben Tabellen, plus der Anbinde-Assistent.
