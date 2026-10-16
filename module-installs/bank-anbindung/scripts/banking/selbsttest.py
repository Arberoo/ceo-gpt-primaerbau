#!/usr/bin/env python3
"""
Banking - Selbsttest. Ohne Bank, ohne Netz, ohne Schluesselbund.

    python scripts/banking/selbsttest.py

WARUM ES DEN GIBT: die vier Fehler, die dieses Modul monatelang bei jeder
Sparkasse unbrauchbar gemacht haben, waren alle ohne echte Bank nachstellbar.
Keiner davon haette einen Live-Test gebraucht, es gab nur nichts, was sie
haette bemerken koennen. Der Test bildet sie als Attrappe nach und nagelt sie
fest. Faellt er, ist eine der vier Regressionen zurueck.

Deckt NICHT ab: ob eine echte Bank die Anmeldung annimmt. Das bleibt ein
einmaliger Lauf von 'setup.py add' mit echten Zugangsdaten.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent.parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from banking import client as bank_client  # noqa: E402
from banking import keychain, registry, tan  # noqa: E402

OK, FEHLER = [], []


def pruefe(name, bedingung, detail=""):
    (OK if bedingung else FEHLER).append(name if not detail else f"{name} ({detail})")


class DialogVerbotenError(RuntimeError):
    """Was python-fints wirft: 'Cannot change TAN mechanism with a standing dialog'."""


class AttrappenClient:
    """Bank-Attrappe. Verhaelt sich in genau den Punkten wie eine Sparkasse,
    an denen das Modul frueher gescheitert ist:
      - vor der Anmeldung nennt sie KEINE TAN-Verfahren
      - set_tan_mechanism im laufenden Dialog ist verboten
      - fuers Anmelden verlangt sie eine TAN (init_tan_response)"""

    def __init__(self, verfahren_vorher=None, login_tan=True):
        self._vorher = verfahren_vorher or {}
        self._nachher = {"921": "pushTAN", "911": "chipTAN"}
        self.im_dialog = False
        self.init_tan_response = None
        self._login_tan = login_tan
        self.gesetzte_verfahren = []
        self.gesendete_tans = []

    def __enter__(self):
        self.im_dialog = True
        if self._login_tan:
            self.init_tan_response = "ANMELDE-TAN"
        return self

    def __exit__(self, *a):
        self.im_dialog = False
        return False

    def get_tan_mechanisms(self):
        return dict(self._nachher if self.im_dialog else self._vorher)

    def set_tan_mechanism(self, mech_id):
        if self.im_dialog:
            raise DialogVerbotenError("Cannot change TAN mechanism with a standing dialog")
        self.gesetzte_verfahren.append(mech_id)

    def send_tan(self, resp, tan_wert):
        self.gesendete_tans.append((resp, tan_wert))
        if resp == self.init_tan_response:
            self.init_tan_response = None
        return "OK"


# ---- 1. Leere Eingaben ----------------------------------------------
class AttrappenKeyring:
    """Schluesselbund-Attrappe. PFLICHT, nicht Bequemlichkeit: ohne sie wuerde
    ein kaputter Test auf einem Mac in den ECHTEN Schluesselbund schreiben, und
    unter Linux scheitert er stattdessen an einem fehlenden Backend, was den
    eigentlichen Befund verdeckt."""

    def __init__(self):
        self.tresor = {}

    def set_password(self, service, key, wert):
        self.tresor[(service, key)] = wert

    def get_password(self, service, key):
        return self.tresor.get((service, key))

    def delete_password(self, service, key):
        self.tresor.pop((service, key), None)


def _mit_attrappen_keyring(fn):
    attrappe = AttrappenKeyring()
    echt = keychain._kr
    keychain._kr = lambda: attrappe
    try:
        return fn(attrappe)
    finally:
        keychain._kr = echt


def test_leere_eingaben():
    def lauf(attrappe):
        for wert, label in ((" ", "Leerzeichen"), ("", "leer"), ("\n", "Zeilenumbruch")):
            try:
                keychain.set_credentials("12345678", wert, "geheim")
                pruefe(f"leerer Anmeldename ({label}) wird abgelehnt", False,
                       "wurde gespeichert")
            except ValueError:
                pruefe(f"leerer Anmeldename ({label}) wird abgelehnt", True)
            except Exception as e:
                pruefe(f"leerer Anmeldename ({label}) wird abgelehnt", False, type(e).__name__)
        try:
            keychain.set_credentials("12345678", "meinlogin", "")
            pruefe("leere PIN wird abgelehnt", False, "wurde gespeichert")
        except ValueError:
            pruefe("leere PIN wird abgelehnt", True)
        pruefe("nichts Leeres ist im Schluesselbund gelandet", attrappe.tresor == {},
               str(attrappe.tresor))

    _mit_attrappen_keyring(lauf)


def test_leerer_altbestand_gilt_als_fehlend():
    """Setups, in denen frueher schon ein leerer Wert gespeichert wurde, duerfen
    nicht 'Credentials: ok' melden."""
    def lauf(attrappe):
        attrappe.set_password(keychain.SERVICE, "12345678:login", "   ")
        attrappe.set_password(keychain.SERVICE, "12345678:pin", "geheim")
        pruefe("leerer Altbestand zaehlt als fehlend", keychain.get_login("12345678") is None)
        pruefe("has_credentials meldet dann nicht 'ok'",
               keychain.has_credentials("12345678") is False)

    _mit_attrappen_keyring(lauf)


def test_fehlermeldung_zeigt_auf_die_ursache():
    bank = {"blz": "12345678", "pintan_url": "https://example.invalid"}
    try:
        bank_client.build_client(bank, login="", pin="geheim")
        pruefe("leerer Login bricht build_client ab", False, "kam durch")
    except RuntimeError as e:
        text = str(e)
        pruefe("leerer Login bricht build_client ab", True)
        pruefe("Meldung nennt das fehlende Feld", "Anmeldename" in text, text[:60])
        # Die alte Meldung war "Keine Credentials im Keychain ... erst setup.py add
        # ausfuehren" - also genau der Befehl, den man gerade laufen hatte.
        pruefe("Meldung behauptet nicht 'keine Credentials'",
               "Keine Credentials" not in text, text[:60])
    except ImportError:
        pruefe("Eingabe-Pruefung laeuft vor dem fints-Import", False,
               "fints wurde zuerst importiert")


# ---- 2. TAN-Verfahren nicht im Dialog -------------------------------
def test_verfahren_nie_im_dialog():
    c = AttrappenClient()
    with c:
        mech, hinweis = tan.apply_mechanism(c, "921")
    pruefe("apply_mechanism setzt im Dialog nichts", c.gesetzte_verfahren == [],
           str(c.gesetzte_verfahren))
    pruefe("apply_mechanism wirft im Dialog nicht", isinstance(hinweis, str))


def test_kein_verfahren_ohne_wunsch():
    c = AttrappenClient(verfahren_vorher={"921": "pushTAN"})
    mech, hinweis = tan.apply_mechanism(c, None)
    pruefe("ohne ausdruecklichen Wunsch wird nichts gesetzt",
           mech is None and c.gesetzte_verfahren == [])
    pruefe("Hinweis nennt die Vorgabe der Bank", "Vorgabe der Bank" in hinweis)


def test_wunsch_wird_vor_dem_dialog_gesetzt():
    c = AttrappenClient(verfahren_vorher={"921": "pushTAN"})
    mech, _ = tan.apply_mechanism(c, "921")
    pruefe("ausdruecklicher Wunsch wird vor dem Dialog gesetzt",
           mech == "921" and c.gesetzte_verfahren == ["921"])


# ---- 3. Leere Verfahrensliste nicht stumm schlucken -----------------
def test_leere_liste_meldet_sich():
    c = AttrappenClient(verfahren_vorher={})       # Sparkasse vor der Anmeldung
    mech, hinweis = tan.apply_mechanism(c, "921")
    pruefe("leere Verfahrensliste setzt nichts", mech is None and c.gesetzte_verfahren == [])
    pruefe("leere Verfahrensliste wird im Klartext gemeldet",
           "keine Verfahren" in hinweis and "Vorgabe der Bank" in hinweis, hinweis[:70])


def test_unbekanntes_verfahren():
    c = AttrappenClient(verfahren_vorher={"911": "chipTAN"})
    mech, hinweis = tan.apply_mechanism(c, "999")
    pruefe("unbekanntes Verfahren wird nicht gesetzt", mech is None)
    pruefe("Meldung listet die bekannten Verfahren", "911" in hinweis, hinweis[:70])


# ---- 4. Anmelde-TAN -------------------------------------------------
def test_anmelde_tan_wird_abgefragt():
    c = AttrappenClient(login_tan=True)
    with c:
        pruefe("Anmelde-TAN wird erkannt", tan.login_tan_pending(c))
        behandelt = tan.handle_login_tan(c, ask=lambda ch: "123456")
    pruefe("Anmelde-TAN wird beantwortet", behandelt and c.gesendete_tans == [("ANMELDE-TAN", "123456")],
           str(c.gesendete_tans))
    pruefe("nach der Anmelde-TAN steht kein Rest offen", not tan.login_tan_pending(c))


def test_ohne_anmelde_tan_passiert_nichts():
    c = AttrappenClient(login_tan=False)
    with c:
        behandelt = tan.handle_login_tan(c, ask=lambda ch: "999999")
    pruefe("ohne Anmelde-TAN wird nichts gefragt", behandelt is False and c.gesendete_tans == [])


# ---- Statische Sperre: der eigentliche Regressionsnagel -------------
def test_quelltext_setzt_kein_verfahren_im_dialog():
    """Verhindert, dass jemand set_tan_mechanism wieder in einen 'with'-Block
    schreibt. Genau das war der Konstruktionsfehler, und er stand an ZWEI
    Stellen, nicht an einer."""
    treffer = []
    for datei in sorted((_SCRIPTS).rglob("*.py")):
        if datei.name == "selbsttest.py":
            continue
        tiefe_dialog = None
        for nr, zeile in enumerate(datei.read_text(encoding="utf-8").splitlines(), 1):
            if not zeile.strip() or zeile.lstrip().startswith("#"):
                continue
            einzug = len(zeile) - len(zeile.lstrip())
            if tiefe_dialog is not None and einzug <= tiefe_dialog:
                tiefe_dialog = None
            if re.match(r"\s*with\s+\w+\s*:", zeile):
                tiefe_dialog = einzug
                continue
            if tiefe_dialog is not None and "set_tan_mechanism(" in zeile:
                treffer.append(f"{datei.name}:{nr}")
    pruefe("kein set_tan_mechanism innerhalb eines Dialogs", not treffer, ", ".join(treffer))


def test_registry_liest_blz():
    info = registry.lookup_by_iban("DE02120300000000202051")
    pruefe("BLZ wird aus der IBAN gelesen", info["blz"] == "12030000", info["blz"])
    try:
        registry.lookup_by_iban("GB33BUKB20201555555555")
        pruefe("Nicht-DE-IBAN wird abgelehnt", False)
    except ValueError:
        pruefe("Nicht-DE-IBAN wird abgelehnt", True)


# ---- photoTAN / Grafik-Challenge (Befund 2026-08-26, Kundenbericht) -
class GrafikChallenge:
    """NeedTANResponse-Attrappe einer photoTAN-Bank. Genau so kam es von der
    Commerzbank: ein Begleitsatz plus ein PNG, das gescannt werden muss."""

    # 1x1-PNG, reicht als Nachweis, dass die Bytes unveraendert durchlaufen
    PNG = bytes.fromhex(
        "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4"
        "890000000a49444154789c63000100000500010d0a2db40000000049454e44ae426082"
    )

    def __init__(self, matrix=True, hhduc=None, decoupled=False):
        self.challenge = "Dies ist Ihre photoTAN Challenge."
        self.challenge_hhduc = hhduc
        self.challenge_matrix = ("image/png", self.PNG) if matrix else None
        self.decoupled = decoupled


def test_phototan_grafik_wird_herausgeschrieben():
    """DER Fehler: challenge_matrix wurde nie ausgewertet. Der Anwender sah nur
    den Begleitsatz, hatte nichts zu scannen und lief in Bankfehler 9340."""
    pfad = tan.zeige_matrix(GrafikChallenge(), oeffnen=False)
    pruefe("photoTAN-Grafik wird herausgeschrieben", pfad is not None)
    if not pfad:
        return
    try:
        daten = Path(pfad).read_bytes()
        pruefe("Grafik ist unveraendert", daten == GrafikChallenge.PNG, f"{len(daten)} Bytes")
        pruefe("Grafik wird als PNG erkannt", str(pfad).endswith(".png"), str(pfad))
        rechte = Path(pfad).stat().st_mode & 0o777
        pruefe("Grafik ist nur fuer den Besitzer lesbar", rechte == 0o600, oct(rechte))
        pruefe("Grafik liegt nicht im offenen /tmp", not str(pfad).startswith("/tmp/"), str(pfad))
    finally:
        Path(pfad).unlink(missing_ok=True)


def test_ohne_grafik_keine_datei():
    """chipTAN und pushTAN duerfen keine leere Datei erzeugen."""
    pruefe("ohne Matrix wird nichts geschrieben",
           tan.zeige_matrix(GrafikChallenge(matrix=False), oeffnen=False) is None)


def test_eingabetext_passt_zum_verfahren():
    """Frueher stand pauschal 'bei pushTAN: in der App bestaetigen'. Bei
    photoTAN gibt es nichts zu bestaetigen, das schickte Anwender in die
    falsche Richtung."""
    foto = tan._eingabe_text(GrafikChallenge(), hat_grafik=True)
    pruefe("photoTAN-Text sagt scannen", "scann" in foto.lower(), foto)
    pruefe("photoTAN-Text behauptet kein pushTAN", "pushtan" not in foto.lower(), foto)

    ent = tan._eingabe_text(GrafikChallenge(decoupled=True), hat_grafik=False)
    pruefe("entkoppelt: keine TAN eintippen", "keine tan" in ent.lower(), ent)

    chip = tan._eingabe_text(GrafikChallenge(matrix=False, hhduc="0389..."), hat_grafik=False)
    pruefe("chipTAN-Text nennt den Generator", "generator" in chip.lower(), chip)


# ---- Entkoppelte Freigabe (decoupled) -------------------------------
def _mit_fints_attrappe(fn):
    """fints.client.NeedTANResponse als Attrappe stellen. Haelt den Test frei
    von einer echten Installation UND deterministisch, falls doch eine da ist."""
    import types

    gesichert = {k: sys.modules.get(k) for k in ("fints", "fints.client")}
    fints_mod = types.ModuleType("fints")
    client_mod = types.ModuleType("fints.client")

    class NeedTANResponse:
        pass

    client_mod.NeedTANResponse = NeedTANResponse
    fints_mod.client = client_mod
    sys.modules["fints"] = fints_mod
    sys.modules["fints.client"] = client_mod
    try:
        return fn(NeedTANResponse)
    finally:
        for k, v in gesichert.items():
            if v is None:
                sys.modules.pop(k, None)
            else:
                sys.modules[k] = v


class DecoupledClient:
    """Bank, die erst nach `bestaetigt_ab` Aufrufen freigibt. Bis dahin
    antwortet sie mit einem weiteren NeedTANResponse (Bankcode 3956)."""

    def __init__(self, offen_klasse, bestaetigt_ab=3):
        self._offen = offen_klasse
        self._bestaetigt_ab = bestaetigt_ab
        self.aufrufe = 0

    def send_tan(self, challenge, tan_wert):
        self.aufrufe += 1
        if self.aufrufe < self._bestaetigt_ab:
            return self._offen()
        return "KONTOAUSZUG"


def test_decoupled_wird_gepollt():
    """Bei entkoppelter Freigabe gibt send_tan wieder ein NeedTANResponse
    zurueck, solange der Mensch nicht freigegeben hat. Wer nur einmal sendet,
    haelt 'noch nicht bestaetigt' faelschlich fuer erledigt."""
    def lauf(offen_klasse):
        intervall = tan.DECOUPLED_INTERVALL_SEK
        tan.DECOUPLED_INTERVALL_SEK = 0  # Test darf nicht warten
        try:
            c = DecoupledClient(offen_klasse, bestaetigt_ab=3)
            ergebnis = tan.beantworte(c, GrafikChallenge(matrix=False, decoupled=True),
                                      ask=lambda ch: "")
            pruefe("entkoppelt: wird bis zur Freigabe gepollt", c.aufrufe == 3, f"{c.aufrufe} Aufrufe")
            pruefe("entkoppelt: liefert am Ende das Ergebnis", ergebnis == "KONTOAUSZUG", str(ergebnis))
        finally:
            tan.DECOUPLED_INTERVALL_SEK = intervall

    _mit_fints_attrappe(lauf)


def test_ohne_decoupled_wird_nur_einmal_gesendet():
    """Gegenprobe: bei normaler TAN darf NICHT gepollt werden."""
    def lauf(offen_klasse):
        c = DecoupledClient(offen_klasse, bestaetigt_ab=99)
        tan.beantworte(c, GrafikChallenge(matrix=False, decoupled=False), ask=lambda ch: "123456")
        pruefe("normale TAN wird genau einmal gesendet", c.aufrufe == 1, f"{c.aufrufe} Aufrufe")

    _mit_fints_attrappe(lauf)


# ---- Statische Sperren gegen Rueckfall ------------------------------
def test_send_tan_laeuft_nur_ueber_einen_weg():
    """send_tan darf NUR in tan.py aufgerufen werden. Ein direkter Aufruf
    anderswo umgeht die decoupled-Schleife und sieht dabei aus wie Erfolg."""
    treffer = []
    for datei in sorted(_SCRIPTS.rglob("*.py")):
        if datei.name in ("selbsttest.py", "tan.py"):
            continue
        for nr, zeile in enumerate(datei.read_text(encoding="utf-8").splitlines(), 1):
            if zeile.lstrip().startswith("#"):
                continue
            if ".send_tan(" in zeile:
                treffer.append(f"{datei.name}:{nr}")
    pruefe("send_tan wird nur zentral in tan.py aufgerufen", not treffer, ", ".join(treffer))


def test_jeder_dialog_gibt_den_gespeicherten_zustand_mit():
    """Ohne from_data ist die system_id unbelegt, python-fints fordert per
    HKSYN3 eine NEUE an, und die Bank sieht einen fremden Client. Ein fremder
    Client bekommt keine SCA-Ausnahme: es kommt bei jedem Abruf wieder eine TAN.
    (Befund 2026-08-26, Kundenbericht Commerzbank.)

    Geprueft wird JEDE Stelle, nicht nur cmd_reauth: der Fehler stand an zwei
    Stellen, genau wie seinerzeit set_tan_mechanism. Einzige erlaubte Ausnahme
    ist der Erstkontakt in cmd_add, dort gibt es noch keine Sitzung; er ist
    daran zu erkennen, dass er login/pin ausdruecklich mitgibt."""
    quelle = (_SCRIPTS / "banking" / "setup.py").read_text(encoding="utf-8")
    verdaechtig = []
    for nr, zeile in enumerate(quelle.splitlines(), 1):
        if "build_client(" not in zeile or zeile.lstrip().startswith("#"):
            continue
        if "from_data" in zeile:
            continue
        if "login=" in zeile and "pin=" in zeile:  # Erstkontakt, hat noch keine Sitzung
            continue
        verdaechtig.append(f"setup.py:{nr}: {zeile.strip()}")
    pruefe("jeder Dialog gibt die gespeicherte Sitzung mit", not verdaechtig,
           " | ".join(verdaechtig))
    pruefe("cmd_add darf ohne Sitzung bauen (Erstkontakt)",
           "build_client(bank, login=login, pin=pin)" in quelle)

# ---- Konten: zwei Quellen, nichts still wegwerfen ------------------
def _mit_fints_modellen(fn):
    """fints.models.SEPAAccount UND fints.client.NeedTANResponse als Attrappe
    stellen (kein Netz, keine Bank, keine Installation noetig)."""
    import types

    schluessel = ("fints", "fints.models", "fints.client")
    gesichert = {k: sys.modules.get(k) for k in schluessel}
    fints_mod = types.ModuleType("fints")
    models_mod = types.ModuleType("fints.models")
    client_mod = types.ModuleType("fints.client")

    class SEPAAccount:
        def __init__(self, iban, bic, accountnumber, subaccount, blz):
            self.iban, self.bic = iban, bic
            self.accountnumber, self.subaccount, self.blz = accountnumber, subaccount, blz

    class NeedTANResponse:
        pass

    models_mod.SEPAAccount = SEPAAccount
    client_mod.NeedTANResponse = NeedTANResponse
    fints_mod.models, fints_mod.client = models_mod, client_mod
    sys.modules["fints"] = fints_mod
    sys.modules["fints.models"] = models_mod
    sys.modules["fints.client"] = client_mod
    try:
        return fn(SEPAAccount)
    finally:
        for k, v in gesichert.items():
            if v is None:
                sys.modules.pop(k, None)
            else:
                sys.modules[k] = v


class Kennung:
    def __init__(self, bank_code):
        self.bank_code = bank_code


class SepaKonto:
    """Was get_sepa_accounts() zurueckgibt."""

    def __init__(self, iban, bic=""):
        self.iban, self.bic = iban, bic


class KontenClient:
    """Bank mit fuenf Konten, von denen sie nur eines als SEPA-faehig meldet.
    Genau die Lage bei der Commerzbank im Bericht vom 26.08.2026."""

    HAUPT = "DE48370400440894701200"
    WEITERE = [
        ("DE13370400440860083500", "0860083500", "EUR100", "9216798300"),
        ("DE89370400440894725100", "0894725100", "EUR101", "9216798301"),
    ]

    def get_sepa_accounts(self):
        # Die Bank meldet nur EIN Konto als SEPA-faehig.
        return [SepaKonto(self.HAUPT, "COBADEFF")]

    def get_information(self):
        konten = [{
            "iban": self.HAUPT, "account_number": "0894701200",
            "subaccount_number": "EUR100", "bank_identifier": Kennung("37040044"),
            "customer_id": "9216798299", "type": 10, "currency": "EUR",
        }]
        for iban, nr, unter, kunde in self.WEITERE:
            konten.append({
                "iban": iban, "account_number": nr, "subaccount_number": unter,
                "bank_identifier": Kennung("37040044"), "customer_id": kunde,
                "type": 10, "currency": "EUR",
            })
        return {"bank": {}, "accounts": konten, "auth": {}}


def test_konten_aus_beiden_quellen():
    """python-fints wirft in get_sepa_accounts() jedes Konto weg, das die Bank
    nicht als SEPA-faehig markiert (as_sepa_account gibt None, die None werden
    gefiltert). Fremdwaehrungs- und Kreditkonten verschwinden damit lautlos.
    Die UPD kennt sie trotzdem."""
    def lauf(_):
        c = KontenClient()
        konten = bank_client.konten_vereinen(c, [SepaKonto(KontenClient.HAUPT, "COBADEFF")])
        ibans = [k["iban"] for k in konten]
        pruefe("alle Konten der Bank kommen an", len(konten) == 3, f"{len(konten)}: {ibans}")
        pruefe("das SEPA-Konto ist genau einmal drin",
               ibans.count(KontenClient.HAUPT) == 1, str(ibans))
        quellen = {k["iban"]: k["quelle"] for k in konten}
        pruefe("Herkunft wird mitgefuehrt",
               quellen.get(KontenClient.HAUPT) == "sepa"
               and quellen.get("DE89370400440894725100") == "upd", str(quellen))

    _mit_fints_modellen(lauf)


def test_unterkontomerkmal_kommt_aus_der_bank():
    """DER Grund fuer Bankfehler 9010: das Unterkontomerkmal ist Teil der
    Kontoadresse (bei der Commerzbank z.B. 'EUR100') und laesst sich aus einer
    IBAN NICHT ableiten. Wer ein Konto allein aus der IBAN baut, schickt eine
    unvollstaendige Adresse und wird abgewiesen."""
    def lauf(_):
        c = KontenClient()
        konten = bank_client.konten_vereinen(c, [])
        nach_iban = {k["iban"]: k for k in konten}
        obj = nach_iban["DE89370400440894725100"]["_obj"]
        pruefe("Unterkontomerkmal wird uebernommen", obj.subaccount == "EUR101", repr(obj.subaccount))
        pruefe("Kontonummer wird uebernommen", obj.accountnumber == "0894725100", repr(obj.accountnumber))
        pruefe("BLZ wird uebernommen", obj.blz == "37040044", repr(obj.blz))
        pruefe("Kundennummer je Konto wird mitgefuehrt",
               nach_iban["DE89370400440894725100"]["customer_id"] == "9216798301",
               nach_iban["DE89370400440894725100"]["customer_id"])

    _mit_fints_modellen(lauf)


def test_upd_ausfall_kippt_den_abruf_nicht():
    """Kennt eine Bank get_information() nicht, bleibt es bei den SEPA-Konten.
    Ein Zusatzweg darf den Hauptweg nie mitreissen."""
    class Kaputt:
        def get_information(self):
            raise RuntimeError("kennt die Bank nicht")

    konten = bank_client.konten_vereinen(Kaputt(), [SepaKonto("DE48370400440894701200")])
    pruefe("SEPA-Konten bleiben bei UPD-Ausfall erhalten", len(konten) == 1, str(len(konten)))


def test_fetch_accounts_verliert_kein_konto():
    """Der eigentliche Nagel: fetch_accounts ist der Weg, den der taegliche
    Abruf nimmt. Baut ihn jemand auf die nackte SEPA-Liste zurueck, verschwinden
    alle nicht-SEPA-Konten, ohne dass irgendwo ein Fehler erscheint."""
    def lauf(_):
        konten = bank_client.fetch_accounts(KontenClient())
        pruefe("fetch_accounts liefert alle Konten der Bank",
               konten is not None and len(konten) == 3,
               str(len(konten) if konten else konten))
        pruefe("auch das Einrichten nutzt beide Quellen",
               (_SCRIPTS / "banking" / "setup.py").read_text(encoding="utf-8")
               .count("konten_vereinen(") >= 2)

    _mit_fints_modellen(lauf)


# ---- 5. Zweiter Weg: PSD2 -------------------------------------------
# Die fuenf Datenfallen unten sind KEINE Theorie. Jede einzelne hat an echten
# Konten schon einmal still falsche Zahlen erzeugt, und keine davon wirft einen
# Fehler -- man sieht nur irgendwann eine Summe, die nicht stimmt.

def test_psd2_gleiche_iban_zwei_schluessel():
    """Ein Sparkonto kann DIESELBE IBAN tragen wie das Girokonto daneben.
    Bekaemen beide denselben Schluessel, ueberschriebe der eine Saldo den
    anderen und in der Vermoegenssumme fehlte ein ganzes Konto."""
    from banking import psd2
    # Erfundene Kennung, ausdruecklich KEINE echte IBAN. Hier stand beim Bau
    # kurz eine aus einem laufenden Setup -- der Leck-Scan hat sie durchgewinkt,
    # weil IBANs in dieser Datei als Beispiele freigegeben sind. Deshalb hier
    # nur Werte, die erkennbar niemandem gehoeren.
    konten = [
        {"iban": "LT99TESTKONTO00000001", "name": "Current", "product": "Current"},
        {"iban": "LT99TESTKONTO00000001", "name": "Sparen", "product": "Savings"},
    ]
    gemeldet = []
    sk = psd2.schluessel_vergeben("revolut", konten, melden=gemeldet.append)
    pruefe("gleiche IBAN ergibt zwei verschiedene Schluessel",
           len(set(sk)) == 2, str(sk))
    pruefe("das Hauptkonto behaelt den nackten Schluessel",
           sk[0] == "LT99TESTKONTO00000001", sk[0])
    pruefe("das Nebenkonto bekommt den Produkt-Zusatz",
           sk[1] == "LT99TESTKONTO00000001:Savings", sk[1])
    pruefe("die Kollision wird gemeldet, nie stillschweigend", len(gemeldet) == 1)


def test_psd2_kollision_ohne_hauptkonto_warnt():
    """Sieht keins der Konten nach Hauptkonto aus, wird die Wahl geraten. Das
    MUSS dabeistehen, sonst haelt man ein geratenes Ergebnis fuer gemessen."""
    from banking import psd2
    konten = [{"iban": "DE02120300000000202051", "name": "Topf A", "product": "Pocket"},
              {"iban": "DE02120300000000202051", "name": "Topf B", "product": "Pocket"}]
    gemeldet = []
    psd2.schluessel_vergeben("x", konten, melden=gemeldet.append)
    pruefe("geratene Zuordnung wird ausdruecklich gewarnt",
           gemeldet and "geraten" in gemeldet[0].lower(), str(gemeldet))


def test_psd2_konto_ohne_iban_geht_nicht_verloren():
    """PayPal hat gar keine IBAN. Ohne Ersatzschluessel faellt das Konto aus
    der Tabelle, ohne dass irgendwo ein Fehler erscheint."""
    from banking import psd2
    sk = psd2.schluessel_vergeben("paypal", [{"iban": None, "name": "Mein Konto"}])
    pruefe("Konto ohne IBAN bekommt einen Schluessel", bool(sk[0]), str(sk))
    pruefe("der Schluessel nennt die Verbindung", sk[0].startswith("paypal:"), sk[0])


def test_psd2_vorgemerkte_buchung_ist_erkennbar():
    """Vorgemerkte Buchungen (PDNG) werden gespeichert, duerfen aber nie in
    eine Summe. Ohne die Spalte zaehlen sie als echt mit."""
    from banking import psd2
    t = psd2.umsatz_flach("DE1", {"status": "PDNG", "booking_date": "2026-08-30",
                                  "transaction_amount": {"amount": "10.00", "currency": "EUR"},
                                  "credit_debit_indicator": "DBIT"})
    pruefe("vorgemerkt wird als PDNG markiert", t["status"] == "PDNG", t["status"])
    gebucht = psd2.umsatz_flach("DE1", {"booking_date": "2026-08-30",
                                        "transaction_amount": {"amount": "10.00"},
                                        "credit_debit_indicator": "CRDT"})
    pruefe("ohne Angabe gilt eine Buchung als gebucht", gebucht["status"] == "BOOK",
           gebucht["status"])


def test_psd2_vorzeichen_wird_selbst_gesetzt():
    """Die Bank liefert IMMER positiv, mit einer Richtungsangabe daneben. Ohne
    eigenes Vorzeichen ist jede Summe falsch, und es faellt nicht auf, weil die
    Einzelwerte stimmen."""
    from banking import psd2
    raus = psd2.umsatz_flach("DE1", {"transaction_amount": {"amount": "42.50"},
                                     "credit_debit_indicator": "DBIT",
                                     "booking_date": "2026-08-30"})
    rein = psd2.umsatz_flach("DE1", {"transaction_amount": {"amount": "42.50"},
                                     "credit_debit_indicator": "CRDT",
                                     "booking_date": "2026-08-30"})
    pruefe("Ausgang wird negativ", raus["amount"] == -42.5, str(raus["amount"]))
    pruefe("Eingang bleibt positiv", rein["amount"] == 42.5, str(rein["amount"]))


def test_psd2_datum_wird_aufgeloest():
    """Jede Bank fuellt ANDERE Datumsfelder. PayPal fuellt NUR
    transaction_date -- ohne Aufloesung haetten diese Zeilen gar kein Datum
    und fielen aus jeder Sortierung."""
    from banking import psd2
    nur_transaktion = {"transaction_date": "2026-08-29",
                       "transaction_amount": {"amount": "1.00"},
                       "credit_debit_indicator": "CRDT"}
    t = psd2.umsatz_flach("paypal:x", nur_transaktion)
    pruefe("Buchung nur mit transaction_date bekommt ein Datum",
           t["booking_date"] == "2026-08-29", str(t["booking_date"]))
    pruefe("Buchungsdatum hat Vorrang, wenn es da ist",
           psd2.datum_von({"booking_date": "2026-01-01", "value_date": "2026-02-02",
                           "transaction_date": "2026-03-03"}) == "2026-01-01")


def test_psd2_fenster_wird_nachgefiltert():
    """Manche Bank ignoriert date_from und liefert immer ihren ganzen Bestand.
    Ohne Nachfilter ist das Fenster wertlos."""
    from banking import psd2
    alt = {"booking_date": "2020-01-01"}
    neu = {"booking_date": "2026-08-30"}
    pruefe("alte Buchung faellt aus dem Fenster",
           not psd2.im_fenster(alt, "2026-06-01"))
    pruefe("neue Buchung bleibt drin", psd2.im_fenster(neu, "2026-06-01"))
    pruefe("ohne Fenster wird nichts weggeworfen", psd2.im_fenster(alt, None))


def test_psd2_nur_ein_saldo_je_konto_und_tag():
    """banking_balances haelt genau EINEN Wert je Konto und Tag. Wuerden alle
    Arten geschrieben, ueberschriebe die letzte still die erste und welcher
    Wert gewinnt haenge an der Reihenfolge der Antwort."""
    from banking import psd2
    liste = [
        {"balance_type": "OTHR", "balance_amount": {"amount": "1.00", "currency": "EUR"}},
        {"balance_type": "CLBD", "balance_amount": {"amount": "500.00", "currency": "EUR"}},
        {"balance_type": "ITAV", "balance_amount": {"amount": "480.00", "currency": "EUR"}},
    ]
    best = psd2.massgeblicher_saldo(liste)
    pruefe("aus mehreren Saldo-Arten gewinnt die hoechstrangige",
           best and best["art"] == "CLBD" and best["betrag"] == 500.0, str(best))
    pruefe("ohne Salden kommt nichts zurueck", psd2.massgeblicher_saldo([]) is None)


def test_psd2_umsatz_id_ist_stabil():
    """Die ID darf NICHT an der account_uid haengen: die vergibt Enable Banking
    je Sitzung neu, und nach jeder Erneuerung bekaeme jeder Umsatz eine zweite
    Zeile."""
    from banking import psd2
    t = {"entry_reference": "ABC123", "transaction_amount": {"amount": "5.00"}}
    pruefe("gleiche Buchung ergibt gleiche ID",
           psd2.umsatz_id("DE1", t) == psd2.umsatz_id("DE1", t))
    ohne = {"booking_date": "2026-08-30", "transaction_amount": {"amount": "5.00"},
            "credit_debit_indicator": "DBIT"}
    pruefe("auch ohne Referenz entsteht eine stabile ID",
           psd2.umsatz_id("DE1", ohne) == psd2.umsatz_id("DE1", ohne))
    pruefe("verschiedene Konten ergeben verschiedene IDs",
           psd2.umsatz_id("DE1", t) != psd2.umsatz_id("DE2", t))


def test_psd2_code_aus_ganzer_adresse():
    """Menschen kopieren die ganze Adresszeile. Danach zu suchen ist
    zuverlaessiger, als jemanden das richtige Stueck ausschneiden zu lassen."""
    from banking import psd2
    pruefe("Code wird aus der ganzen Adresse geholt",
           psd2.code_aus("https://x.de/cb?state=a&code=XYZ789&s=1") == "XYZ789")
    pruefe("blanker Code geht auch durch", psd2.code_aus("XYZ789") == "XYZ789")
    pruefe("leere Eingabe ergibt nichts", psd2.code_aus("") == "")


def test_psd2_ruehrt_kein_geld_an():
    """Die Application ist auf AIS beschraenkt. Diese Datei darf gar nicht erst
    einen Endpunkt kennen, der etwas ausloesen koennte."""
    quelle = (_SCRIPTS / "banking" / "psd2.py").read_text(encoding="utf-8")
    for verboten in ("/payments", "payment_request", "/sessions/payment", "initiate"):
        pruefe(f"psd2.py kennt keinen Schreib-Endpunkt ({verboten})",
               verboten not in quelle)


# ---- 6. Zwei Wege, eine Tabellenfamilie -----------------------------

def test_altkonfig_gilt_als_fints():
    """Eintraege aus der Zeit vor dem zweiten Weg haben weder 'key' noch 'weg'.
    Werden sie nicht als FinTS gelesen, verschwinden bestehende Banken
    stillschweigend aus dem Abruf."""
    from banking import config_store
    alt = {"blz": "12345678", "label": "Alte Bank"}
    pruefe("Alt-Eintrag gilt als FinTS",
           config_store.bank_weg(alt) == config_store.WEG_FINTS)
    pruefe("Alt-Eintrag behaelt die BLZ als Schluessel",
           config_store.bank_key(alt) == "12345678")
    neu = {"key": "revolut-cy", "weg": "psd2", "label": "Revolut"}
    pruefe("PSD2-Eintrag wird als PSD2 gelesen",
           config_store.bank_weg(neu) == config_store.WEG_PSD2)
    pruefe("PSD2-Eintrag nutzt seinen eigenen Schluessel",
           config_store.bank_key(neu) == "revolut-cy")


def test_collect_liefert_immer_einen_status():
    """Fehlt das status-Feld, wertet der Orchestrator den Lauf als Fehler MIT
    LEEREM GRUND -- eine Meldung jeden Morgen, an der man nichts erkennen kann."""
    import collect_banking as cb
    from banking import config_store
    original = config_store.load
    try:
        config_store.load = lambda: {"banks": []}
        r = cb.collect()
        pruefe("collect() ohne Bank hat ein status-Feld", "status" in r)
        pruefe("collect() ohne Bank meldet skipped", r.get("status") == "skipped",
               str(r.get("status")))
        pruefe("skipped nennt einen Grund", bool(r.get("reason")))
    finally:
        config_store.load = original


def test_ein_weg_kippt_den_anderen_nicht():
    """Faellt eine Bank aus, muss die andere trotzdem durchlaufen. Sonst nimmt
    eine kaputte Verbindung alle anderen mit."""
    import collect_banking as cb
    from banking import config_store, psd2
    original_load, original_session = config_store.load, psd2.session
    try:
        config_store.load = lambda: {"banks": [
            {"key": "kaputt", "weg": "psd2", "label": "Ohne Freigabe"},
            {"key": "auch-kaputt", "weg": "psd2", "label": "Zweite"},
        ]}
        psd2.session = lambda name: None
        r = cb.collect()
        pruefe("ein Lauf ohne jede Freigabe bricht nicht ab",
               r.get("status") == "success", str(r.get("status")))
        zustaende = r["data"]["sync_state"]
        pruefe("beide Verbindungen werden gemeldet, nicht nur die erste",
               len(zustaende) == 2, str(len(zustaende)))
        pruefe("fehlende Freigabe wird als needs_tan gemeldet",
               all(s["needs_tan"] == 1 for s in zustaende))
        pruefe("die Meldung nennt den Weg zurueck",
               all("psd2-reauth" in s["message"] for s in zustaende))
    finally:
        config_store.load, psd2.session = original_load, original_session


def test_schema_wird_additiv_nachgezogen():
    """Der Umbau darf keine bestehende Installation zwingen, ihre Historie
    wegzuwerfen. Neue Spalten kommen per ALTER TABLE dazu, alte Zeilen bleiben."""
    import sqlite3
    import collect_banking as cb
    conn = sqlite3.connect(":memory:")
    # Eine Tabelle im ALTEN Zustand, mit einer bestehenden Zeile.
    conn.execute("""CREATE TABLE banking_accounts (
        iban TEXT PRIMARY KEY, bank_label TEXT, blz TEXT, bic TEXT,
        currency TEXT, last_synced TEXT)""")
    conn.execute("INSERT INTO banking_accounts VALUES "
                 "('DE111','Alte Bank','12345678','X','EUR','2026-01-01')")
    cb.write(conn, {"status": "skipped"}, "2026-08-31")
    spalten = {r[1] for r in conn.execute("PRAGMA table_info(banking_accounts)")}
    for neu in ("weg", "institut", "land", "konto_name", "iban_klar"):
        pruefe(f"Spalte {neu} wird nachgezogen", neu in spalten)
    zeilen = list(conn.execute("SELECT iban, bank_label FROM banking_accounts"))
    pruefe("die bestehende Zeile ueberlebt den Nachzug",
           zeilen == [("DE111", "Alte Bank")], str(zeilen))
    conn.close()


def test_fints_zeilen_aendern_sich_nicht():
    """Gegenprobe zur Nicht-Rueckwirkung: ein FinTS-Umsatz muss nach dem Umbau
    exakt dieselben Werte schreiben wie vorher, plus die neuen Spalten."""
    import sqlite3
    import collect_banking as cb
    conn = sqlite3.connect(":memory:")
    ergebnis = {"status": "success", "data": {
        "accounts": [{"iban": "DE111", "bank_label": "Bank", "blz": "12345678",
                      "bic": "X", "currency": "EUR", "weg": "fints"}],
        "balances": [{"iban": "DE111", "balance": 100.0, "currency": "EUR"}],
        "transactions": [{"txn_id": "t1", "iban": "DE111", "booking_date": "2026-08-30",
                          "value_date": "2026-08-30", "amount": -5.0, "currency": "EUR",
                          "direction": "DBIT", "counterparty_name": "Laden",
                          "counterparty_iban": None, "purpose": "Kauf",
                          "posting_text": "REF", "weg": "fints"}],
        "sync_state": [{"blz": "12345678", "needs_tan": 0, "message": "", "weg": "fints"}],
    }}
    cb.write(conn, ergebnis, "2026-08-31")
    row = conn.execute("SELECT amount, status, weg FROM banking_transactions").fetchone()
    pruefe("FinTS-Betrag bleibt unveraendert", row[0] == -5.0, str(row[0]))
    pruefe("FinTS-Umsatz gilt als gebucht", row[1] == "BOOK", str(row[1]))
    pruefe("FinTS-Umsatz traegt seinen Weg", row[2] == "fints", str(row[2]))
    konto = conn.execute("SELECT iban_klar FROM banking_accounts").fetchone()
    pruefe("ohne eigene Angabe ist iban_klar die IBAN", konto[0] == "DE111", str(konto[0]))
    conn.close()


# ---- 7. Der Assistent entscheidet den Weg ---------------------------

def _fake_registry(mit_fints=True):
    def lookup(iban):
        if not iban.startswith("DE"):
            raise ValueError(f"Keine gueltige deutsche IBAN: {iban}")
        return {"blz": iban[4:12], "bank_name": "Testbank", "bic": "",
                "pintan_url": "https://fints.test/pin" if mit_fints else ""}
    return lookup


def test_assistent_waehlt_fints_wo_moeglich():
    from banking import assistent
    p = assistent.weg_fuer("DE89370400440532013000", _fake_registry(True))
    pruefe("deutsche Bank mit FinTS geht ueber FinTS",
           p["weg"] == assistent.WEG_FINTS, p["weg"])
    pruefe("die Entscheidung traegt immer einen Grund", bool(p.get("grund")))


def test_assistent_weicht_auf_psd2_aus():
    from banking import assistent
    ohne = assistent.weg_fuer("DE89370400440532013000", _fake_registry(False))
    pruefe("deutsche Bank ohne FinTS geht ueber PSD2",
           ohne["weg"] == assistent.WEG_PSD2, ohne["weg"])
    aus = assistent.weg_fuer("LT99TESTKONTO00000001", _fake_registry(True))
    pruefe("IBAN aus dem Ausland geht ueber PSD2",
           aus["weg"] == assistent.WEG_PSD2, aus["weg"])
    pruefe("das Land wird mitgegeben", aus.get("land") == "LT", str(aus.get("land")))
    marke = assistent.weg_fuer("Revolut", _fake_registry(True))
    pruefe("eine Neobank beim Namen geht ueber PSD2",
           marke["weg"] == assistent.WEG_PSD2, marke["weg"])


def test_assistent_sagt_was_gar_nicht_geht():
    """PSD2 deckt nur ZAHLUNGSkonten ab. Ein Sparkonto zu versuchen kostet nur
    Zeit -- und ein 'geht nicht' ohne Grund ist wertlos."""
    from banking import assistent
    for wort in ("Sparkonto bei meiner Bank", "mein Depot", "Festgeld"):
        p = assistent.weg_fuer(wort, _fake_registry(True))
        pruefe(f"'{wort}' wird als nicht anbindbar erkannt",
               p["weg"] == assistent.WEG_KEINER, p["weg"])
        pruefe(f"'{wort}' bekommt eine Begruendung", len(p.get("grund", "")) > 20)


def test_assistent_entscheidet_nicht_zur_laufzeit():
    """Ein automatischer Rueckfall im Tageslauf ist unmoeglich, weil beide Wege
    einen Menschen brauchen. Wer das doch einbaut, faellt hier auf."""
    quelle = (_SCRIPTS / "collect_banking.py").read_text(encoding="utf-8")
    pruefe("der Sammler richtet nichts ein",
           "psd2_setup" not in quelle and "assistent" not in quelle.split("Setup:")[0])
    pruefe("der Sammler fragt nie nach einer Eingabe",
           "input(" not in quelle)


def test_assistent_verspricht_keinen_weg_der_nicht_existiert():
    """C24 hat weder FinTS noch einen Zugang mit Benutzername und Passwort. Wer
    es in die Neobank-Liste stellt, schickt es auf PSD2 und verspricht dem
    Kunden einen Weg, den es nicht gibt -- beim Bau genau so passiert und nur
    im Trockenlauf aufgefallen, weil die eigene Doku etwas anderes sagte."""
    from banking import assistent
    p = assistent.weg_fuer("C24", _fake_registry(True))
    pruefe("C24 wird als nicht anbindbar erkannt",
           p["weg"] == assistent.WEG_KEINER, p["weg"])
    pruefe("und die Begruendung nennt den Grund",
           "QR" in p.get("grund", "") or "Passwort" in p.get("grund", ""))
    pruefe("Doku und Assistent widersprechen sich nicht",
           "C24" in (Path(__file__).resolve().parent.parent.parent
                     / "reference" / "welche-bank-welcher-weg.md").read_text(encoding="utf-8"))


def main():
    for fn in [v for k, v in sorted(globals().items()) if k.startswith("test_")]:
        try:
            fn()
        except Exception as e:
            FEHLER.append(f"{fn.__name__} ist abgestuerzt: {type(e).__name__}: {e}")

    for f in FEHLER:
        print(f"  FEHLER  {f}")
    print(f"\n{len(OK)} von {len(OK) + len(FEHLER)} Pruefungen bestanden.")
    if not FEHLER:
        print("Selbsttest gruen. (Deckt nicht ab, ob eine echte Bank annimmt.)")
    return 1 if FEHLER else 0


if __name__ == "__main__":
    sys.exit(main())
