"""
Banking - Anbinde-Assistent.

Fragt einmal ab, was der Kunde hat, entscheidet je Konto den passenden Weg und
richtet nacheinander ein. Fuer den Kunden gibt es damit EINEN Befehl, nicht
zwei Welten.

    python scripts/banking/assistent.py

DIE REGEL, KURZ: FinTS zuerst, wo es geht. Kein Dritter dazwischen, keine
Drosselung auf ~4 Abrufe pro Tag, volle Historie statt 90 Tage, und keine
Abhaengigkeit davon, dass ein kostenloses Fremdangebot bestehen bleibt. PSD2
ist der Weg fuer alles, was FinTS nicht kann.

WICHTIG, DAMIT NIEMAND ES FALSCH BAUT: die Entscheidung faellt HIER, beim
Einrichten, und nicht zur Laufzeit. Ein automatischer Rueckfall im Tageslauf
ist unmoeglich, weil BEIDE Wege einen Menschen brauchen -- FinTS eine TAN, PSD2
eine Freigabe in der Bank-App. Was hier einmal entschieden wurde, laeuft danach
ohne Eingabe durch.
"""
from __future__ import annotations

import re
import sys

from banking import config_store, registry

# Neobanken und Dienste, die es in Deutschland gibt, aber kein FinTS anbieten.
# Wird nur gebraucht, wenn jemand einen NAMEN statt einer IBAN nennt -- bei
# einer IBAN entscheidet ohnehin die Registry.
OHNE_FINTS = {
    "revolut", "n26", "trade republic", "traderepublic", "wise", "transferwise",
    "paypal", "vivid", "bunq", "monzo", "openbank", "tomorrow",
}

# Einzelne Institute, die auf KEINEM Weg gehen. Steht getrennt von KEIN_WEG,
# weil es hier nicht um die Kontoart geht, sondern um die konkrete Bank.
OHNE_JEDEN_WEG = {
    "c24": "C24 bietet kein FinTS an, und der Login laeuft ueber QR-Code plus "
           "PIN aus der App -- es gibt weder Benutzernamen noch Passwort, mit "
           "dem sich ein Zugang einrichten liesse.",
}

# Kontoarten, die auf KEINEM Weg erreichbar sind. PSD2 deckt ausdruecklich nur
# ZAHLUNGSkonten ab; Sparen, Festgeld und Depots fallen nicht darunter. Das ist
# die Richtlinie, nicht die Anbindung -- mehrfach nachgeprueft, bitte nicht
# erneut durchprobieren.
KEIN_WEG = {
    "sparkonto": "Sparkonten sind keine Zahlungskonten. PSD2 deckt sie nicht ab.",
    "sparbuch": "Sparbuecher sind keine Zahlungskonten. PSD2 deckt sie nicht ab.",
    "tagesgeld": "Tagesgeldkonten sind meist keine Zahlungskonten und fallen nicht unter PSD2.",
    "festgeld": "Festgeld ist kein Zahlungskonto. PSD2 deckt es nicht ab.",
    "depot": "Ein Wertpapierdepot ist kein Zahlungskonto und faellt nicht unter PSD2.",
    "aktien": "Ein Wertpapierdepot ist kein Zahlungskonto und faellt nicht unter PSD2.",
    "krypto": "Kryptobestaende gibt keine Bankschnittstelle heraus.",
}

WEG_FINTS = config_store.WEG_FINTS
WEG_PSD2 = config_store.WEG_PSD2
WEG_KEINER = "keiner"


def _norm(s):
    return re.sub(r"\s+", " ", (s or "").strip().lower())


def _ist_iban(text):
    kandidat = re.sub(r"\s+", "", (text or "")).upper()
    return bool(re.fullmatch(r"[A-Z]{2}[0-9A-Z]{13,32}", kandidat))


def weg_fuer(eingabe, registry_lookup=None):
    """Welcher Weg passt zu dieser Angabe? Reine Entscheidung, kein Netz.

    Nimmt eine IBAN ODER einen Banknamen ODER eine Kontoart. Gibt immer einen
    Grund mit -- ein 'geht nicht' ohne Begruendung ist wertlos."""
    lookup = registry_lookup or registry.lookup_by_iban
    roh = (eingabe or "").strip()
    text = _norm(roh)
    if not text:
        return {"eingabe": roh, "weg": WEG_KEINER, "grund": "leere Angabe"}

    # Kontoart zuerst: eine Sparkonto-IBAN sieht aus wie jede andere, aber
    # PSD2 gibt sie trotzdem nicht heraus.
    for wort, grund in KEIN_WEG.items():
        if wort in text:
            return {"eingabe": roh, "weg": WEG_KEINER, "grund": grund,
                    "hinweis": "Saldo laesst sich von Hand pflegen."}

    # Einzelne Institute, die nachweislich auf keinem Weg gehen. MUSS vor der
    # Neobank-Liste stehen, sonst wird C24 auf PSD2 geschickt und dem Kunden
    # ein Weg versprochen, den es nicht gibt.
    for marke, grund in OHNE_JEDEN_WEG.items():
        if marke in text:
            return {"eingabe": roh, "weg": WEG_KEINER, "grund": grund,
                    "hinweis": "Saldo laesst sich von Hand pflegen."}

    if _ist_iban(roh):
        kandidat = re.sub(r"\s+", "", roh).upper()
        if not kandidat.startswith("DE"):
            return {"eingabe": roh, "weg": WEG_PSD2, "iban": kandidat,
                    "land": kandidat[:2],
                    "grund": f"IBAN aus {kandidat[:2]}. FinTS ist ein deutscher "
                             f"Standard und greift dort nicht."}
        try:
            info = lookup(kandidat)
        except ValueError as e:
            return {"eingabe": roh, "weg": WEG_PSD2, "iban": kandidat, "land": "DE",
                    "grund": f"{e}"}
        if info.get("pintan_url"):
            return {"eingabe": roh, "weg": WEG_FINTS, "iban": kandidat, "land": "DE",
                    "blz": info["blz"], "bank": info.get("bank_name") or info["blz"],
                    "grund": f"{info.get('bank_name') or 'Diese Bank'} bietet FinTS an."}
        return {"eingabe": roh, "weg": WEG_PSD2, "iban": kandidat, "land": "DE",
                "blz": info.get("blz"), "bank": info.get("bank_name") or "",
                "grund": "Fuer diese Bankleitzahl ist kein FinTS-Zugang hinterlegt."}

    # Kein IBAN-Format: dann ist es ein Name.
    for marke in OHNE_FINTS:
        if marke in text:
            return {"eingabe": roh, "weg": WEG_PSD2, "bank": roh,
                    "grund": f"{roh} bietet kein FinTS an."}
    return {"eingabe": roh, "weg": WEG_PSD2, "bank": roh, "unsicher": True,
            "grund": "Ohne IBAN laesst sich kein FinTS-Zugang nachschlagen. "
                     "Mit IBAN wird FinTS geprueft, das waere der bessere Weg."}


def plan_fuer(eingaben, registry_lookup=None):
    return [weg_fuer(e, registry_lookup) for e in eingaben if (e or "").strip()]


def _zeile(p):
    if p["weg"] == WEG_FINTS:
        wie = "FinTS (PIN und TAN)"
    elif p["weg"] == WEG_PSD2:
        wie = "PSD2 (Freigabe in der Bank-App)"
    else:
        wie = "geht nicht"
    return f"  {p['eingabe']:28} {wie:32} {p['grund']}"


def plan_zeigen(plan):
    print("\n--- So wuerde ich vorgehen ---")
    for p in plan:
        print(_zeile(p))
    fints = sum(1 for p in plan if p["weg"] == WEG_FINTS)
    psd2_ = sum(1 for p in plan if p["weg"] == WEG_PSD2)
    keiner = sum(1 for p in plan if p["weg"] == WEG_KEINER)
    teile = []
    if fints:
        teile.append(f"{fints} ueber FinTS")
    if psd2_:
        teile.append(f"{psd2_} ueber PSD2")
    if keiner:
        teile.append(f"{keiner} gar nicht")
    print(f"\nMacht: {', '.join(teile) if teile else 'nichts'}.")
    if psd2_:
        print("Fuer den PSD2-Teil brauchst du einmalig einen kostenlosen")
        print("Enable-Banking-Zugang. Anleitung: reference/enable-banking.md")
    if keiner:
        print("Was nicht geht, kannst du als Saldo von Hand pflegen -- besser")
        print("als es in jeder Summe zu vergessen.")


def _eingaben_sammeln():
    print("=== Bankanbindung einrichten ===")
    print("\nWelche Konten willst du anbinden? Eine Angabe pro Zeile, am besten")
    print("die IBAN (dann kann ich pruefen, ob FinTS geht). Ein Bankname oder")
    print("'Sparkonto' geht auch. Leere Zeile beendet die Eingabe.\n")
    raus = []
    while True:
        try:
            zeile = input("  > ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not zeile:
            break
        raus.append(zeile)
    return raus


def durchfuehren(plan):
    """Den Plan abarbeiten, ein Konto nach dem anderen."""
    from banking import psd2_setup
    import banking.setup as fints_setup

    for p in plan:
        print("\n" + "=" * 60)
        print(f"{p['eingabe']}  ->  {p['grund']}")
        if p["weg"] == WEG_KEINER:
            print("Wird uebersprungen. " + p.get("hinweis", ""))
            continue
        weiter = input("Jetzt einrichten? (ja/nein/stop): ").strip().lower()
        if weiter in ("stop", "s"):
            print("Angehalten. Der Rest laesst sich jederzeit nachholen.")
            return
        if weiter not in ("ja", "j", "yes", ""):
            print("Uebersprungen.")
            continue
        try:
            if p["weg"] == WEG_FINTS:
                fints_setup.cmd_add(iban_vorgabe=p.get("iban"))
            else:
                psd2_setup.cmd_add(p.get("land"), p.get("bank"))
        except KeyboardInterrupt:
            print("\nAbgebrochen.")
            return
        except Exception as e:
            print(f"\nHat nicht geklappt: {type(e).__name__}: {e}")
            print("Der naechste Punkt geht trotzdem weiter.")


def abschluss():
    banks = config_store.load().get("banks", [])
    print("\n" + "=" * 60)
    if not banks:
        print("Es ist noch nichts eingerichtet.")
        return
    print(f"Eingerichtet: {len(banks)} Verbindung(en)")
    for b in banks:
        print(f"  {b.get('label') or config_store.bank_key(b)} "
              f"[{config_store.bank_weg(b)}]")
    print("\nNaechster Schritt: einmal 'python scripts/collect_banking.py' laufen")
    print("lassen und pruefen, dass Salden ankommen. Danach macht das der")
    print("Tageslauf von allein.")


def main():
    eingaben = _eingaben_sammeln()
    if not eingaben:
        print("Nichts angegeben, nichts geaendert.")
        return
    plan = plan_fuer(eingaben)
    plan_zeigen(plan)
    los = input("\nSo durchgehen? (ja/nein): ").strip().lower()
    if los not in ("ja", "j", "yes", ""):
        print("Abgebrochen, es wurde nichts geaendert.")
        return
    durchfuehren(plan)
    abschluss()


if __name__ == "__main__":
    sys.exit(main())
