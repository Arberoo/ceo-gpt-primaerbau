"""
Banking - TAN-Handling fuer FinTS.

Nur INTERAKTIV beim Setup / Re-Auth verwenden. Der taegliche Abruf laeuft
headless und ruft NICHTS aus diesem Modul, sondern bricht bei TAN-Bedarf
sauber ab.

VIER REGELN, DIE HIER IN CODE STEHEN:

1. DAS TAN-VERFAHREN WIRD NICHT MEHR VON UNS GESETZT.
   (Befund 2026-08-22, Sparkasse.) FinTS verbietet set_tan_mechanism()
   waehrend eines stehenden Dialogs ("Cannot change TAN mechanism with a
   standing dialog"). Der naheliegende Fix, die Auswahl vor den Dialog zu
   ziehen, ist aber genauso falsch: Sparkassen nennen ihre Verfahren ERST
   NACH der Anmeldung, davor kommt eine leere Liste zurueck, es wird keins
   gesetzt, und die Bank weist die Signatur mit Fehler 9340 ab. Richtig ist:
   gar nicht setzen, die Vorgabe der Bank nehmen. Gesetzt wird nur noch, wenn
   jemand in der Config ausdruecklich ein anderes Verfahren verlangt, und dann
   VOR dem Dialog (siehe apply_mechanism).

2. DIE ANMELDE-TAN WIRD ABGEFRAGT.
   Viele Banken verlangen schon fuers ANMELDEN eine TAN, nicht erst fuer den
   Kontoabruf. python-fints legt sie als client.init_tan_response ab, direkt
   nachdem der Dialog aufgeht. Wer nur die Rueckgabe von get_sepa_accounts()
   auf TAN-Bedarf prueft, sieht sie nie und der Dialog bricht ab.
   handle_login_tan() muss deshalb als ERSTES im 'with'-Block laufen.

3. DIE CHALLENGE HAT DREI ERSCHEINUNGSFORMEN, NICHT EINE.
   (Befund 2026-08-26, Kundenbericht Commerzbank/photoTAN.) NeedTANResponse traegt
   challenge (Text), challenge_hhduc (chipTAN-Flicker) UND challenge_matrix
   (das Bild fuer photoTAN/QR, als tuple(mime_type, bytes)). Wer nur die
   ersten beiden auswertet, zeigt einer photoTAN-Bank ihren Begleitsatz
   "Dies ist Ihre photoTAN Challenge." an und sonst nichts: der Anwender hat
   nichts zu scannen, kann keine TAN erzeugen, und der Dialog laeuft in einen
   Signaturfehler 9340. Genau das war drei Monate lang der Zustand.

4. BEI 'DECOUPLED' GIBT ES KEINE TAN ZUM EINTIPPEN.
   Manche Banken lassen nur in der App freigeben. python-fints markiert das
   als challenge.decoupled; der tan-Parameter von send_tan wird dann ignoriert.
   Wichtig: solange der Mensch noch nicht freigegeben hat, antwortet die Bank
   mit 3956 und send_tan gibt WIEDER ein NeedTANResponse zurueck. Wer nur
   einmal sendet, haelt ein "noch nicht bestaetigt" faelschlich fuer erledigt
   und arbeitet auf einem toten Dialog weiter. Es muss gepollt werden.
"""
from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

from banking import rechte  # Windows-Anpassung: Rechte nur fuer den Besitzer

# Wie oft/lange bei entkoppelter Freigabe nachgefragt wird (Regel 4).
DECOUPLED_INTERVALL_SEK = 5
DECOUPLED_VERSUCHE = 24  # rund 2 Minuten


def list_mechanisms(client):
    """Verfuegbare TAN-Verfahren als Dict, nie None.

    Vor der Anmeldung ist das bei vielen Banken (u.a. Sparkassen) leer. Das ist
    kein Fehler, sondern der Normalfall, und genau der Grund, warum wir kein
    Verfahren mehr vorab auswaehlen."""
    try:
        return dict(client.get_tan_mechanisms() or {})
    except Exception:
        return {}


def apply_mechanism(client, preferred):
    """Ein AUSDRUECKLICH gewuenschtes Verfahren setzen. Vor dem Dialog aufrufen.

    Gibt (mech_id, hinweis) zurueck. mech_id ist None, wenn nichts gesetzt
    wurde; `hinweis` sagt dann warum, im Klartext. Es wird bewusst NICHT
    stillschweigend auf irgendein Verfahren ausgewichen: ein falsch geratenes
    Verfahren scheitert spaeter mit einem Bankcode, der nirgends hinzeigt."""
    if not preferred:
        return None, "kein Verfahren erzwungen, es gilt die Vorgabe der Bank"

    mechanisms = list_mechanisms(client)
    if not mechanisms:
        return None, (
            f"Verfahren '{preferred}' konnte nicht gesetzt werden: die Bank nennt "
            "vor der Anmeldung keine Verfahren. Es gilt die Vorgabe der Bank."
        )
    if preferred not in mechanisms:
        return None, (
            f"Verfahren '{preferred}' kennt die Bank nicht. Bekannt: "
            f"{', '.join(sorted(mechanisms))}. Es gilt die Vorgabe der Bank."
        )
    try:
        client.set_tan_mechanism(preferred)
    except Exception as e:
        return None, (
            f"Verfahren '{preferred}' liess sich nicht setzen ({type(e).__name__}: {e}). "
            "Es gilt die Vorgabe der Bank."
        )
    return preferred, f"Verfahren {preferred} gesetzt"


def select_medium(client):
    """TAN-Medium waehlen, falls die Bank eines verlangt. Im Dialog erlaubt.

    Gibt (medium_name, hinweis) zurueck. Viele Banken brauchen das nicht, dann
    passiert nichts."""
    try:
        from fints.formals import DescriptionRequired

        mech = client.get_current_tan_mechanism()
        if getattr(mech, "description_required", None) != DescriptionRequired.MUST:
            return None, "kein TAN-Medium noetig"
        media = client.get_tan_media()
        media_list = media[1] if isinstance(media, tuple) and len(media) > 1 else media
        if not media_list:
            return None, "Bank verlangt ein TAN-Medium, nennt aber keins"
        medium = media_list[0]
        client.set_tan_medium(medium)
        name = getattr(medium, "tan_medium_name", None) or str(medium)
        return name, f"TAN-Medium {name} gesetzt"
    except Exception as e:
        # Defensiv: eine fehlende Medium-Auswahl darf das Setup nie kippen.
        return None, f"TAN-Medium uebersprungen ({type(e).__name__})"


def login_tan_pending(client):
    """True, wenn die Bank fuers Anmelden eine TAN will. Auch fuer den headless-Weg."""
    return bool(getattr(client, "init_tan_response", None))


def is_decoupled(challenge):
    """True, wenn nur in der App freigegeben wird und es nichts einzutippen gibt."""
    return bool(getattr(challenge, "decoupled", False))


def _bild_verzeichnis():
    """Wo die TAN-Grafik landet: neben der Config im Modul-Datenordner (0700).

    BEWUSST NICHT /tmp: dort liegt sie unter einem vorhersagbaren Namen fuer
    jeden Benutzer der Maschine lesbar. Faellt der Import aus (Modul einzeln
    benutzt), lieber /tmp als gar kein Bild."""
    try:
        from banking.config_store import BANKING_DIR

        BANKING_DIR.mkdir(parents=True, exist_ok=True)
        try:
            rechte.schuetze(BANKING_DIR, 0o700)  # Windows-Anpassung, siehe rechte.py
        except Exception:
            pass
        return BANKING_DIR
    except Exception:
        import tempfile

        return Path(tempfile.gettempdir())


def _oeffne(pfad):
    """Bild im Standard-Betrachter oeffnen. Gibt True zurueck, wenn es lief.

    Fehlschlag ist kein Drama: der Pfad wird ohnehin ausgegeben, der Anwender
    kann die Datei selbst oeffnen. Ein harter Fehler hier waere schlimmer als
    ein nicht aufgehendes Fenster, er wuerde die TAN-Eingabe verhindern."""
    if sys.platform == "darwin":
        befehl = ["open", str(pfad)]
    elif sys.platform.startswith("win"):
        befehl = ["cmd", "/c", "start", "", str(pfad)]
    else:
        befehl = ["xdg-open", str(pfad)]
    try:
        subprocess.run(
            befehl,
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=10,
        )
        return True
    except Exception:
        return False


def zeige_matrix(challenge, oeffnen=True):
    """Die Grafik-Challenge (photoTAN / QR) herausschreiben und anzeigen.

    Gibt den Pfad zurueck oder None, wenn die Bank keine Grafik geschickt hat.
    Die Datei traegt 0600 und wird nach der Eingabe wieder geloescht
    (siehe prompt_tan)."""
    matrix = getattr(challenge, "challenge_matrix", None)
    if not matrix:
        return None
    try:
        mime, daten = matrix
    except (TypeError, ValueError):
        return None
    if not daten:
        return None

    endung = ".png" if "png" in str(mime).lower() else ".bin"
    ziel = _bild_verzeichnis() / f"tan-grafik{endung}"
    try:
        ziel.write_bytes(daten)
        try:
            rechte.schuetze(ziel, 0o600)  # Windows-Anpassung, siehe rechte.py
        except Exception:
            pass
    except Exception as e:
        print(f"  Grafik liess sich nicht speichern ({type(e).__name__}: {e}).")
        return None

    print(f"\nTAN-Grafik: {ziel}")
    if oeffnen and not _oeffne(ziel):
        print("  (Konnte nicht automatisch geoeffnet werden, bitte selbst oeffnen.)")
    return ziel


def _aufraeumen(pfad):
    """Die TAN-Grafik nach Gebrauch entfernen. Sie ist eine Sekunde spaeter wertlos."""
    if not pfad:
        return
    try:
        Path(pfad).unlink()
    except Exception:
        pass


def handle_login_tan(client, ask=None):
    """Die TAN abarbeiten, die die Bank schon FUERS ANMELDEN verlangt.

    Als erstes im 'with'-Block aufrufen. Gibt True zurueck, wenn eine TAN
    noetig war und beantwortet wurde, sonst False.

    `ask` ist der TAN-Frager (Default: prompt_tan). Headless wird das hier
    NICHT aufgerufen, dort sagt login_tan_pending() Bescheid."""
    resp = getattr(client, "init_tan_response", None)
    if not resp:
        return False
    beantworte(client, resp, ask)
    return True


def beantworte(client, challenge, ask=None):
    """Eine Challenge beantworten. DER EINE WEG, ueber den jede TAN laeuft.

    Nie direkt client.send_tan() aufrufen: bei entkoppelter Freigabe muss so
    lange nachgefragt werden, bis der Mensch in der App bestaetigt hat.

    Regel 4: bei decoupled gibt send_tan wieder ein NeedTANResponse zurueck,
    solange nicht freigegeben ist (Bankcode 3956). Nur einmal zu senden sieht
    aus wie Erfolg und ist keiner."""
    ask = ask or prompt_tan
    antwort = client.send_tan(challenge, ask(challenge))
    if not is_decoupled(challenge):
        return antwort

    from fints.client import NeedTANResponse

    for versuch in range(DECOUPLED_VERSUCHE):
        if not isinstance(antwort, NeedTANResponse):
            return antwort
        if versuch == 0:
            print("  Warte auf die Freigabe in deiner Banking-App...")
        time.sleep(DECOUPLED_INTERVALL_SEK)
        antwort = client.send_tan(antwort, "")

    raise TimeoutError(
        "Die Freigabe in der Banking-App kam nicht rechtzeitig an "
        f"(nach {DECOUPLED_VERSUCHE * DECOUPLED_INTERVALL_SEK} Sekunden). "
        "Einfach erneut versuchen."
    )


def _eingabe_text(challenge, hat_grafik):
    """Die Aufforderung passend zum Verfahren.

    Frueher stand hier pauschal 'bei pushTAN: in der App bestaetigen'. Bei
    photoTAN gibt es nichts zu bestaetigen, es muss gescannt und eingetippt
    werden, und der Anwender wurde damit in die falsche Richtung geschickt."""
    if is_decoupled(challenge):
        return "In der Banking-App freigeben, dann Enter (keine TAN eintippen): "
    if hat_grafik:
        return "Grafik mit der Banking-App scannen, dann die angezeigte TAN eintippen: "
    if getattr(challenge, "challenge_hhduc", None):
        return "TAN vom TAN-Generator eintippen: "
    return "TAN eingeben (bei pushTAN: in der Banking-App bestaetigen, dann Enter): "


def prompt_tan(challenge):
    """Interaktiver TAN-Callback. Zeigt die Challenge und liest die TAN.

    Deckt alle vier Erscheinungsformen ab: Text, Flickercode (chipTAN),
    Grafik (photoTAN/QR) und entkoppelte Freigabe."""
    print("\n--- TAN-Anfrage der Bank ---")
    desc = getattr(challenge, "challenge", None)
    if desc:
        print(desc)

    hhduc = getattr(challenge, "challenge_hhduc", None)
    if hhduc:
        try:
            from fints.hhd.flicker import terminal_flicker_unix

            terminal_flicker_unix(hhduc)
        except Exception:
            pass

    bild = zeige_matrix(challenge)

    if is_decoupled(challenge):
        # Der Rueckgabewert wird von send_tan ignoriert. Das Enter dient nur
        # dazu, dem Menschen Zeit zum Freigeben zu lassen.
        input(_eingabe_text(challenge, bool(bild)))
        _aufraeumen(bild)
        return ""

    try:
        return input(_eingabe_text(challenge, bool(bild))).strip()
    finally:
        _aufraeumen(bild)
