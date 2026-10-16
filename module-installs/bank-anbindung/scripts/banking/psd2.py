"""
Banking - Weg 2: PSD2 ueber Enable Banking (AISP, read-only).

WOFUER: alles, was FinTS nicht kann. Neobanken (Revolut, N26, Trade Republic,
Wise), Konten ausserhalb Deutschlands, PayPal, und deutsche Banken ohne
FinTS-Zugang. FinTS bleibt der bevorzugte Weg, wo er verfuegbar ist -- kein
Dritter dazwischen, keine Drosselung, volle Historie.

WARUM UEBERHAUPT EIN DRITTER: Neobanken wie Revolut haben keine offene API
fuer Privatkunden (deren Open-Banking-Schnittstelle verlangt ein
eIDAS-Zertifikat und regulierten TPP-Status). Der offizielle Weg an die
eigenen Kontodaten fuehrt ueber einen lizenzierten Kontoinformationsdienst.
Enable Banking Oy (Finnland, FIN-FSA-registriert) bietet dafuer den Modus
"restricted production": kostenlos, und die Schnittstelle gibt AUSSCHLIESSLICH
die Konten heraus, die im Control Panel selbst verknuepft wurden. Das ist
zugleich die Sicherheitsgrenze.

HERKUNFT: portiert aus dem CEO-GPT-Hauptsetup (enable_banking.py +
collect_banken.py), Stand 2026-08-31. Es gibt diese Logik damit ZWEIMAL. Wer
hier einen Fehler behebt, schaut bitte nach, ob die andere Kopie denselben hat
-- genau dieses Auseinanderlaufen hat schon einmal drei Monate lang Fixes
verschluckt.

NUR LESEN: die Application ist auf den Dienst "AIS" beschraenkt. Es gibt in
dieser Datei keinen einzigen Aufruf, der Geld bewegen koennte, und der
Selbsttest wacht darueber.

BETRIEBSGRENZEN (nicht wegoptimieren):
  - Banken drosseln auf ~4 Abrufe pro Tag, wenn der Nutzer nicht aktiv dabei
    ist. Also EIN Lauf pro Tag, kein Polling.
  - Eine Freigabe gilt hoechstens 180 Tage, danach neu in der Bank-App bestaetigen.
  - Ohne "Link accounts" im Control Panel kommt eine LEERE Kontoliste zurueck.
    Das ist die haeufigste Stolperfalle und KEIN Fehler im Code.
  - Ohne erneute Freigabe reicht die Historie 90 Tage zurueck. Weiter zurueck
    baut sie sich nur lokal auf, Tag fuer Tag.

Der Zugang liegt als DATEIEN in data/banking/psd2/ (nicht in einer
Umgebungsdatei: ein mehrzeiliges Schluesselformat gehoert dort nicht hin).
Welche Dateien das sind, steht in reference/enable-banking.md.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from datetime import datetime, timedelta, timezone

from banking import config_store

API_BASE = "https://api.enablebanking.com"
JWT_ISSUER = "enablebanking.com"
JWT_AUDIENCE = "api.enablebanking.com"

# 180 Tage ist das Maximum der Banken. 179 lassen einen Tag Luft, damit ein
# Zeitzonen-Grenzfall die Freigabe nicht direkt beim Anlegen kippt.
CONSENT_DAYS = 179

TIMEOUT = 30
RETRY_MARKERS = (
    "NameResolutionError", "Name or service not known",
    "Temporary failure in name resolution", "Read timed out",
    "Connection timed out", "Connection refused", "Connection reset",
    "Connection aborted",
)

# Welcher Saldo gilt, wenn eine Bank mehrere Arten liefert. Feste Rangfolge
# statt "nimm den ersten": manche Bank meldet nur ITAV, andere XPCD/CLBD/OTHR.
# Ohne Rangfolge haenge es an der Reihenfolge der Antwort, welcher Wert in der
# Vermoegenssumme landet -- und die kann sich jederzeit aendern.
SALDO_RANG = {"CLBD": 1, "ITAV": 2, "CLAV": 3, "XPCD": 4, "OTHR": 9}

# Woerter, an denen ein HAUPTkonto erkennbar ist. Nur diese behalten bei einer
# Schluessel-Kollision den nackten Schluessel.
HAUPTKONTO = {"current", "current account", "giro", "girokonto", "main", "cacc",
              "checking", "payment", "compte courant", "multidevises"}

SCHLUESSEL_DATEI = "private" + "_key.pem"
APP_DATEI = "application_id.txt"
SITZUNGS_DATEI = "sessions.json"


class PSD2Error(RuntimeError):
    """Klartext-Fehler, der so an den Geschaeftsfuehrer gehen darf."""


# ---- Zugang ---------------------------------------------------------
def data_dir():
    return config_store.psd2_dir()


def key_path():
    return data_dir() / SCHLUESSEL_DATEI


def app_id_path():
    return data_dir() / APP_DATEI


def sessions_path():
    return data_dir() / SITZUNGS_DATEI


def zugang_da():
    """Liegt der Zugang? Fragt NICHTS ab, geht nicht ins Netz."""
    return key_path().exists() and app_id_path().exists()


def _read_credentials():
    if not zugang_da():
        raise PSD2Error(
            f"Enable-Banking-Zugang fehlt in {data_dir()}. Erwartet werden "
            f"{SCHLUESSEL_DATEI} und {APP_DATEI}. "
            "Anleitung: reference/enable-banking.md"
        )
    return app_id_path().read_text().strip(), key_path().read_bytes()


def _b64(data):
    if isinstance(data, dict):
        data = json.dumps(data, separators=(",", ":")).encode()
    return base64.urlsafe_b64encode(data).rstrip(b"=")


_token_cache = {"token": None, "exp": 0}


def token():
    """JWT/RS256, selbst signiert, eine Stunde gueltig. Im Prozess gecacht."""
    now = int(time.time())
    if _token_cache["token"] and now < _token_cache["exp"] - 60:
        return _token_cache["token"]
    try:
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import padding
    except ImportError:
        raise PSD2Error(
            "Die Bibliothek 'cryptography' fehlt. Sie wird nur fuer den "
            "PSD2-Weg gebraucht: pip install cryptography"
        ) from None

    app_id, pem = _read_credentials()
    key = serialization.load_pem_private_key(pem, password=None)
    exp = now + 3600
    signing_input = (
        _b64({"typ": "JWT", "alg": "RS256", "kid": app_id})
        + b"." + _b64({"iss": JWT_ISSUER, "aud": JWT_AUDIENCE, "iat": now, "exp": exp})
    )
    sig = key.sign(signing_input, padding.PKCS1v15(), hashes.SHA256())
    _token_cache["token"] = (signing_input + b"." + _b64(sig)).decode()
    _token_cache["exp"] = exp
    return _token_cache["token"]


def _call(method, path, body=None, _retried=False):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        API_BASE + path, data=data, method=method,
        headers={"Authorization": "Bearer " + token(),
                 "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            raw = resp.read()
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        detail = e.read().decode(errors="replace")[:600]
        raise PSD2Error(_klartext(e.code, detail, path)) from None
    except Exception as e:
        if not _retried and any(m in str(e) for m in RETRY_MARKERS):
            time.sleep(5)
            return _call(method, path, body, _retried=True)
        raise PSD2Error(f"{method} {path} -> {type(e).__name__}: {e}") from None


def _klartext(code, detail, path):
    """Die vier Fehler, die im Betrieb wirklich vorkommen, im Klartext statt
    als HTTP-Nummer. Alles andere bleibt roh, damit nichts verschleiert wird."""
    d = detail or ""
    if "WRONG_AUTHORIZATION_CODE" in d:
        return ("Der Code wurde abgelehnt. Der Freigabe-Fluss hat DREI Stationen "
                "(Bank -> Enable Banking -> Redirect-Adresse); nur der Code aus "
                "dem LETZTEN Sprung gilt. Bitte die Adresse ganz am Ende des "
                "Vorgangs kopieren, nicht die von der Zwischenseite.")
    if "EXPIRED_SESSION" in d or (code == 401 and "session" in d.lower()):
        return ("Die Freigabe ist abgelaufen (sie gilt hoechstens 180 Tage). "
                "Neu bestaetigen: setup.py psd2-reauth <name>")
    if code == 429:
        return ("Die Bank hat gedrosselt (~4 Abrufe pro Tag, wenn niemand aktiv "
                "dabei ist). Das ist kein Defekt, morgen laeuft es wieder. "
                "Wichtig: jetzt keinen zweiten Lauf hinterherschicken.")
    if code == 403:
        return (f"Zugriff verweigert ({path}). Haeufigster Grund: die "
                f"Application ist nicht aktiv oder der Dienst AIS fehlt. "
                f"Antwort der Schnittstelle: {d}")
    return f"{path} -> HTTP {code}: {d}"


def get(path):
    return _call("GET", path)


def post(path, body):
    return _call("POST", path, body)


# ---- Stammdaten -----------------------------------------------------
def application():
    return get("/application")


def redirect_url():
    """Die im Control Panel hinterlegte Redirect-Adresse. Bewusst gelesen statt
    hart verdrahtet -- aendert sie sich dort, zieht der Code automatisch mit."""
    urls = application().get("redirect_urls") or []
    if not urls:
        raise PSD2Error(
            "An der Application ist keine Redirect-Adresse hinterlegt. Ohne sie "
            "kann keine Freigabe zurueckkommen. Siehe reference/enable-banking.md"
        )
    return urls[0]


def aspsps(country):
    return get(f"/aspsps?country={urllib.parse.quote(country)}").get("aspsps", [])


def suche_banken(country, text=None):
    """Banken eines Landes, optional gefiltert. Fuer die Auswahl beim Einrichten."""
    out = []
    for b in aspsps(country):
        name = b.get("name") or ""
        if text and text.lower() not in name.lower():
            continue
        methoden = b.get("auth_methods") or []
        out.append({
            "name": name,
            "land": b.get("country"),
            "bic": b.get("bic") or "",
            "arten": sorted({m.get("approach") for m in methoden if m.get("approach")}),
            # Verlangt die Bank Zugangsdaten in einem FREMDEN Formular? Bei
            # REDIRECT gibt man sein Passwort nur der eigenen Bank. Das ist ein
            # echter Unterschied und gehoert vor die Wahl, nicht dahinter.
            "passwort_noetig": any((m.get("credentials") or []) for m in methoden),
        })
    return sorted(out, key=lambda x: x["name"])


def finde_bank(name, country):
    """Der Institutsname muss EXAKT dem Namen in der Enable-Banking-Liste
    entsprechen -- 'Sparkasse' allein reicht nicht, es gibt hunderte."""
    for a in aspsps(country):
        if (a.get("name") or "").strip().lower() == name.strip().lower():
            return a
    raise PSD2Error(
        f"Bank '{name}' steht nicht in der Liste fuer {country}. "
        f"Nachsehen mit: setup.py psd2-banken {country} {name.split()[0]}"
    )


# ---- Sitzungen ------------------------------------------------------
def _load_sessions():
    p = sessions_path()
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_sessions(sessions):
    d = data_dir()
    d.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(d, 0o700)
    except Exception:
        pass
    tmp = sessions_path().with_suffix(".json.tmp")
    tmp.write_text(json.dumps(sessions, indent=2, ensure_ascii=False), encoding="utf-8")
    try:
        os.chmod(tmp, 0o600)
    except Exception:
        pass
    os.replace(tmp, sessions_path())


def start_auth(institut, land, psu_type="personal", state="verbindung"):
    """Freigabe-Adresse erzeugen. Loest selbst nichts aus und speichert nichts."""
    bank = finde_bank(institut, land)
    gueltig_bis = datetime.now(timezone.utc) + timedelta(days=CONSENT_DAYS)
    antwort = post("/auth", {
        "access": {"valid_until": gueltig_bis.strftime("%Y-%m-%dT%H:%M:%S.000+00:00")},
        "aspsp": {"name": bank["name"], "country": bank["country"]},
        "psu_type": psu_type,
        "redirect_url": redirect_url(),
        "state": state,
    })
    return antwort.get("url"), antwort.get("authorization_id")


def code_aus(text):
    """Nimmt den Code ODER die ganze Adresszeile.

    Menschen kopieren die ganze Adresse, und danach zu suchen ist zuverlaessiger,
    als jemanden zu bitten, von Hand das richtige Stueck herauszuschneiden."""
    text = (text or "").strip()
    if not text:
        return ""
    if "code=" in text:
        return text.split("code=", 1)[1].split("&", 1)[0].strip()
    return text


def create_session(code, name):
    """Den Code gegen eine Freigabe tauschen und ablegen."""
    s = post("/sessions", {"code": code_aus(code)})
    konten = [
        {"uid": k.get("uid"),
         "iban": (k.get("account_id") or {}).get("iban"),
         "name": k.get("name") or k.get("product"),
         "product": k.get("product"),
         "cash_account_type": k.get("cash_account_type"),
         "currency": k.get("currency")}
        for k in (s.get("accounts") or [])
    ]
    sessions = _load_sessions()
    sessions[name] = {
        "session_id": s.get("session_id"),
        "gueltig_bis": (s.get("access") or {}).get("valid_until"),
        "angelegt_am": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "institut": (s.get("aspsp") or {}).get("name"),
        "land": (s.get("aspsp") or {}).get("country"),
        "konten": konten,
    }
    _save_sessions(sessions)
    return sessions[name]


def entferne_session(name):
    sessions = _load_sessions()
    if name in sessions:
        del sessions[name]
        _save_sessions(sessions)


def session(name):
    return _load_sessions().get(name)


def rest_tage(gueltig_bis):
    if not gueltig_bis:
        return None
    try:
        ende = datetime.fromisoformat(str(gueltig_bis).replace("Z", "+00:00"))
    except ValueError:
        return None
    return (ende - datetime.now(timezone.utc)).days


def zustand(rest):
    if rest is None:
        return "unbekannt"
    if rest < 0:
        return "abgelaufen"
    if rest < 14:
        return "laeuft bald ab"
    return "ok"


def sitzungs_status():
    out = []
    for name, s in _load_sessions().items():
        rest = rest_tage(s.get("gueltig_bis"))
        out.append({"verbindung": name, "institut": s.get("institut"),
                    "land": s.get("land"), "konten": len(s.get("konten") or []),
                    "gueltig_bis": s.get("gueltig_bis"), "rest_tage": rest,
                    "zustand": zustand(rest)})
    return out


# ---- Daten ----------------------------------------------------------
def balances(account_uid):
    return get(f"/accounts/{account_uid}/balances").get("balances", [])


def transactions(account_uid, date_from=None, date_to=None):
    """Alle Umsaetze im Fenster, ueber continuation_key durchgeblaettert."""
    params = {}
    if date_from:
        params["date_from"] = date_from
    if date_to:
        params["date_to"] = date_to
    alle, key, runden = [], None, 0
    while runden < 50:
        q = dict(params)
        if key:
            q["continuation_key"] = key
        pfad = f"/accounts/{account_uid}/transactions"
        if q:
            pfad += "?" + urllib.parse.urlencode(q)
        d = get(pfad)
        alle.extend(d.get("transactions", []))
        key = d.get("continuation_key")
        runden += 1
        if not key:
            break
    return alle


# ---- Aufbereitung ---------------------------------------------------
def _f(wert):
    try:
        return float(wert)
    except (TypeError, ValueError):
        return None


def _text(wert):
    """remittance_information ist eine LISTE, creditor/debtor ein dict."""
    if wert is None:
        return None
    if isinstance(wert, list):
        teile = [str(t).strip() for t in wert if t and str(t).strip()]
        return " | ".join(teile) or None
    s = str(wert).strip()
    return s or None


def konto_key(verbindung, konto):
    """Die STABILE Kennung eines Kontos.

    NICHT die account_uid nehmen: die vergibt Enable Banking je SITZUNG neu.
    Steckte sie im Schluessel, bekaeme nach jeder Erneuerung -- also
    spaetestens alle 180 Tage -- jedes Konto und jeder Umsatz eine zweite
    Zeile, und die Historie zerfiele in Bruchstuecke.

    IBAN ist die echte Identitaet. PayPal hat keine, dort traegt der Kontoname."""
    iban = _text(konto.get("iban"))
    if iban:
        return iban
    return f"{verbindung}:{_text(konto.get('name')) or 'konto'}"


def _zusatz_text(w):
    return (_text(w) or "Konto").strip().title()


def _zusatz(konto):
    for feld in ("product", "name", "cash_account_type"):
        w = _text(konto.get(feld))
        if w:
            return _zusatz_text(w)
    return "Konto"


def _ist_hauptkonto(konto):
    for feld in ("product", "cash_account_type", "name"):
        w = (_text(konto.get(feld)) or "").strip().lower()
        if w and w in HAUPTKONTO:
            return True
    return False


def schluessel_vergeben(verbindung, konten, melden=None):
    """Schluessel fuer ALLE Konten einer Verbindung auf einmal.

    Warum nicht je Konto einzeln: Unterkonten (Sparkonto, Pockets) koennen
    DIESELBE IBAN tragen wie das Girokonto. konto_key() gaebe dann beiden
    denselben Schluessel, der Saldo des einen ueberschriebe den des anderen,
    und in der Summe fehlte ein ganzes Konto -- ohne dass irgendwo ein Fehler
    erscheint.

    Das Hauptkonto behaelt den nackten Schluessel, damit eine bestehende
    Historie nicht abreisst. Nebenkonten bekommen '<IBAN>:<Produkt>'."""
    basis = [konto_key(verbindung, k) for k in konten]
    aus = list(basis)
    for b, n in Counter(basis).items():
        if n < 2:
            continue
        idx = [i for i, x in enumerate(basis) if x == b]
        halter = next((i for i in idx if _ist_hauptkonto(konten[i])), None)
        geraten = halter is None
        if geraten:
            halter = idx[0]
        for i in idx:
            if i != halter:
                aus[i] = f"{b}:{_zusatz(konten[i])}"
        if melden:
            liste = ", ".join(f"{_text(konten[i].get('name')) or '?'} -> {aus[i]}"
                              for i in idx)
            text = (f"{verbindung}: mehrere Konten teilen sich die Kennung {b}. "
                    f"Zuordnung: {liste}.")
            if geraten:
                text += (" ACHTUNG: keins davon sieht nach Hauptkonto aus, die "
                         "Wahl ist geraten. Bitte pruefen, bevor die Zahlen "
                         "verwendet werden.")
            melden(text)
    return aus


def massgeblicher_saldo(balance_liste):
    """Aus mehreren Saldo-Arten die EINE, die gilt.

    banking_balances hat PRIMARY KEY (date, iban), also genau einen Wert je
    Konto und Tag. Wuerden alle Arten geschrieben, ueberschriebe die letzte
    still die erste, und welcher Wert gewinnt haenge an der Reihenfolge der
    Antwort. Deshalb hier entscheiden, nicht in der Datenbank."""
    best = None
    for b in balance_liste or []:
        art = (b.get("balance_type") or "OTHR").upper()
        betrag = _f((b.get("balance_amount") or {}).get("amount"))
        if betrag is None:
            continue
        rang = SALDO_RANG.get(art, 10)
        if best is None or rang < best["rang"]:
            best = {"betrag": betrag,
                    "currency": (b.get("balance_amount") or {}).get("currency"),
                    "art": art, "rang": rang}
    return best


def datum_von(t):
    """Das eine Datum, auf das sich Sortierung und Filter verlassen koennen.

    Jede Bank fuellt ANDERE Felder (an echten Daten gemessen: die eine nur
    booking+value, die naechste alle drei, PayPal NUR transaction_date). Ohne
    diese Aufloesung haetten PayPal-Umsaetze gar kein Datum."""
    return t.get("booking_date") or t.get("value_date") or t.get("transaction_date")


def im_fenster(t, von):
    """Manche Bank haelt sich nicht an date_from und liefert immer ihren ganzen
    Bestand. Nachfiltern, sonst ist das Fenster wertlos."""
    if not von:
        return True
    d = datum_von(t)
    return bool(d) and d >= von


def umsatz_id(schluessel, t):
    """Stabile ID. entry_reference liefern die meisten Banken, PSD2 laesst es
    aber optional und manche Bank aendert es zwischen vorgemerkt und gebucht.
    Deshalb Rueckfall auf einen Fingerabdruck aus unveraenderlichen Merkmalen."""
    ref = _text(t.get("entry_reference")) or _text(t.get("transaction_id"))
    if ref:
        return f"{schluessel}:{ref}"
    betrag = t.get("transaction_amount") or {}
    roh = "|".join(str(x) for x in (
        schluessel,
        t.get("booking_date") or t.get("value_date") or "",
        betrag.get("amount") or "", betrag.get("currency") or "",
        t.get("credit_debit_indicator") or "",
        _text((t.get("creditor") or {}).get("name")) or "",
        _text((t.get("debtor") or {}).get("name")) or "",
        _text(t.get("remittance_information")) or "",
    ))
    return f"{schluessel}:h:{hashlib.sha256(roh.encode()).hexdigest()[:32]}"


def _gegenpartei(t):
    """Bei ausgehenden Buchungen ist der Empfaenger interessant, bei
    eingehenden der Absender. Manche Bank laesst beide Namen leer."""
    raus = (t.get("credit_debit_indicator") or "").upper() == "DBIT"
    primaer = (t.get("creditor") if raus else t.get("debtor")) or {}
    name = _text(primaer.get("name"))
    if name:
        return name
    andere = (t.get("debtor") if raus else t.get("creditor")) or {}
    return _text(andere.get("name"))


def _gegenkonto(t):
    raus = (t.get("credit_debit_indicator") or "").upper() == "DBIT"
    konto = (t.get("creditor_account") if raus else t.get("debtor_account")) or {}
    return _text(konto.get("iban"))


def umsatz_flach(schluessel, t):
    """Ein PSD2-Umsatz in der Form, die collect_banking.write() erwartet.

    Zwei Dinge passieren hier, die spaeter niemand mehr sieht:
      * Das Vorzeichen wird selbst gesetzt. Die Bank liefert IMMER positiv, mit
        einer Richtungsangabe daneben. Ohne das ist jede Summe falsch, und es
        faellt nicht auf, weil die Einzelwerte stimmen.
      * Das aufgeloeste Datum landet in booking_date, damit Zeilen ohne
        Buchungsdatum (PayPal) nicht aus jeder Sortierung fallen. Das Rohfeld
        bleibt in value_date stehen."""
    betrag_roh = t.get("transaction_amount") or {}
    betrag = _f(betrag_roh.get("amount"))
    richtung = (t.get("credit_debit_indicator") or "").upper()
    if betrag is not None and richtung == "DBIT":
        betrag = -betrag
    return {
        "txn_id": umsatz_id(schluessel, t),
        "iban": schluessel,
        "booking_date": datum_von(t),
        "value_date": t.get("value_date") or t.get("transaction_date"),
        "amount": betrag,
        "currency": betrag_roh.get("currency"),
        "direction": richtung or None,
        "counterparty_name": _gegenpartei(t),
        "counterparty_iban": _gegenkonto(t),
        "purpose": _text(t.get("remittance_information")),
        "posting_text": _text(t.get("entry_reference")),
        # BOOK = gebucht, PDNG = vorgemerkt. Vorgemerkte werden gespeichert,
        # aber nie in eine Summe gezaehlt.
        "status": (t.get("status") or "BOOK").upper(),
        "weg": "psd2",
    }
