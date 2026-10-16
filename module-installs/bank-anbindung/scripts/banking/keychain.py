"""
Banking - Credential-Speicher im macOS-Keychain.

Login + PIN liegen im System-Keychain (via `keyring`), NICHT im .env oder
in der Config-JSON. Bank-Credentials gehoeren nicht in Klartext.
Service-Name: 'ceogpt-banking', Account-Key: '{blz}:login' / '{blz}:pin'.

`keyring` wird lazy importiert, damit der Collector auch importierbar bleibt,
falls keyring (noch) nicht installiert ist.
"""
from __future__ import annotations

SERVICE = "ceogpt-banking"


def _kr():
    import keyring
    return keyring


def set_credentials(blz, login, pin):
    """Zugangsdaten ablegen. Leere Werte werden abgelehnt, nicht gespeichert.

    Warum das hier nochmal geprueft wird, obwohl das Setup schon fragt: ein
    leerer Anmeldename liess sich frueher klaglos speichern (typisch, wenn beim
    Einfuegen ein Zeilenumbruch mitkommt und die naechste Eingabeaufforderung
    ihn gleich mitverschluckt). Der Fehler fiel erst viel spaeter auf, als
    "Keine Credentials im Keychain" - eine Meldung, die in die falsche Richtung
    zeigt. Ein leerer Wert ist nie eine gueltige Eingabe, also kommt er gar
    nicht erst rein."""
    login = (login or "").strip()
    pin = pin or ""
    if not login:
        raise ValueError("Anmeldename ist leer.")
    if not pin:
        raise ValueError("PIN ist leer.")
    kr = _kr()
    kr.set_password(SERVICE, f"{blz}:login", login)
    kr.set_password(SERVICE, f"{blz}:pin", pin)


def get_login(blz):
    """Anmeldename. Ein leerer Altbestand zaehlt wie 'nicht vorhanden'.

    Wichtig fuer Setups, in denen frueher schon ein leerer Wert gespeichert
    wurde: sonst gilt der Eintrag als vorhanden und has_credentials() meldet
    faelschlich 'ok'."""
    return (_kr().get_password(SERVICE, f"{blz}:login") or "").strip() or None


def get_pin(blz):
    return _kr().get_password(SERVICE, f"{blz}:pin")


def has_credentials(blz):
    try:
        return bool(get_login(blz) and get_pin(blz))
    except Exception:
        return False


def delete(blz):
    kr = _kr()
    for key in (f"{blz}:login", f"{blz}:pin"):
        try:
            kr.delete_password(SERVICE, key)
        except Exception:
            pass
