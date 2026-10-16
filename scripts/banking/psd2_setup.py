"""
Banking - PSD2-Verbindung einrichten (interaktiv).

Der EINZIGE Ort, an dem eine PSD2-Freigabe entsteht. Der taegliche Abruf
(collect_banking.py) laeuft danach ohne jede Eingabe.

DER RUECKWEG IST DIE EINE STELLE, DIE HAKEN KANN. Nach der Freigabe in der
Bank-App schickt Enable Banking den Browser auf die Redirect-Adresse, die im
Control Panel hinterlegt ist. Dieses Modul hat keinen Webserver. Deshalb gibt
es ZWEI Wege, und der Kunde entscheidet beim Anlegen seiner Application,
welchen er will:

  A) LAUSCHER (empfohlen, robust): im Control Panel
     http://localhost:8899/callback als Redirect-Adresse eintragen. Beim
     Einrichten macht dieses Skript kurz einen Ein-Zweck-Lauscher auf, faengt
     den Code selbst und beendet sich sofort wieder. Nichts zum Kopieren.

  B) EINFUEGEN (immer moeglich): irgendeine Adresse eintragen. Der Browser
     landet dort auf einer Seite, die womoeglich gar nicht laedt -- das ist
     normal. In der Adresszeile steht trotzdem ?code=..., und genau die Zeile
     wird hier eingefuegt.

Weg B ist der Rueckfall, wenn ein Anbieter keine localhost-Adresse annimmt.
Beide enden im selben create_session().
"""
from __future__ import annotations

import re
import sys
import urllib.parse

from banking import config_store, psd2

LAUSCHER_PORT = 8899
LAUSCHER_PFAD = "/callback"
LAUSCHER_TIMEOUT = 300


def _frage(text):
    try:
        return input(text).strip()
    except (EOFError, KeyboardInterrupt):
        print()
        return ""


def _name_aus(institut, land):
    """Ein kurzer, stabiler Verbindungsname aus dem Institutsnamen."""
    roh = re.sub(r"[^a-z0-9]+", "-", (institut or "bank").lower()).strip("-")
    return f"{roh or 'bank'}-{(land or '').lower()}"


def zugang_pruefen():
    """Liegt der Enable-Banking-Zugang? Sonst hat das Einrichten keinen Zweck."""
    if psd2.zugang_da():
        return True
    print("\nEs fehlt noch der einmalige Enable-Banking-Zugang.")
    print(f"Erwartet werden zwei Dateien in {psd2.data_dir()}:")
    print(f"  {psd2.SCHLUESSEL_DATEI}   (der Schluessel deiner Application)")
    print(f"  {psd2.APP_DATEI}          (die Application ID)")
    print("\nWie du beides bekommst, steht Schritt fuer Schritt in")
    print("reference/enable-banking.md. Das dauert einmalig etwa 10 Minuten")
    print("und kostet nichts.")
    return False


def bank_waehlen(land, suchtext=None):
    """Bank aus der Enable-Banking-Liste aussuchen."""
    try:
        treffer = psd2.suche_banken(land, suchtext)
    except psd2.PSD2Error as e:
        print(f"\nFEHLER: {e}")
        return None
    if not treffer:
        print(f"\nKeine Bank in {land} gefunden"
              + (f", die '{suchtext}' enthaelt." if suchtext else "."))
        print("Anderer Suchbegriff oder anderes Land? Der Name muss so "
              "geschrieben sein wie bei der Bank selbst.")
        return None
    if len(treffer) == 1:
        b = treffer[0]
        print(f"\nGefunden: {b['name']} ({b['land']})")
        return b
    print(f"\n{len(treffer)} Treffer:")
    for i, b in enumerate(treffer[:40], 1):
        hinweis = " [Passwort in fremdem Formular]" if b["passwort_noetig"] else ""
        print(f"  {i:2}. {b['name']}{hinweis}")
    if len(treffer) > 40:
        print(f"  ... und {len(treffer) - 40} weitere. Bitte genauer suchen.")
    wahl = _frage("\nNummer (leer = abbrechen): ")
    if not wahl.isdigit() or not (1 <= int(wahl) <= min(40, len(treffer))):
        return None
    return treffer[int(wahl) - 1]


def _lauscher(port=LAUSCHER_PORT, timeout=LAUSCHER_TIMEOUT):
    """Ein-Zweck-Lauscher: nimmt genau EINE Anfrage entgegen, liest den Code
    heraus, antwortet dem Browser und beendet sich. Kein Dienst, kein Port,
    der offen bleibt."""
    from http.server import BaseHTTPRequestHandler, HTTPServer

    gefangen = {}

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            gefangen["code"] = (q.get("code") or [""])[0]
            gefangen["fehler"] = (q.get("error") or [""])[0]
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            text = ("Freigabe angekommen. Du kannst dieses Fenster schliessen."
                    if gefangen["code"] else
                    "Es kam kein Code an. Zurueck ins Terminal.")
            self.wfile.write(f"<html><body><h3>{text}</h3></body></html>".encode())

        def log_message(self, *a):
            pass  # nicht ins Terminal quatschen, dort laeuft die Fuehrung

    try:
        srv = HTTPServer(("127.0.0.1", port), Handler)
    except OSError as e:
        print(f"  Lauscher auf Port {port} ging nicht auf ({e}).")
        return None
    srv.timeout = timeout
    srv.handle_request()
    srv.server_close()
    if gefangen.get("fehler"):
        print(f"  Die Bank meldete: {gefangen['fehler']}")
    return gefangen.get("code") or None


def freigabe_holen(institut, land, psu_type, name):
    """Freigabe-Adresse erzeugen, Code einsammeln, Sitzung anlegen."""
    try:
        url, _ = psd2.start_auth(institut, land, psu_type, state=name)
        redirect = psd2.redirect_url()
    except psd2.PSD2Error as e:
        print(f"\nFEHLER: {e}")
        return None

    print("\n--- Freigabe in der Bank ---")
    print("Oeffne diese Adresse und gib den Zugriff frei:\n")
    print(f"  {url}\n")
    print("Die Freigabe gilt hoechstens 180 Tage, danach fragt die Bank erneut.")

    lauscher_moeglich = f"localhost:{LAUSCHER_PORT}" in (redirect or "") or \
                        f"127.0.0.1:{LAUSCHER_PORT}" in (redirect or "")

    code = None
    if lauscher_moeglich:
        print(f"\nIch warte hier auf die Rueckmeldung (bis zu "
              f"{LAUSCHER_TIMEOUT // 60} Minuten). Du musst nichts kopieren.")
        code = _lauscher()

    if not code:
        if lauscher_moeglich:
            print("\nEs kam nichts an. Dann bitte von Hand:")
        print("\nNach der Freigabe landet der Browser auf")
        print(f"  {redirect}")
        print("Diese Seite laedt womoeglich gar nicht -- das ist normal und kein")
        print("Fehler. Entscheidend ist die ADRESSZEILE: dort steht ?code=...")
        eingabe = _frage("\nGanze Adresse (oder nur den Code) hier einfuegen: ")
        code = psd2.code_aus(eingabe)

    if not code:
        print("Kein Code bekommen. Es wurde nichts gespeichert.")
        return None

    try:
        s = psd2.create_session(code, name)
    except psd2.PSD2Error as e:
        print(f"\nFEHLER: {e}")
        return None
    return s


def konten_melden(s):
    """Was die Bank herausgegeben hat -- und der haeufigste Stolperstein."""
    konten = s.get("konten") or []
    if not konten:
        print("\nDie Freigabe steht, aber die Bank hat KEIN Konto herausgegeben.")
        print("Das ist fast immer derselbe Grund und kein Fehler im Code:")
        print("  Im Enable-Banking-Control-Panel muss das Konto zusaetzlich")
        print("  ueber 'Link accounts' verknuepft werden. Der kostenlose Modus")
        print("  gibt ausschliesslich verknuepfte Konten heraus.")
        print("Danach hier nochmal 'psd2-reauth' laufen lassen.")
        return False
    print(f"\n{len(konten)} Konto/Konten freigegeben:")
    for k in konten:
        print(f"  {k.get('name') or '-'}  {k.get('currency') or ''}  "
              f"{k.get('iban') or '(ohne IBAN)'}")
    return True


def cmd_add(land=None, suchtext=None):
    """Neue PSD2-Verbindung anlegen."""
    print("=== Bank ueber PSD2 anbinden (Enable Banking) ===")
    if not zugang_pruefen():
        return None

    land = (land or _frage("Land der Bank (z.B. DE, CY, LU, AT): ")).strip().upper()
    if not land:
        print("Ohne Land geht es nicht.")
        return None
    if suchtext is None:
        suchtext = _frage("Name der Bank (Teil reicht, z.B. 'revolut'): ")

    bank = bank_waehlen(land, suchtext or None)
    if not bank:
        return None

    if bank["passwort_noetig"]:
        print("\nACHTUNG: diese Bank verlangt Benutzername und Passwort in einem")
        print("FREMDEN Formular, nicht auf ihrer eigenen Seite. Bei einer")
        print("Weiterleitung gibt man seine Zugangsdaten nur der eigenen Bank.")
        if _frage("Trotzdem fortfahren? (ja/nein): ").lower() not in ("ja", "j", "yes"):
            print("Abgebrochen, es wurde nichts gespeichert.")
            return None

    psu_type = "personal"
    name = _name_aus(bank["name"], bank["land"])
    if config_store.get_bank(name):
        print(f"\n'{name}' ist schon eingerichtet. Zum Erneuern: "
              f"setup.py psd2-reauth {name}")
        return None

    s = freigabe_holen(bank["name"], bank["land"], psu_type, name)
    if not s:
        return None
    konten_melden(s)

    # Erst JETZT speichern. Dasselbe Prinzip wie beim FinTS-Weg: es soll keinen
    # halb eingerichteten Zustand geben, der sich als eingerichtet ausgibt.
    eintrag = {
        "key": name,
        "weg": config_store.WEG_PSD2,
        "label": bank["name"],
        "institut": bank["name"],
        "land": bank["land"],
        "psu_type": psu_type,
        "bic": bank.get("bic", ""),
        "fetch_days": 90,
    }
    config_store.upsert_bank(eintrag)
    print(f"\nEingerichtet als '{name}'. Der Tageslauf holt ab jetzt Salden "
          f"und Umsaetze.")
    return eintrag


def cmd_reauth(name):
    """Freigabe erneuern (nach 180 Tagen oder nach 'Link accounts')."""
    bank = config_store.get_bank(name)
    if not bank or config_store.bank_weg(bank) != config_store.WEG_PSD2:
        print(f"'{name}' ist keine PSD2-Verbindung. Vorhandene zeigen: setup.py list")
        return None
    if not zugang_pruefen():
        return None
    print(f"=== Freigabe erneuern: {bank.get('label') or name} ===")
    s = freigabe_holen(bank.get("institut") or bank.get("label"), bank.get("land"),
                       bank.get("psu_type", "personal"), name)
    if not s:
        return None
    konten_melden(s)
    print("\nFreigabe erneuert.")
    return s


def cmd_banken(land, suchtext=None):
    """Nachschlagen, wie eine Bank bei Enable Banking genau heisst."""
    if not zugang_pruefen():
        return
    try:
        treffer = psd2.suche_banken(land.upper(), suchtext)
    except psd2.PSD2Error as e:
        print(f"FEHLER: {e}")
        return
    if not treffer:
        print(f"Nichts gefunden in {land.upper()}"
              + (f" fuer '{suchtext}'." if suchtext else "."))
        return
    for b in treffer:
        art = "Passwort im fremden Formular" if b["passwort_noetig"] else "Weiterleitung"
        print(f"{b['name']:45} {b['bic']:12} {art}")


def cmd_remove(name):
    bank = config_store.get_bank(name)
    if not bank:
        print(f"'{name}' ist nicht eingerichtet.")
        return
    config_store.remove_bank(name)
    psd2.entferne_session(name)
    print(f"'{name}' entfernt (Config + Freigabe).")


if __name__ == "__main__":
    args = sys.argv[1:]
    if not args:
        print(__doc__)
    elif args[0] == "add":
        cmd_add(*args[1:3])
    elif args[0] == "reauth" and len(args) > 1:
        cmd_reauth(args[1])
    elif args[0] == "banken" and len(args) > 1:
        cmd_banken(args[1], args[2] if len(args) > 2 else None)
    elif args[0] == "remove" and len(args) > 1:
        cmd_remove(args[1])
    else:
        print(__doc__)
