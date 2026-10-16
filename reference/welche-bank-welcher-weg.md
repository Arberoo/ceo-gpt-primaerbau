# Welche Bank geht über welchen Weg

Nachschlagetabelle für den Anbinde-Assistenten und für den, der von Hand
entscheiden will. Der Assistent (`setup.py assistent`) macht das von allein,
diese Datei erklärt, warum er es so macht.

---

## Die Regel in einem Satz

**FinTS zuerst, wo es geht. PSD2 für alles andere. Was ein Zahlungskonto ist,
geht auf einem der beiden Wege — alles andere gar nicht.**

---

## Die Tabelle

| Was du hast | Weg | Warum |
|---|---|---|
| Deutsche IBAN, Bank bietet FinTS (Sparkasse, Volksbank, Commerzbank, DKB, ING, Comdirect …) | **FinTS** | Kein Dritter dazwischen, keine Drosselung, volle Historie |
| Deutsche IBAN, kein FinTS-Zugang hinterlegt | **PSD2** | Sonst wäre hier Schluss |
| Revolut, N26, Trade Republic, Wise, Vivid, bunq, Tomorrow | **PSD2** | Neobanken bieten kein FinTS an |
| PayPal | **PSD2** | Kein FinTS, keine IBAN |
| IBAN außerhalb Deutschlands (LU, AT, CY, NL …) | **PSD2** | FinTS ist ein deutscher Standard |
| Sparkonto, Sparbuch, Tagesgeld, Festgeld | **gar nicht** | Kein Zahlungskonto, fällt nicht unter die Richtlinie |
| Wertpapierdepot | **gar nicht** | Kein Zahlungskonto |
| Kryptobestände | **gar nicht** | Gibt keine Bankschnittstelle heraus |
| C24 Bank | **gar nicht** | Kein FinTS, und der Login läuft über QR-Code plus App-PIN, es gibt weder Benutzernamen noch Passwort |

---

## Warum FinTS die bessere Wahl ist, wo er geht

Vier Gründe, alle im Betrieb spürbar:

1. **Kein Dritter.** Deine Zugangsdaten bleiben zwischen dir und deiner Bank.
2. **Keine Drosselung.** PSD2 erlaubt etwa vier Abrufe pro Tag, FinTS nicht.
3. **Volle Historie.** PSD2 gibt ohne neue Freigabe nur 90 Tage heraus.
4. **Keine Abhängigkeit.** Der kostenlose PSD2-Modus ist ein Angebot eines
   Unternehmens, kein Naturgesetz.

**Der ehrliche Gegenpunkt:** FinTS ist zugleich der zerbrechlichere Weg. Jede
Bank setzt ihn ein bisschen anders um, und dieses Modul hat zwischen Mai und
August 2026 sieben Fehler an genau dieser Stelle gehabt — bei Sparkassen und
bei photoTAN-Banken. PSD2 ist beim Einrichten gleichförmiger. Die Regel bleibt
trotzdem FinTS zuerst, nur die Erwartung sollte realistisch sein.

---

## Was passiert, wenn gar nichts geht

Ein Sparkonto oder Depot lässt sich nicht anbinden. Das ist die Richtlinie,
nicht die Umsetzung, und es ist mehrfach nachgeprüft. Bitte nicht erneut
durchprobieren.

Der praktische Weg ist, den Saldo von Hand zu pflegen. Ein von Hand gepflegter
Wert ist ungenau, aber ein **fehlendes** Konto ist schlimmer: es fehlt in jeder
Summe, und niemand sieht, dass es fehlt.

---

## Wie der Assistent entscheidet

`assistent.weg_fuer()` bekommt eine IBAN, einen Banknamen oder eine Kontoart
und gibt immer drei Dinge zurück: den Weg, einen **Grund** und, wo nötig, einen
Hinweis. Ein „geht nicht" ohne Begründung wäre wertlos.

Die Reihenfolge der Prüfung:

1. Ist es eine Kontoart, die nirgends geht (Sparkonto, Depot …)? Dann Schluss,
   mit Begründung. **Das kommt zuerst**, denn eine Sparkonto-IBAN sieht aus wie
   jede andere.
2. Ist es eine IBAN? Nicht-deutsch → PSD2. Deutsch → in der FinTS-Registry
   nachschlagen, Treffer → FinTS, sonst PSD2.
3. Ist es ein Name? Bekannte Neobank → PSD2. Sonst PSD2 mit dem Hinweis, dass
   eine IBAN die bessere Angabe wäre, weil sich damit FinTS prüfen ließe.

Die Entscheidung fällt **beim Einrichten**, nicht im täglichen Abruf. Ein
automatischer Rückfall zur Laufzeit ist unmöglich, weil beide Wege einen
Menschen brauchen: FinTS eine TAN, PSD2 eine Freigabe in der Bank-App.
