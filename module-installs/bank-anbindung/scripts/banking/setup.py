#!/usr/bin/env python3
"""
Banking - Interaktives Setup (Claude-gefuehrt).

Befehle:
    python scripts/banking/setup.py assistent     # Gefuehrt: was hast du? -> passender Weg je Konto
    python scripts/banking/setup.py add           # Neue Bank anbinden (IBAN, Login, PIN, TAN)
    python scripts/banking/setup.py reauth <BLZ>  # Session erneuern (180-Tage-SCA)
    python scripts/banking/setup.py list          # Eingerichtete Banken zeigen
    python scripts/banking/setup.py remove <KEY>  # Bank entfernen (BLZ oder PSD2-Name)
    python scripts/banking/setup.py verfahren <BLZ> [ID]   # TAN-Verfahren zeigen/erzwingen

    python scripts/banking/setup.py psd2-add [LAND] [NAME] # Bank ueber PSD2 anbinden
    python scripts/banking/setup.py psd2-reauth <NAME>     # PSD2-Freigabe erneuern (180 Tage)
    python scripts/banking/setup.py psd2-banken <LAND> [TEXT]  # Wie heisst die Bank dort genau?

ZWEI WEGE, EIN MODUL (seit 2026-08-31):
  * FinTS/HBCI fuer deutsche Banken. Bevorzugt, wo es geht: kein Dritter
    dazwischen, keine Drosselung, volle Historie.
  * PSD2 ueber Enable Banking fuer alles andere -- Neobanken, EU-Ausland,
    PayPal, deutsche Banken ohne FinTS.
Welcher Weg passt, entscheidet der 'assistent'. Wer 'add' direkt aufruft und
dabei an eine Bank ohne FinTS geraet, bekommt PSD2 angeboten statt einer
Sackgasse.

Nur HIER passiert TAN-Interaktion. Der taegliche Abruf (scripts/collect_banking.py)
laeuft headless.

DREI DINGE, DIE HIER BEWUSST SO SIND (Befund 2026-08-22, Sparkasse):
  * Leere Eingaben werden nicht angenommen und nicht gespeichert. Frueher
    landete ein leerer Anmeldename im Schluesselbund und der Fehler tauchte
    spaeter als "Keine Credentials im Keychain" auf.
  * Die Zugangsdaten wandern erst NACH einer erfolgreichen Verbindung in den
    Schluesselbund. Vorher gab es einen halb eingerichteten Zustand, der sich
    als "eingerichtet" ausgab.
  * Das TAN-Verfahren wird NICHT gesetzt, es gilt die Vorgabe der Bank. Warum,
    steht ausfuehrlich im Kopf von banking/tan.py. Wer doch eins erzwingen
    will, nimmt den Befehl 'verfahren'.
"""
import re
import sys
from pathlib import Path

# Bootstrap: scripts/ auf den Pfad, damit 'from banking import ...' funktioniert,
# egal ob direkt (python scripts/banking/setup.py) aufgerufen.
_SCRIPTS = Path(__file__).resolve().parent.parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

import getpass  # noqa: E402

from banking import (  # noqa: E402
    registry,
    keychain,
    config_store,
    session,
    tan,
)
from banking import client as bank_client  # noqa: E402

HINWEIS_FEHLER = (
    "Hinweis fuer Claude: Fehlercode + Bankname recherchieren (Server-URL, "
    "Segment-Version, ggf. eigene DK-Product-ID) und erneut versuchen. "
    "Ein TAN-Verfahren NICHT auf Verdacht setzen, siehe banking/tan.py."
)


def _frage_pflicht(text, geheim=False, versuche=3):
    """Eingabe, die nicht leer sein darf. Gibt None zurueck, wenn aufgegeben.

    Der Grund fuer diese Funktion ist ein echter Ausfall: beim Einfuegen einer
    IBAN kam ein Zeilenumbruch mit, die naechste Eingabeaufforderung verschluckte
    ihn als leere Zeile, und der leere Anmeldename wurde klaglos gespeichert."""
    for i in range(versuche):
        wert = (getpass.getpass(text) if geheim else input(text)).strip()
        if wert:
            return wert
        rest = versuche - i - 1
        print(
            "  Da kam nichts an. Das passiert, wenn beim Einfuegen ein "
            "Zeilenumbruch mitkommt."
            + (f" Noch {rest} Versuch(e)." if rest else "")
        )
    print("Abgebrochen, es wurde nichts gespeichert.")
    return None


def _oeffne_und_melde_tan(c):
    """Dialog laeuft bereits: Anmelde-TAN abarbeiten und TAN-Medium klaeren."""
    if tan.handle_login_tan(c):
        print("Anmelde-TAN bestaetigt.")
    _, hinweis = tan.select_medium(c)
    if hinweis and "kein TAN-Medium noetig" not in hinweis:
        print(f"  {hinweis}")


def _psd2_anbieten(grund, land=None, name=None):
    """Kein FinTS moeglich -- statt abzubrechen den zweiten Weg anbieten.

    Frueher endete cmd_add hier mit 'geht nicht'. Das war fuer den Kunden eine
    Sackgasse, obwohl das Modul den Fall inzwischen abdecken kann."""
    print(f"\n{grund}")
    print("Ueber PSD2 (Enable Banking) geht diese Bank aber. Der Unterschied:")
    print("  statt PIN und TAN gibst du den Zugriff einmal in deiner Bank-App frei.")
    if input("Jetzt ueber PSD2 anbinden? (ja/nein): ").strip().lower() not in ("ja", "j", "yes"):
        print("Abgebrochen, es wurde nichts gespeichert.")
        return None
    from banking import psd2_setup
    return psd2_setup.cmd_add(land, name)


def cmd_add(iban_vorgabe=None):
    print("=== Bank anbinden (FinTS) ===")
    iban = iban_vorgabe or _frage_pflicht("IBAN deines Kontos: ")
    if not iban:
        return
    try:
        info = registry.lookup_by_iban(iban)
    except ValueError as e:
        # Keine deutsche IBAN. FinTS ist ein deutscher Standard, also ist hier
        # nicht Schluss, sondern der andere Weg dran.
        land = re.sub(r"\s+", "", iban).upper()[:2]
        return _psd2_anbieten(str(e), land=land if land.isalpha() else None)

    blz = info["blz"]
    if not info["pintan_url"]:
        print(f"\nFuer BLZ {blz} ({info['bank_name'] or 'unbekannt'}) ist keine FinTS-URL hinterlegt.")
        print("Moegliche Gruende: Neobank ohne FinTS, oder Registry veraltet.")
        print(
            "Claude kann jetzt die aktuelle FinTS-PIN/TAN-URL dieser Bank recherchieren "
            "und hier eintragen."
        )
        manual = input("FinTS-Server-URL (leer = ueber PSD2 versuchen): ").strip()
        if not manual:
            return _psd2_anbieten(
                "Kein FinTS-Zugang fuer diese Bank.",
                land="DE", name=info.get("bank_name") or None)
        info["pintan_url"] = manual

    print(f"\nBank:   {info['bank_name'] or blz}")
    print(f"BLZ:    {blz}")
    print(f"Server: {info['pintan_url']}")
    login = _frage_pflicht("Online-Banking Login (Anmeldename / Legitimations-ID): ")
    if not login:
        return
    pin = _frage_pflicht("Online-Banking PIN: ", geheim=True)
    if not pin:
        return

    bank = {
        # key + weg seit 2026-08-31, seit es zwei Wege gibt. Fuer FinTS ist der
        # Schluessel weiterhin die BLZ, damit bestehende Konfigs unveraendert
        # weiterlaufen.
        "key": blz,
        "weg": config_store.WEG_FINTS,
        "blz": blz,
        "label": info["bank_name"] or blz,
        "pintan_url": info["pintan_url"],
        "bic": info.get("bic", ""),
        "product_id": bank_client.DEFAULT_PRODUCT_ID,
        # None = Vorgabe der Bank. Bewusst nicht vorbelegen, siehe banking/tan.py.
        "tan_mechanism": None,
        "tan_medium": None,
        "accounts": [],
        "fetch_days": 90,
        "session_file": config_store.session_path(blz),
    }

    print("\nVerbinde... (die Bank kann jetzt eine TAN verlangen)")
    # Zugangsdaten ausdruecklich mitgeben statt aus dem Schluesselbund lesen:
    # gespeichert wird erst, wenn die Verbindung wirklich stand.
    c = bank_client.build_client(bank, login=login, pin=pin)
    try:
        with c:
            _oeffne_und_melde_tan(c)

            accounts = c.get_sepa_accounts()
            if bank_client.needs_tan(accounts):
                accounts = tan.beantworte(c, accounts)
            konten = bank_client.konten_vereinen(c, accounts)
            ibans = [k["iban"] for k in konten]
            bank["accounts"] = ibans
            print(f"\nGefundene Konten: {len(konten)}")
            for k in konten:
                woher = "SEPA-Liste" if k["quelle"] == "sepa" else "nur in den Bankdaten (UPD)"
                kunde = f", Kundennr {k['customer_id']}" if k.get("customer_id") else ""
                print(f"  {k['iban']}  ({woher}{kunde})")
            if not konten:
                print("  (keine)")

            if konten:
                bal = c.get_balance(konten[0]["_obj"])
                if bank_client.needs_tan(bal):
                    bal = tan.beantworte(c, bal)
                print(f"Testsaldo {ibans[0]}: {bal.amount.amount} {bal.amount.currency}")

        if not bank["accounts"]:
            print(
                "\nDie Bank hat kein einziges Konto herausgegeben. Das ist KEIN Erfolg: "
                "es wird nichts gespeichert und der taegliche Abruf haette nichts zu holen."
            )
            print(
                "Meist liegt es daran, dass der genutzte Zugang keine Konto-Freigabe hat "
                "oder die falsche Legitimations-ID verwendet wurde."
            )
            return

        # Ab hier steht die Verbindung. Jetzt erst schreiben.
        keychain.set_credentials(blz, login, pin)
        session.save(bank["session_file"], c.deconstruct(including_private=True))
        config_store.upsert_bank(bank)
        print("\nVerbindung steht und gespeichert. Taegliche Abrufe laufen ab jetzt automatisch.")
    except Exception as e:
        print(f"\nVerbindung fehlgeschlagen: {type(e).__name__}: {e}")
        print("Es wurde nichts gespeichert, du kannst 'add' einfach erneut laufen lassen.")
        print(HINWEIS_FEHLER)


def cmd_reauth(blz):
    bank = config_store.get_bank(blz)
    if not bank:
        print(f"Keine Bank mit BLZ {blz} eingerichtet.")
        return
    print(f"=== Re-Auth {bank['label']} ({blz}) ===")
    # WICHTIG (Befund 2026-08-26, Kundenbericht Commerzbank): den gespeicherten Zustand
    # MITGEBEN. Frueher stand hier build_client(bank) ohne from_data, mit der
    # Begruendung "frischer Dialog wegen Issue #125". Das verwechselt zwei
    # Dinge. Issue #125 betrifft das FORTSETZEN eines pausierten Dialogs nach
    # send_tan; from_data laedt dagegen nur den gespeicherten Zustand und baut
    # trotzdem einen frischen Dialog. Ohne from_data ist die system_id
    # SYSTEM_ID_UNASSIGNED ('0'), python-fints schickt dann HKSYN3(NEW_SYSTEM_ID)
    # und die Bank vergibt bei JEDEM Re-Auth eine NEUE Kundensystem-Kennung.
    # Fuer die Bank ist das jedes Mal ein fremder Client, und ein fremder Client
    # bekommt keine SCA-Ausnahme: es kam bei jedem Abruf wieder eine TAN.
    c = bank_client.build_client(bank, from_data=session.load(bank["session_file"]))
    # Ein ausdruecklich gewuenschtes Verfahren wird VOR dem Dialog gesetzt,
    # nie darin. Ohne Wunsch passiert hier nichts, die Bank entscheidet.
    if bank.get("tan_mechanism"):
        _, hinweis = tan.apply_mechanism(c, bank["tan_mechanism"])
        print(f"  {hinweis}")
    try:
        with c:
            _oeffne_und_melde_tan(c)
            accounts = c.get_sepa_accounts()
            if bank_client.needs_tan(accounts):
                accounts = tan.beantworte(c, accounts)
            konten = bank_client.konten_vereinen(c, accounts)
            if konten:
                # Kontoliste auffrischen: schaltet die Bank ein Konto nach,
                # taucht es sonst nie auf, weil die Liste aus der Ersteinrichtung
                # stammt.
                bank["accounts"] = [k["iban"] for k in konten]
                config_store.upsert_bank(bank)
                print(f"Konten: {len(konten)} ({', '.join(bank['accounts'])})")
        session.save(bank["session_file"], c.deconstruct(including_private=True))
        print("Session erneuert. Headless-Abrufe laufen wieder.")
    except Exception as e:
        print(f"Re-Auth fehlgeschlagen: {type(e).__name__}: {e}")
        print(HINWEIS_FEHLER)


def cmd_verfahren(blz, mech_id=None, zuruecksetzen=False):
    """TAN-Verfahren anzeigen oder ausdruecklich erzwingen.

    Ohne ID: zeigt, was die Bank anbietet (nach der Anmeldung, denn davor
    nennen viele Banken gar nichts). Mit ID: schreibt den Wunsch in die Config,
    ab dann wird er vor jedem Dialog gesetzt."""
    bank = config_store.get_bank(blz)
    if not bank:
        print(f"Keine Bank mit BLZ {blz} eingerichtet.")
        return
    if zuruecksetzen:
        bank["tan_mechanism"] = None
        config_store.upsert_bank(bank)
        print("Zurueckgesetzt: es gilt wieder die Vorgabe der Bank.")
        return
    if mech_id:
        bank["tan_mechanism"] = mech_id
        config_store.upsert_bank(bank)
        print(f"Verfahren {mech_id} als Wunsch hinterlegt. Wirkt ab dem naechsten Dialog.")
        print(f"Zuruecksetzen auf die Vorgabe der Bank: setup.py verfahren {blz} standard")
        return

    # Auch hier den gespeicherten Zustand mitgeben: dieser Befehl oeffnet einen
    # echten Dialog, und ohne from_data fordert python-fints eine NEUE
    # Kundensystem-Kennung an. Ein blosses Nachschauen wuerde dann die
    # TAN-Freiheit der bestehenden Sitzung verbrennen (siehe cmd_reauth).
    c = bank_client.build_client(bank, from_data=session.load(bank["session_file"]))
    print("Vor der Anmeldung nennt die Bank:", tan.list_mechanisms(c) or "(nichts)")
    try:
        with c:
            _oeffne_und_melde_tan(c)
            print("Nach der Anmeldung nennt die Bank:", tan.list_mechanisms(c) or "(nichts)")
    except Exception as e:
        print(f"Konnte nicht anmelden: {type(e).__name__}: {e}")
    aktuell = bank.get("tan_mechanism") or "(Vorgabe der Bank)"
    print(f"Eingestellt: {aktuell}")


def cmd_list():
    banks = config_store.load().get("banks", [])
    if not banks:
        print("Keine Bank eingerichtet. 'python scripts/banking/setup.py assistent' ausfuehren.")
        return
    for b in banks:
        weg = config_store.bank_weg(b)
        schluessel = config_store.bank_key(b)
        if weg == config_store.WEG_PSD2:
            # Beim PSD2-Weg gibt es weder Schluesselbund noch Session-Datei.
            # Was dort zaehlt, ist die Restlaufzeit der Freigabe.
            from banking import psd2
            s = psd2.session(schluessel) or {}
            rest = psd2.rest_tage(s.get("gueltig_bis"))
            zustand = psd2.zustand(rest) if s else "keine Freigabe"
            rest_txt = f"noch {rest} Tage" if rest is not None else "unbekannt"
            print(
                f"- {b.get('label') or schluessel} [PSD2, {b.get('land', '?')}] "
                f"| Konten: {len(s.get('konten') or [])} "
                f"| Freigabe: {rest_txt} [{zustand}]"
            )
            continue
        creds = "ok" if keychain.has_credentials(b["blz"]) else "FEHLT"
        sess = "vorhanden" if session.load(b.get("session_file")) else "fehlt"
        mech = b.get("tan_mechanism") or "Vorgabe der Bank"
        print(
            f"- {b['label']} [FinTS, BLZ {b['blz']}] | Konten: {len(b.get('accounts', []))} "
            f"| Credentials: {creds} | Session: {sess} | TAN: {mech}"
        )


def cmd_remove(key):
    bank = config_store.get_bank(key)
    if bank and config_store.bank_weg(bank) == config_store.WEG_PSD2:
        from banking import psd2_setup
        psd2_setup.cmd_remove(key)
        return
    config_store.remove_bank(key)
    keychain.delete(key)
    print(f"{key} entfernt (Config + Keychain).")


def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        return
    cmd = args[0]
    if cmd == "assistent":
        from banking import assistent
        assistent.main()
    elif cmd == "psd2-add":
        from banking import psd2_setup
        psd2_setup.cmd_add(args[1] if len(args) > 1 else None,
                           args[2] if len(args) > 2 else None)
    elif cmd == "psd2-reauth" and len(args) > 1:
        from banking import psd2_setup
        psd2_setup.cmd_reauth(args[1])
    elif cmd == "psd2-banken" and len(args) > 1:
        from banking import psd2_setup
        psd2_setup.cmd_banken(args[1], args[2] if len(args) > 2 else None)
    elif cmd == "add":
        cmd_add()
    elif cmd == "reauth" and len(args) > 1:
        cmd_reauth(args[1])
    elif cmd == "verfahren" and len(args) > 1:
        wunsch = args[2] if len(args) > 2 else None
        cmd_verfahren(args[1], None if wunsch == "standard" else wunsch,
                      zuruecksetzen=(wunsch == "standard"))
    elif cmd == "list":
        cmd_list()
    elif cmd == "remove" and len(args) > 1:
        cmd_remove(args[1])
    else:
        print(__doc__)


if __name__ == "__main__":
    main()
