"""
Banking - FinTS-Client-Wrapper (python-fints).

Gemeinsam genutzt von setup.py (interaktiv) und collect_banking.py (headless).
Read-only: Salden + Umsaetze. Keine Ueberweisungen.

Hinweis Issue #125 (python-fints): nach einem send_tan kann ein resumter,
mehrseitiger Umsatzabruf crashen. Loesung: Re-Auth in einem frischen Dialog
(setup.py reauth baut den Client ohne from_data neu) statt einen pausierten
Dialog fortzusetzen.
"""
from __future__ import annotations

import hashlib
from datetime import date, timedelta

from banking import keychain

# Oeffentlicher python-fints Product-Identifier, am BLSK-Prototyp (Sparkasse)
# am 2026-05-26 bewiesen. Ueberschreibbar via .env BANK_FINTS_PRODUCT_ID oder
# pro Bank in der Config. DK-Eigenregistrierung nur noetig, falls eine Bank
# mit 9078/3079 ablehnt.
DEFAULT_PRODUCT_ID = "9FA6681DEC0CF3046BFC2F8A6"


def build_client(bank, from_data=None, product_id=None, login=None, pin=None):
    """Baut einen FinTS3PinTanClient aus Bank-Config + Zugangsdaten.

    login/pin koennen ausdruecklich mitgegeben werden. Das Setup nutzt das, um
    die Zugangsdaten ERST ZU PRUEFEN und sie erst danach in den Schluesselbund
    zu schreiben. Ohne diesen Weg landete frueher auch ein leerer Anmeldename
    im Schluesselbund, und der Fehler tauchte spaeter als "Keine Credentials im
    Keychain" auf, also an einer Stelle, die mit der Ursache nichts zu tun hat.

    Ohne login/pin wird wie gehabt der Schluesselbund gelesen (headless-Weg)."""
    blz = bank["blz"]
    if login is None:
        login = keychain.get_login(blz)
    if pin is None:
        pin = keychain.get_pin(blz)
    login = (login or "").strip()
    pin = pin or ""
    if not login or not pin:
        fehlt = " und ".join(
            [t for t, v in (("Anmeldename", login), ("PIN", pin)) if not v]
        )
        raise RuntimeError(
            f"{fehlt} fehlt fuer BLZ {blz} (im Schluesselbund steht nichts oder ein "
            f"leerer Wert). Neu hinterlegen mit: "
            f"python scripts/banking/setup.py add"
        )
    from fints.client import FinTS3PinTanClient
    import os

    pid = (
        product_id
        or bank.get("product_id")
        or os.getenv("BANK_FINTS_PRODUCT_ID")
        or DEFAULT_PRODUCT_ID
    )
    kwargs = {"product_id": pid}
    if from_data:
        kwargs["from_data"] = from_data
    return FinTS3PinTanClient(blz, login, pin, bank["pintan_url"], **kwargs)


def needs_tan(obj):
    """True, wenn eine Operation eine TAN/SCA verlangt (headless = abbrechen)."""
    from fints.client import NeedTANResponse

    return isinstance(obj, NeedTANResponse)


def fetch_accounts(client):
    """Konten des Zugangs. Gibt Liste von Dicts (rohes Objekt unter _obj) oder
    None, wenn eine TAN noetig ist.

    ZWEI QUELLEN, UND DAS IST WICHTIG (Befund 2026-08-26, Kundenbericht Commerzbank):

    - `get_sepa_accounts()` fragt die Bank per HKSPA nach ihren SEPA-Konten.
      Diese Liste ist die bequeme, aber NICHT die vollstaendige: python-fints
      wirft dabei jedes Konto weg, das die Bank nicht als SEPA-faehig markiert
      (`as_sepa_account()` gibt dann None zurueck, und die None werden
      gefiltert). Fremdwaehrungs-, Geldmarkt- und Kreditkonten verschwinden so
      lautlos. Kein Fehler, keine Meldung, das Konto existiert einfach nicht.
    - Die Userparameterdaten (UPD) der Bank tragen JEDES Konto, das dieser
      Zugang bedienen darf, samt der Kundennummer, unter der es haengt.
      `client.get_information()['accounts']` liest sie aus.

    Zusammengefuehrt wird ueber die IBAN. Was nur in der UPD steht, wird
    ergaenzt statt ignoriert."""
    accounts = client.get_sepa_accounts()
    if needs_tan(accounts):
        return None
    return konten_vereinen(client, accounts)


def konten_vereinen(client, sepa_accounts):
    """SEPA-Liste plus die Konten, die nur in der UPD stehen. Siehe
    fetch_accounts fuer das Warum. Nimmt eine bereits geholte SEPA-Liste
    entgegen, damit der interaktive Weg (setup.py) nicht ein zweites Mal
    fragen und eine zweite TAN ausloesen muss."""
    out, gesehen = [], set()
    for a in sepa_accounts or []:
        iban = getattr(a, "iban", "") or ""
        gesehen.add(iban)
        out.append({
            "iban": iban,
            "bic": getattr(a, "bic", ""),
            "quelle": "sepa",
            "customer_id": "",
            "_obj": a,
        })
    out.extend(_konten_aus_upd(client, gesehen))
    return out


def _konten_aus_upd(client, schon_bekannt):
    """Konten, die in der UPD stehen, aber nicht in der SEPA-Liste ankamen.

    Das Unterkontomerkmal kommt hier aus der Bank und wird NIE geraten. Es ist
    Teil der Kontoadresse (bei der Commerzbank z.B. 'EUR100'), und aus einer
    IBAN laesst es sich nicht ableiten. Wer ein Konto allein aus der IBAN baut,
    schickt eine unvollstaendige Adresse, und die Bank antwortet mit 9010
    ('Konto nicht vorhanden oder unzulaessig'). Genau daran ist der Versuch
    gescheitert, die Konten von Hand zu adressieren."""
    try:
        from fints.models import SEPAAccount

        info = client.get_information() or {}
    except Exception:
        return []

    zusatz = []
    for acc in info.get("accounts", []):
        iban = acc.get("iban") or ""
        if not iban or iban in schon_bekannt:
            continue
        kennung = acc.get("bank_identifier")
        blz = getattr(kennung, "bank_code", "") or ""
        obj = SEPAAccount(
            iban=iban,
            bic="",
            accountnumber=acc.get("account_number") or "",
            subaccount=acc.get("subaccount_number") or "",  # aus der Bank, nie geraten
            blz=blz,
        )
        zusatz.append({
            "iban": iban,
            "bic": "",
            "quelle": "upd",
            "customer_id": acc.get("customer_id") or "",
            "_obj": obj,
        })
    return zusatz


def fetch_balance(client, account_obj):
    """Aktueller Saldo eines Kontos. None bei TAN-Bedarf."""
    bal = client.get_balance(account_obj)
    if needs_tan(bal):
        return None
    return {
        "amount": float(bal.amount.amount),
        "currency": bal.amount.currency,
        "date": str(getattr(bal, "date", "") or ""),
    }


def fetch_transactions(client, account_obj, days=90):
    """Umsaetze der letzten `days` Tage. None bei TAN-Bedarf."""
    end = date.today()
    start = end - timedelta(days=days)
    txns = client.get_transactions(account_obj, start, end)
    if needs_tan(txns):
        return None
    out = []
    for t in txns:
        d = t.data
        amount = d.get("amount")
        amt = float(amount.amount) if amount is not None else 0.0
        cur = amount.currency if amount is not None else "EUR"
        out.append(
            {
                "booking_date": str(d.get("date") or ""),
                "value_date": str(d.get("entry_date") or d.get("date") or ""),
                "amount": amt,
                "currency": cur,
                "direction": "in" if amt >= 0 else "out",
                "counterparty_name": (d.get("applicant_name") or "")[:200],
                "counterparty_iban": d.get("applicant_iban") or "",
                "purpose": (d.get("purpose") or "")[:500],
                "posting_text": d.get("posting_text") or "",
            }
        )
    return out


def txn_hash(iban, t):
    """Stabiler Dedup-Hash. FinTS/MT940 liefert keine eindeutigen IDs, daher
    Content-Hash aus den invarianten Feldern einer Buchung."""
    raw = "|".join(
        [
            iban or "",
            t.get("booking_date") or "",
            f"{t.get('amount', 0.0):.2f}",
            t.get("currency") or "",
            (t.get("purpose") or "").strip(),
            t.get("counterparty_iban") or "",
            (t.get("counterparty_name") or "").strip(),
        ]
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()
