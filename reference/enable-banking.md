# Enable Banking: der zweite Weg, kurz erklärt

Diese Datei brauchst du nur, wenn eine deiner Banken **kein FinTS** kann. Also
bei Neobanken (Revolut, N26, Trade Republic, Wise), bei Konten außerhalb
Deutschlands, bei PayPal und bei den wenigen deutschen Banken ohne
FinTS-Zugang.

Das Einrichten dauert einmalig etwa zehn Minuten und kostet nichts.

---

## Warum es überhaupt einen Dritten braucht

Bei einer deutschen Filialbank meldest du dich mit deinen eigenen Zugangsdaten
selbst an. Das ist FinTS, und dafür braucht niemand eine Erlaubnis.

Neobanken haben so etwas nicht. Ihre offene Schnittstelle ist für **Unternehmen**
gedacht, nicht für Kunden, und der Zugang verlangt ein eIDAS-Zertifikat plus
den Status eines regulierten Zahlungsdienstleisters. Das ist für eine
Privatperson praktisch unerreichbar.

Der Gesetzgeber hat dafür einen zweiten Weg vorgesehen: den
**Kontoinformationsdienst**. Das ist ein lizenziertes Unternehmen, das im
Auftrag des Kunden Kontodaten abrufen darf. Du gibst den Zugriff einmal in
deiner Bank-App frei, danach kann der Dienst lesen. Ein Passwort gibst du ihm
nie.

Dieses Modul nutzt dafür **Enable Banking Oy** (Finnland, bei der
Finanzaufsicht FIN-FSA registriert). Deren Modus *restricted production* ist
dauerhaft kostenlos, weil er ausschließlich die Konten herausgibt, die du
selbst verknüpft hast. Genau das ist zugleich die Sicherheitsgrenze: fremde
Konten sind über deinen Zugang gar nicht erreichbar.

**Dein eigener Zugang, nicht unserer.** Du legst ihn auf deinen Namen an, die
Schlüssel liegen auf deinem Rechner, und niemand außer dir kann damit etwas
abrufen. Das passt zum Rest: dein KI-Mitarbeiter gehört dir.

---

## Was du am Ende hast

Zwei Dateien in `data/banking/psd2/`:

| Datei | Was drinsteht |
|---|---|
| `application_id.txt` | die Kennung deiner Anwendung, eine Zeile |
| der Schlüssel (`.pem`) | dein privater Schlüssel, mit dem sich dein Rechner ausweist |

Beide legt dieser Ablauf an. Sie liegen nur bei dir, gehen nie in ein Backup
nach draußen und stehen in keiner Konfigurationsdatei.

---

## Schritt für Schritt

### 1. Konto anlegen

Auf [enablebanking.com](https://enablebanking.com) registrieren. Kostenlos, es
wird keine Zahlungsinformation verlangt.

### 2. Anwendung anlegen

Im Control Panel eine neue *Application* anlegen. Drei Angaben entscheiden:

- **Environment: `PRODUCTION`.** Die Testumgebung liefert erfundene Daten.
- **Services: nur `AIS`.** AIS heißt Kontoinformation, also *lesen*. Wähle
  ausdrücklich **nicht** `PIS` (Zahlungsauslösung). Was du nicht freischaltest,
  kann auch kein Fehler und kein Angreifer später missbrauchen. Dieses Modul
  hat keinen einzigen Aufruf, der Geld bewegen könnte, aber die Grenze soll
  auch auf der anderen Seite gezogen sein.
- **Redirect-Adresse:** siehe nächster Punkt, das ist die einzige Stelle, an
  der man sich vertun kann.

### 3. Die Redirect-Adresse

Nach der Freigabe schickt die Bank deinen Browser auf eine Adresse zurück, und
in dieser Adresse steht der Code, den das Modul braucht.

**Empfohlen:** trag

```
http://localhost:8899/callback
```

ein. Beim Einrichten macht das Modul dann kurz einen Ein-Zweck-Lauscher auf,
fängt den Code selbst und beendet sich sofort wieder. Du musst nichts kopieren,
und es bleibt danach nichts offen.

**Falls dein Anbieter keine localhost-Adresse annimmt:** trag irgendeine
Adresse ein, die dir gehört. Der Browser landet dort auf einer Seite, die
womöglich gar nicht lädt. **Das ist normal und kein Fehler.** Entscheidend ist
allein die Adresszeile, dort steht `?code=...`. Diese Zeile fügst du im
Terminal ein, das Modul holt sich den Code selbst heraus.

### 4. Schlüssel erzeugen und ablegen

Das Control Panel bietet beim Anlegen der Application einen Schlüssel zum
Herunterladen an. Leg ihn zusammen mit der Application ID in
`data/banking/psd2/` ab. Die genauen Dateinamen nennt dir das Modul, wenn du

```
python scripts/banking/setup.py psd2-add
```

startest, ohne dass sie da sind. Der Ordner wird so angelegt, dass nur dein
Benutzerkonto hineinsehen kann.

### 5. Konten verknüpfen — der Schritt, den alle vergessen

Im Control Panel gibt es **„Link accounts"**. Erst damit gibst du frei, welche
deiner Konten überhaupt sichtbar sein dürfen.

**Ohne diesen Schritt liefert die Schnittstelle eine leere Kontoliste, ganz
ohne Fehlermeldung.** Das ist mit Abstand die häufigste Stolperfalle. Wenn das
Modul sagt „Freigabe steht, aber die Bank gibt kein Konto heraus", ist fast
immer genau das der Grund.

### 6. Bank anbinden

```
python scripts/banking/setup.py psd2-add
```

oder, bequemer, für alle Konten auf einmal:

```
python scripts/banking/setup.py assistent
```

---

## Was du wissen musst, bevor du dich wunderst

**Etwa vier Abrufe pro Tag.** Die Banken drosseln, wenn du nicht selbst gerade
davorsitzt. Deshalb läuft genau ein Abruf pro Tag im normalen Tageslauf. Wer
zwischendurch mehrfach von Hand anstößt, verbrennt das Tagesbudget und bekommt
danach eine Fehlermeldung, bis der nächste Tag anfängt. Das ist kein Defekt.

**Die Freigabe hält höchstens 180 Tage.** Danach fragt die Bank erneut. Das
Modul warnt zwei Wochen vorher, erneuert wird mit
`setup.py psd2-reauth <name>`.

**Die Historie reicht 90 Tage zurück.** Was davor liegt, gibt die Bank ohne
neue Freigabe nicht heraus. Ab dem ersten Lauf baut sich die Historie bei dir
lokal weiter auf, Tag für Tag.

**Nicht jedes Konto ist erreichbar.** Die Richtlinie deckt ausdrücklich nur
**Zahlungskonten** ab. Sparkonten, Festgeld und Depots fallen nicht darunter,
und daran ändert auch keine andere Anbindung etwas. Das ist mehrfach
nachgeprüft und keine Frage der Umsetzung. Für solche Konten pflegst du den
Saldo besser von Hand, als ihn in jeder Summe zu vergessen.

**Manche Bank verlangt dein Passwort in einem fremden Formular.** Die meisten
leiten dich auf ihre eigene Seite, dort gibst du deine Zugangsdaten wie immer
nur der Bank. Ein paar wenige machen es anders. Das Modul sagt es dir vor der
Auswahl und fragt nach, statt es beiläufig passieren zu lassen.

---

## Wenn es klemmt

| Was du siehst | Was es wirklich ist |
|---|---|
| „Freigabe steht, aber die Bank gibt kein Konto heraus" | „Link accounts" im Control Panel fehlt. Nachholen, dann `psd2-reauth`. |
| „Der Code wurde abgelehnt" | Der Ablauf hat drei Stationen (Bank → Enable Banking → deine Adresse). Nur der Code aus dem **letzten** Sprung gilt. Die Adresse ganz am Ende kopieren, nicht die von der Zwischenseite. |
| „Die Freigabe ist abgelaufen" | Die 180 Tage sind um. `setup.py psd2-reauth <name>`. |
| „Die Bank hat gedrosselt" | Tagesbudget verbraucht. Morgen läuft es wieder. Jetzt **keinen** zweiten Lauf hinterherschicken, das macht es nur schlimmer. |
| „Zugriff verweigert" | Die Application ist nicht aktiv, oder der Dienst AIS fehlt. Im Control Panel nachsehen. |
| Die Seite nach der Freigabe lädt nicht | Normal, wenn du keine localhost-Adresse eingetragen hast. Es zählt nur die Adresszeile. |
| „Die Bibliothek cryptography fehlt" | Nur der PSD2-Weg braucht sie: `pip install cryptography`. |

---

## Für den, der den Code liest

Kern liegt in `scripts/banking/psd2.py`, das Einrichten in
`psd2_setup.py`. Die Anmeldung läuft über ein selbst signiertes JWT (RS256,
eine Stunde gültig), es gibt keinen OAuth-Umweg und keinen Server, der etwas
zwischenspeichert.

Der Code ist aus dem CEO-GPT-Hauptsetup portiert (Stand 31.08.2026) und
existiert damit **zweimal**. Wer hier einen Fehler behebt, sieht bitte nach, ob
die andere Kopie denselben hat.
