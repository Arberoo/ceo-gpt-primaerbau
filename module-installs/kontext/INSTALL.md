# Kontext: Installation

<!-- MODUL-METADATEN
modul: kontext
version: v1
status: RELEASED
released: 2026-02-27
requires: [absicherung]
phase: 1
category: Kern-Module
complexity: medium
api_keys: 0
setup_time: 30-45 Minuten
-->

---

## FÜR CLAUDE (Anleitung für dich, das Programm)

Du hilfst dem Member, das **Gehirn** seines Mitarbeiters mit Kontext aufzubauen. Das ist der erste Schritt im CEO-GPT. Es verwandelt eine leere Vorlage in ein CEO-GPT, der ihn und sein Business kennt.

**Deine Rolle:** Du bist Interviewer, Stratege und Organisator. Du verstehst diese Person und ihr Business in der Tiefe und übersetzt das in strukturierte Kontext-Dateien, die jede zukünftige Sitzung tragen.

**Verhalten:**
- Lauf es als Gespräch. Frag nach wenn was schwammig ist
- Geh davon aus, dass die Person nicht technisch ist, außer sie sagt etwas anderes
- Feier kleine Fortschritte ("Dein Geschäfts-Kontext sieht solide aus, dein Mitarbeiter wird gleich deutlich brauchbarer")
- Hetz nicht durch das Interview, die Qualität des Kontexts bestimmt direkt die Qualität jeder späteren Antwort
- Sprich aufmunternd, der Member baut hier etwas Echtes
- Wenn etwas unklar ist, frag nach statt zu raten. Schlechter Kontext ist schlimmer als fehlender Kontext.

**Pacing:**
- Nicht durchrasen. Nach Meilensteinen kurz halten.
- Nach der Methoden-Wahl: "Gut. Damit fängt jetzt der zentrale Setup-Schritt deines CEO-GPT an."
- Nach dem Sammeln der Roh-Infos: "Ich habe ein Bild im Kopf. Ein paar Nachfragen noch, um die Lücken zu füllen."
- Nach dem Schreiben der Kontext-Dateien: "Das Gehirn deines Mitarbeiters hat jetzt Kontext. Wir aktualisieren jetzt deine CLAUDE.md und testen es."
- Nach dem /prime-Test: "Es läuft. Dein Mitarbeiter kennt jetzt dein Business. Jede Sitzung ab hier startet informiert."

**Qualitätsmaßstab:** Die Kontext-Dateien sollen so gut sein, dass eine frische Sitzung mit /prime sofort weiß:
1. Wer diese Person ist und was sie tut
2. Was das Business macht, wem es dient, wie es operiert
3. Was die aktuellen Prioritäten sind und wie Erfolg aussieht
4. Wie der aktuelle Stand bei Zahlen und laufenden Themen ist

Wenn der Kontext das nicht leistet, frag weiter.

---

## ÜBERSICHT (lies das dem Member vor dem Start vor)

Jetzt bauen wir den ersten Bereich vom Gehirn, nämlich Kontext. Das ist die Basis, auf der alles andere aufsetzt. Ohne den Kontext startet jedes Gespräch mit deinem Mitarbeiter bei null. Mit dem Kontext kennt dein Mitarbeiter dein Business, deine Rolle, deine Strategie und deine Zahlen, bevor du den ersten Satz tippst.

Das ist der Plan:

1. **Kontext einsammeln** über dich und dein Business, du wählst wie (Gespräch, Einfügen, oder Dokumente importieren)
2. **In vier strukturierte Dateien gießen**, die dein Mitarbeiter jede Sitzung liest
3. **Deine CLAUDE.md personalisieren**, damit das CEO-GPT dein Business spiegelt
4. **Testen** mit /prime, um zu sehen, dass alles greift

**Wenn wir fertig sind:** Jede neue Sitzung mit /prime startet informiert. Wer du bist, was dein Business macht, woran du gerade arbeitest, wo die Zahlen stehen. Kein erneutes Erklären, kein Kontext-Verlust.

**Setup-Zeit:** 30 bis 45 Minuten, je nachdem wie viel Kontext du schon hast
**Kosten:** kostenlos, keine API Keys, keine externen Dienste
**Worauf es ankommt:** wie tief und ehrlich du hier fütterst. Je mehr dein Mitarbeiter weiß, desto brauchbarer wird er.

---

## METHODEN-WAHL

Es gibt drei Wege, deinen Kontext reinzubekommen. Du kannst einen, zwei oder alle drei nutzen.

**Wie willst du den Kontext über dich und dein Business füttern? Such dir aus, was passt:**

### Option A: Dokumente importieren
"Leg Dateien in deinen `context/import/` Ordner, Businesspläne, Pitch Decks, Über-uns-Seiten, Notion-Exporte, ChatGPT-Memory-Exporte, Strategie-Docs, Excel-Tabellen, alles mit Kontext über dein Business. Ich lese das durch und nehme es als Basis."

**Passt gut für:** Leute, die ihr Business schon irgendwo dokumentiert haben. Je mehr du reinwirfst, desto weniger muss ich fragen.

### Option B: Interview im Gespräch
"Ich stelle dir Fragen zu deinem Business, deiner Rolle, deiner Strategie und deinen aktuellen Zahlen. Du redest einfach, ich strukturiere es."

**Passt gut für:** Leute, die ihren Kontext im Kopf tragen. Mit Voice-to-Text (z.B. Wispr Flow) geht das nochmal schneller, einfach reinsprechen."

### Option C: Text einfügen
"Kopier rein, was du hast, deine Webseite, dein LinkedIn-Profil, Strategie-Docs, interne Notizen, Investor Decks. Ich verarbeite alles."

**Passt gut für:** Leute, deren Kontext verteilt rumliegt. Schnapp dir die Stücke und schick sie blockweise rein.

---

**Frag:** "Was nimmst du? Du kannst mischen, z.B. Docs in den Import-Ordner werfen UND die Lücken im Gespräch füllen."

Notier dir die Wahl und mach entsprechend weiter.

**Hinweis am Rande:** "Falls du ChatGPT nutzt und Verlauf hast, geh auf Einstellungen → Datenkontrolle → Daten exportieren. Diesen Export legst du in den Import-Ordner, dann lerne ich aus deinen alten Gesprächen mit. Oder du fragst ChatGPT direkt: 'Erzähl mir alles, was du über mich und mein Business weißt', und fügst die Antwort hier ein."

---

## INSTALLATION

### CEO-GPT prüfen

Check, ob die Vorlage sauber steht:

```bash
ls context/
```

Du solltest sehen: `business-info.md`, `current-data.md`, `personal-info.md`, `strategy.md` und einen `import/` Ordner.

```bash
ls .claude/commands/prime.md
```

Der /prime Befehl muss da sein.

Wenn was fehlt, leg es an. Das sind die Vorlage-Dateien aus dem CEO-GPT-Template-ZIP.

[VERIFY] Alle 4 Kontext-Dateien existieren und der Import-Ordner ist da.

"Dein CEO-GPT steht. Jetzt füllen wir ihn mit Kontext über dich und dein Business."

---

### Kontext sammeln

Folg dem Weg, den der Member in der Methoden-Wahl gewählt hat.

#### Bei Dokument-Import (Option A):

Frag: "Hast du Dateien in `context/import/` gelegt? Falls noch nicht, wirf sie jetzt rein, ich warte."

Wenn Dateien da sind:

```bash
ls context/import/
```

Lies jede Datei im Import-Ordner. Bau dir bei jeder Datei ein Bild vom Business, von der Person, ihrer Rolle und ihrer Strategie.

Nach allen Imports sag dem Member: "Das habe ich aus deinen Dokumenten mitgenommen:" und gib eine Zusammenfassung. Dann: "Jetzt frag ich noch ein paar Sachen nach, um die Lücken zu schließen."

Geh zum Interview unten, aber überspring Fragen, die durch die Importe schon klar beantwortet sind.

#### Bei Gespräch (Option B):

Direkt zum Interview unten.

#### Bei Einfügen (Option C):

Frag: "Pack deinen ersten Textblock rein. Du kannst mehrmals nacheinander einfügen, sag einfach Bescheid, wenn du fertig bist."

Nimm alle Texte an. Nach jedem Block kurz quittieren, was angekommen ist. Wenn der Member fertig ist, fass zusammen und geh dann zu den Interview-Fragen für offene Punkte.

---

### Das Interview

Arbeite die Themenfelder durch. Du musst nicht jede Frage stellen, nutz dein Urteil basierend auf dem, was aus Importen und Texten schon klar ist. Bohr nach, wo Antworten dünn sind. Geh tief, wo es zählt.

**Start:** "Wir bauen jetzt das volle Bild. Ich frag dich zu vier Themen: dein Business, du selbst, deine Strategie, deine aktuellen Zahlen. Los?"

---

#### Thema 1: Dein Business (`business-info.md`)

Kernfragen, deck die alle ab:

- "Was macht dein Business? Erklär es so, als würdest du es jemandem erzählen, der noch nie davon gehört hat."
- "Wen bedient ihr? Was für Kunden oder Mandanten?"
- "Was verkauft ihr? Produkte, Dienstleistungen, Abos. Gib mir einen Überblick über euer Angebot und die ungefähren Preisrahmen."
- "Wie kommen Kunden zu euch? Was ist der Haupt-Weg, über den ihr Business macht?"
- "Wie groß ist das Ganze? Umsatzbereich, Teamgröße, wie lange schon am Markt?"
- "Was ist euer Geschäftsmodell? Wiederkehrender Umsatz, Projektgeschäft, Kurse, SaaS, Agentur, Beratung?"
- "Was unterscheidet euch vom Wettbewerb? Warum kommen Leute zu euch und nicht zu den anderen?"

Geh tiefer, wenn es passt:
- "Hast du mehrere Geschäftsbereiche oder Umsatzquellen? Erzähl mir zu jeder kurz was."
- "In welchem Markt seid ihr unterwegs? Trends, die euch gerade prägen?"
- "Wichtige Partnerschaften, Plattformen oder Abhängigkeiten, die ich kennen sollte?"
- "In welcher Phase steht ihr? Gerade gestartet, am Wachsen, am Skalieren, etabliert?"

**Mehrere Geschäfte erkennen:** Wenn der Member mehrere Geschäfte, Geschäftsbereiche oder Umsatzquellen erwähnt, merk dir das. Die Ordner-Struktur dafür kommt später.

---

#### Thema 2: Du selbst (`personal-info.md`)

- "Was ist deine Rolle? Geschäftsführer, Gründer, Operations, Marketing. Was machst du im Alltag konkret?"
- "Wofür bist du persönlich verantwortlich? Welche Entscheidungen landen auf deinem Tisch?"
- "Wo geht der Großteil deiner Zeit hin?"
- "Wofür willst du diesen CEO-GPT nutzen? Was wäre am wertvollsten, Analysen, Content, Strategie, Operations, Automatisierung, etwas anderes?"
- "Gibt es etwas zu deinem Hintergrund, deinen Skills oder deinem Arbeitsstil, das relevant ist? Bist du eher technisch oder nicht, arbeitest du allein oder mit Team?"

---

#### Thema 3: Deine Strategie (`strategy.md`)

- "Was sind gerade deine zwei, drei Top-Prioritäten? Was willst du dieses Quartal oder dieses Jahr erreichen?"
- "Wie sieht Erfolg aus? Wenn die nächsten drei bis sechs Monate gut laufen, was ist dann anders?"
- "Stehen größere Entscheidungen an? Abwägungen, Pivots, Sachen, wo du noch unsicher bist?"
- "Was ist deine Wachstumsstrategie? Wie willst du Umsatz hochziehen oder skalieren?"
- "Längerfristige Vision, wo willst du in zwei, drei Jahren stehen?"

---

#### Thema 4: Aktuelle Lage (`current-data.md`)

- "Was sind die wichtigen Zahlen in deinem Business? Umsatz, Kunden, Abonnenten, Pipeline, Conversion. Was du eben trackst."
- "Woher kommen die Zahlen? Stripe, Google Analytics, Excel, CRM, Bauchgefühl?"
- "Wie ist der Stand gerade? Laufende Projekte, jüngste Wins, Blocker, Sachen in Bewegung?"
- "Team-Auslastung. Bist du dünn besetzt, am Einstellen, am Auslagern?"

**Hinweis:** Diese Datei bleibt erstmal von Hand gepflegt, bis später die Daten dazukommen (die holt die Zahlen automatisch). Auch ein grober Tagesstand ist wertvoll. Sag dem Member: "Das ist erstmal ein statischer Stand. Sobald du die Daten einrichtest, wird das automatisch aus deinen echten Quellen aktualisiert."

---

**Nach dem Interview:** "Ich hab ein solides Bild. Ich gieß das jetzt in deine Kontext-Dateien."

---

### Kontext-Dateien schreiben

Schreib jetzt alle vier Kontext-Dateien aus dem, was du gesammelt hast. Halte dich an:

**Schreibstil:**
- Klare, scanbare Prosa, keine Textwüsten
- Headers, Bullet Points und Tabellen wo passend
- `business-info.md` in der dritten Person ("Das Unternehmen bietet...")
- `personal-info.md` in der zweiten Person ("Du bist Gründer und Geschäftsführer...")
- `strategy.md` in aktiver Sprache ("Der Fokus liegt auf...")
- Tabellen für Kennzahlen in `current-data.md`
- "Wie das zusammenhängt"-Blöcke aus den Vorlagen behalten, die helfen späteren Sitzungen
- Genug Detail, dass es nützt, aber kompakt. Pro Datei 30 bis 80 Zeilen, nicht 200.

**Pro Datei:**
1. Lies die existierende Vorlage-Datei
2. Ersetz den Platzhalter-Inhalt durch echten Inhalt
3. Halt die Struktur (Headers, Hinweise) intakt
4. Schreib die Datei

Schreib alle vier:
- `context/business-info.md`
- `context/personal-info.md`
- `context/strategy.md`
- `context/current-data.md`

[VERIFY] Nach dem Schreiben jede Datei nochmal lesen und prüfen, ob die Kernpunkte sauber drin sind.

"Deine Kontext-Dateien stehen. Ich les sie dir kurz zurück, dann sagst du, ob was schief ist."

Lies eine knappe Zusammenfassung jeder Datei vor. Frag: "Trifft das dein Business? Irgendwo falsch oder fehlt was?"

Wenn Korrekturen kommen, anpassen.

---

### Mehrere Geschäfte strukturieren (wenn nötig)

**Nur machen, wenn der Member mehrere Geschäfte, Geschäftsbereiche oder separate Umsatzquellen hat.**

Bei einem Business direkt zur nächsten Sektion springen.

Bei mehreren:

"Du hast mehrere Geschäfte erwähnt. Ich schlag dir eine Struktur vor, die jedes sauber trennt und deinem Mitarbeiter trotzdem den Gesamtblick gibt."

Vorschlag:

```
context/
├── group/                    # Die Dachebene über allem
│   ├── overview.md           # Was die Gruppe ist, wie die Geschäfte zusammenhängen
│   └── strategy.md           # Prioritäten auf Gruppen-Ebene
├── {business-1}/             # Erstes Business
│   ├── overview.md           # Was es macht, Team, Angebot
│   └── strategy.md           # Eigene Prioritäten
├── {business-2}/             # Zweites Business
│   ├── overview.md
│   └── strategy.md
├── personal-info.md          # Eine Datei, über dich quer über alle Geschäfte
├── current-data.md           # Kombinierte Zahlen (oder pro Business splitten)
└── import/                   # Roh-Docs bleiben hier
```

Frag: "Passt das für dein Setup? Was willst du anpassen?"

Bei OK die Struktur umbauen:
1. Ordner anlegen
2. Die bestehende `business-info.md` in pro-Business Overview-Dateien splitten
3. Eine Gruppen-Overview anlegen, wenn es eine verbindende Strategie gibt
4. `strategy.md` splitten oder lassen, je nachdem ob Strategien geteilt oder verschieden sind
5. Den /prime Befehl auf die neuen Pfade anpassen

[VERIFY] `ls -R context/` laufen lassen, prüfen ob die Struktur sauber ist.

Außerdem den /prime Befehl (`.claude/commands/prime.md`) updaten, damit er die neuen Pfade liest. Er soll alle Kontext-Dateien in der neuen Struktur einsammeln.

---

### CLAUDE.md aktualisieren

"Jetzt fassen wir deine CLAUDE.md an. Das ist die Master-Datei, die jede Sitzung als erstes geladen wird. Wir personalisieren sie auf dein Business."

Lies die existierende `CLAUDE.md` Vorlage.

Aktualisier folgende Abschnitte, lass die Gesamtstruktur intakt:

1. **"Was das hier ist"**: den generischen Absatz durch einen Einzeiler zum konkreten CEO-GPT ersetzen (z.B. "Das ist der strategische CEO-GPT von [Name] für [Geschäftsname], eine Agentur, die...")

2. **"Aufbau deines CEO-GPT"**: auf die echte Ordner-Struktur anpassen, vor allem wenn die Mehr-Geschäfte-Struktur aufgesetzt wurde. Neue Ordner oder Dateien eintragen.

3. **"Die Beziehung zwischen dir und deinem Mitarbeiter"**: Grundmuster lassen, aber die Geschäftsführer-Beschreibung personalisieren (z.B. "Geschäftsführer: [Name], Gründer von [Business]. Setzt Ziele rund um [Kernbereiche]...")

4. **"Sitzungs-Ablauf"**: unverändert, außer der Member will was anders

5. **Neuen "Kontext-Zusammenfassung"-Block einfügen** (nach Aufbau deines CEO-GPT):
   ```
   ## Kontext-Zusammenfassung

   **Business:** [Einzeiler]
   **Rolle:** [Rolle]
   **Aktueller Fokus:** [Top 1-2 Prioritäten]
   **Wichtigste Kennzahl:** [Nordstern-Kennzahl]
   ```

**Nicht machen:**
- Befehle-Block oder existierende Befehle löschen
- "Wichtige Regel: Diese Datei pflegen" rausnehmen
- Sitzungs-Ablauf rauswerfen
- CLAUDE.md mit vollem Geschäfts-Detail vollstopfen, das gehört in die Kontext-Dateien. CLAUDE.md ist nur die Orientierung.

[VERIFY] Die aktualisierte CLAUDE.md zurücklesen und prüfen, dass sie sauber, personalisiert und nicht aufgebläht ist.

---

## TEST

### Prime-Test

"Wir testen jetzt. Ich lass /prime laufen und schau, ob dein Mitarbeiter dein Business verstanden hat."

/prime ausführen.

Nach dem Prime soll die Zusammenfassung zeigen, dass dein Mitarbeiter versteht:
- Wer der Member ist
- Was das Business macht
- Aktuelle Prioritäten
- Wichtige Zahlen und Lage

**Wenn die Zusammenfassung stimmt:** Sag mit Pause und Wärme:
> *"Das Gehirn deines Mitarbeiters steht. Er kennt dich, dein Business und deinen Alltag jetzt. Stell ihm eine Frage, dann merkst du es selber."*

Jede neue Sitzung startet ab jetzt hier.

**Wenn was schief ist:** Die passende Kontext-Datei korrigieren und nochmal testen.

### Stichprobe

Frag den Member nach einer echten Frage:

"Stell mir eine Frage zu deinem Business, eine Strategie-Frage, eine Analyse, irgendwas, was du sonst von Hand erklären müsstest."

Zeig, dass dein Mitarbeiter klug antworten kann, weil der Kontext steht.

"Merkst du, ich brauchte kein Hintergrund-Briefing? So fühlt sich ein Mitarbeiter mit Gehirn an. Jede Sitzung ab jetzt startet so informiert."

---

## WAS ALS NÄCHSTES

*"Dein Gehirn hat jetzt Kontext. Ich kenne dich, dein Business, deine Strategie und deinen Alltag.*

*Als Nächstes kämen deine Zahlen. Ich verbinde mich mit deinen Datenquellen und hole jeden Morgen automatisch deine frischen Werte rein, damit du nicht mehr durch fünf Dashboards klicken musst. Setup-Zeit etwa 30 bis 60 Minuten.*

*Willst du gleich weitermachen, oder lieber Pause?"*

Wenn der Member "ja" oder "weiter" sagt, direkt `/install module-installs/daten` starten.
Wenn er Pause will, warm verabschieden und sagen dass er einfach `/install module-installs/daten` läuft wenn er soweit ist.

## Nützliche Gewohnheiten

Nach jedem größeren Geschäfts-Change (neues Produkt, neue Person im Team, Strategie-Shift, großer Win) die Kontext-Dateien nachziehen. Veralteter Kontext macht deinen Mitarbeiter veraltet. Aktueller Kontext macht ihn zum strategischen Partner. Auch alte Strategie-Dokumente, Pitch Decks und Notizen kannst du jederzeit in `context/import/` legen und deinen Mitarbeiter bitten, sie einzubauen.
