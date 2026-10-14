#!/usr/bin/env python3
"""Geheimnis verdeckt eingeben und in die .env schreiben, ohne die Datei zu öffnen.

Gedacht für den Fulfillment-Call: Statt die .env aufzumachen und ein Passwort
sichtbar reinzutippen, fragt dieses Skript verdeckt ab (wie `sudo`, es erscheint
kein Zeichen). Der Wert landet von selbst in der .env. Niemand sieht ihn, auch der
nicht, der gerade auf den Bildschirm schaut. Im Call kann der Kunde selbst tippen.

Aufruf:
    python scripts/set_secret.py                 # fragt erst nach dem Schlüssel, dann verdeckt nach dem Wert
    python scripts/set_secret.py IMAP_PW_INFO    # Schlüssel vorgegeben, nur noch verdeckt tippen
    python scripts/set_secret.py IMAP_PW_INFO --show   # ausnahmsweise sichtbar tippen (z.B. langer API-Key)

Verhalten:
    - Verdeckte Eingabe per getpass (Standard). Der Wert wird nie angezeigt.
    - Schreibt KEY=WERT in die .env im Projekt-Wurzelverzeichnis.
      Gibt es den Schlüssel schon, wird seine Zeile ersetzt, sonst angehängt.
    - Bestätigt nur "gesetzt", nie den Wert selbst.
"""

import sys
import getpass
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
ENV_PATH = REPO / ".env"


def gueltiger_schluessel(name: str) -> bool:
    """Schlüssel muss aussehen wie eine .env-Variable: Buchstaben, Ziffern, Unterstrich."""
    return bool(name) and name.replace("_", "").isalnum() and not name[0].isdigit()


def setze_schluessel(env_text: str, key: str, value: str) -> str:
    """Ersetzt die Zeile KEY=... oder hängt sie an. Lässt alles andere unangetastet.
    Räumt dabei DUBLETTEN auf: gibt es den Schlüssel mehrfach, bleibt genau eine Zeile
    mit dem neuen Wert übrig (sonst gewinnt beim Laden die letzte alte Dublette)."""
    zeilen = env_text.splitlines()
    neue_zeile = f"{key}={value}"
    out = []
    gefunden = False
    for zeile in zeilen:
        ist_treffer = (not zeile.lstrip().startswith("#")
                       and "=" in zeile and zeile.split("=", 1)[0].strip() == key)
        if ist_treffer:
            if not gefunden:
                out.append(neue_zeile)   # erste Fundstelle ersetzen
                gefunden = True
            # weitere Dubletten still weglassen
            continue
        out.append(zeile)
    if not gefunden:
        out.append(neue_zeile)
    return "\n".join(out) + "\n"


def main() -> int:
    args = [a for a in sys.argv[1:]]
    sichtbar = "--show" in args
    args = [a for a in args if a != "--show"]

    key = args[0] if args else input("Welcher Schlüssel? (z.B. IMAP_PW_INFO): ").strip()

    if not gueltiger_schluessel(key):
        print(f"✗ '{key}' ist kein gültiger Schlüsselname. Erlaubt: Buchstaben, Ziffern, Unterstrich (nicht mit Ziffer beginnend).")
        return 1

    print(f"\nGib jetzt den Wert für {key} ein.")
    if sichtbar:
        print("(sichtbar)")
        value = input(f"{key} = ").strip()
    else:
        print("(verdeckt, wie bei sudo, es erscheint nichts beim Tippen)")
        # Bis zu drei Anläufe: jeder Wert wird zweimal getippt und muss übereinstimmen.
        # So fängt ein Vertipper niemanden ab, man darf einfach nochmal.
        value = None
        max_versuche = 3
        for versuch in range(1, max_versuche + 1):
            erste = getpass.getpass(f"{key} = ").strip()
            kontrolle = getpass.getpass(f"{key} nochmal zur Kontrolle = ").strip()
            if erste and erste == kontrolle:
                value = erste
                break
            grund = "Leer." if not erste else "Die beiden Eingaben sind nicht gleich."
            if versuch < max_versuche:
                print(f"✗ {grund} Versuch {versuch} von {max_versuche}, bitte nochmal.\n")
            else:
                print(f"✗ {grund} Auch nach {max_versuche} Versuchen nichts Passendes. Nichts gespeichert.")
                return 1

    if not value:
        print("✗ Leer. Nichts gespeichert.")
        return 1
    if "\n" in value or "\r" in value:
        print("✗ Der Wert enthält einen Zeilenumbruch. Nichts gespeichert.")
        return 1

    alt = ENV_PATH.read_text() if ENV_PATH.exists() else ""
    neu = setze_schluessel(alt, key, value)
    ENV_PATH.write_text(neu)
    # Datei privat halten (nur der Besitzer darf lesen/schreiben).
    try:
        ENV_PATH.chmod(0o600)
    except OSError:
        pass

    print(f"\n✓ {key} gesetzt ({len(value)} Zeichen, verdeckt). In {ENV_PATH} gespeichert.")
    print("  Der Wert wurde nirgends angezeigt.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
