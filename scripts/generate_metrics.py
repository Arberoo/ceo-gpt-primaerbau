"""
Daten: Kennzahlen-Generator

Liest die Datenbank und erzeugt eine lesbare key-metrics.md.
Diese Datei wird vom /prime-Befehl geladen, damit dein Mitarbeiter
immer frische Zahlen sieht.

Findet automatisch, welche Tabellen es gibt, und erzeugt pro Tabelle
eine Sektion. Dein Mitarbeiter passt die Datei während der Installation
an deine echten Quellen an.

Nutzung:
    python scripts/generate_metrics.py
"""

import sqlite3
from datetime import datetime
from pathlib import Path

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = WORKSPACE_ROOT / "data" / "data.db"
# PrimaerBau-Anpassung (16.10.2026): Kontostaende und Umsaetze sind vertraulich.
# context/ wandert nachts ins GitHub-Repo, data/ nicht. Deshalb liegt die
# Kennzahlen-Datei lokal unter data/kennzahlen/ statt context/group/.
OUTPUT_PATH = WORKSPACE_ROOT / "data" / "kennzahlen" / "key-metrics.md"


# --- Formatierungs-Helfer ---

def fmt_number(value, prefix="", suffix=""):
    """Zahl mit Tausender-Trennzeichen. Gibt 'Keine Daten' bei None zurück."""
    if value is None:
        return "Keine Daten"
    if isinstance(value, float):
        return f"{prefix}{value:,.0f}{suffix}"
    return f"{prefix}{value:,}{suffix}"


def fmt_currency(value, symbol="€"):
    """Währungsbetrag mit Symbol und Tausender-Trennzeichen."""
    if value is None:
        return "Keine Daten"
    return f"{symbol}{value:,.0f}"


def fmt_pct(value):
    """Prozentwert auf 1 Nachkommastelle."""
    if value is None:
        return "Keine Daten"
    return f"{value:.1f}%"


def query_one(conn, sql):
    """Abfrage-Helfer, gibt erste Zeile als dict oder None zurück."""
    try:
        row = conn.execute(sql).fetchone()
        return dict(row) if row else None
    except Exception:
        return None


def query_all(conn, sql):
    """Abfrage-Helfer, gibt alle Zeilen als Liste von dicts zurück."""
    try:
        return [dict(r) for r in conn.execute(sql).fetchall()]
    except Exception:
        return []


def table_exists(conn, name):
    """Prüfen, ob eine Tabelle existiert."""
    r = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (name,)
    ).fetchone()
    return r is not None


# ============================================================
# SEKTIONS-GENERATOREN
# Jede Funktion gibt eine Liste von Markdown-Zeilen zurück.
# Während der Installation legt dein Mitarbeiter hier eigene
# Sektions-Funktionen für deine angebundenen Quellen an.
# ============================================================


def section_fx_rates(conn):
    """Wechselkurse, der Starter-Sammler (immer verfügbar)."""
    if not table_exists(conn, "fx_rates"):
        return []
    lines = []
    lines.append("## Wechselkurse")
    lines.append("| Währung | Kurs (von USD) | Stand |")
    lines.append("|---------|----------------|-------|")
    rows = query_all(conn, """
        SELECT date, currency, rate FROM fx_rates
        WHERE date = (SELECT MAX(date) FROM fx_rates)
        ORDER BY currency
    """)
    for r in rows:
        lines.append(f"| {r['currency']} | {r['rate']:.4f} | {r['date']} |")
    lines.append("")
    return lines


# --- ANPASSUNGS-ZONE ---

def eur(betrag):
    """Deutsches Format: 12.345,67 €"""
    if betrag is None:
        return "Keine Daten"
    return f"{betrag:,.2f} €".replace(",", "X").replace(".", ",").replace("X", ".")


def section_banking(conn):
    """Liquiditaet aus der Bankanbindung (module-installs/bank-anbindung).

    Nur gebuchte Umsaetze (status = 'BOOK') zaehlen, vorgemerkte nie."""
    if not table_exists(conn, "banking_balances"):
        return []
    lines = ["## Bank (Liquiditaet)", ""]

    salden = query_all(conn, """
        SELECT a.bank_label, COALESCE(a.konto_name, '') AS konto,
               COALESCE(a.iban_klar, a.iban) AS iban, b.balance, b.currency, b.date
        FROM banking_balances b
        JOIN banking_accounts a ON a.iban = b.iban
        WHERE b.date = (SELECT MAX(date) FROM banking_balances b2 WHERE b2.iban = b.iban)
        ORDER BY a.bank_label, iban
    """)
    if salden:
        lines += ["| Konto | Saldo | Stand |", "|---|---|---|"]
        for r in salden:
            name = " ".join(x for x in (r["bank_label"], r["konto"]) if x)
            kurz = r["iban"].replace(" ", "")[-10:]
            lines.append(f"| {name} …{kurz[:4]} {kurz[4:8]} {kurz[8:]} | {eur(r['balance'])} | {r['date']} |")
        summe = sum(r["balance"] or 0 for r in salden if (r["currency"] or "EUR") == "EUR")
        lines += [f"| **Gesamt** | **{eur(summe)}** | |", ""]

    fluss = query_one(conn, """
        SELECT SUM(CASE WHEN amount > 0 THEN amount ELSE 0 END) AS ein,
               SUM(CASE WHEN amount < 0 THEN amount ELSE 0 END) AS aus
        FROM banking_transactions
        WHERE status = 'BOOK' AND booking_date >= date('now', '-30 days')  -- ohne Umbuchungen zwischen eigenen Konten
        AND COALESCE(REPLACE(counterparty_iban, ' ', ''), '') NOT IN
            (SELECT REPLACE(COALESCE(iban_klar, iban), ' ', '') FROM banking_accounts)
    """)
    if fluss and (fluss["ein"] or fluss["aus"]):
        lines += ["**Letzte 30 Tage (gebucht):**",
                  f"- Eingang: {eur(fluss['ein'] or 0)}",
                  f"- Ausgang: {eur(fluss['aus'] or 0)}", ""]

    top = query_all(conn, """
        SELECT COALESCE(NULLIF(counterparty_name, ''), '(ohne Namen)') AS name,
               SUM(amount) AS summe, COUNT(*) AS anzahl
        FROM banking_transactions
        WHERE status = 'BOOK' AND amount < 0 AND booking_date >= date('now', '-30 days')  -- ohne Umbuchungen zwischen eigenen Konten
        AND COALESCE(REPLACE(counterparty_iban, ' ', ''), '') NOT IN
            (SELECT REPLACE(COALESCE(iban_klar, iban), ' ', '') FROM banking_accounts)
        GROUP BY name ORDER BY summe ASC LIMIT 5
    """)
    if top:
        lines += ["**Groesste Empfaenger (30 Tage):**", "| Empfaenger | Summe | Buchungen |", "|---|---|---|"]
        for r in top:
            lines.append(f"| {r['name']} | {eur(r['summe'])} | {r['anzahl']} |")
        lines.append("")

    if table_exists(conn, "banking_sync_state"):
        for r in query_all(conn, "SELECT blz, needs_tan, message, rest_tage FROM banking_sync_state"):
            if r["needs_tan"]:
                lines.append(f"> ⚠ Bank {r['blz']}: Bestaetigung noetig ({r['message']}). "
                             f"`python scripts/banking/setup.py reauth {r['blz']}`")
            elif r["rest_tage"] is not None and r["rest_tage"] <= 14:
                lines.append(f"> Hinweis: Freigabe Bank {r['blz']} laeuft in {r['rest_tage']} Tagen ab.")
        lines.append("")
    return lines


# Hier trägt dein Mitarbeiter während der Installation eigene
# Sektions-Funktionen ein. Pattern:
#
#   def section_NAME(conn):
#       if not table_exists(conn, "TABELLEN_NAME"):
#           return []
#       lines = ["## Sektions-Titel", "| Kennzahl | Wert | Stand |", ...]
#       row = query_one(conn, "SELECT ... FROM TABELLEN_NAME ORDER BY date DESC LIMIT 1")
#       if row:
#           lines.append(f"| Kennzahl | {fmt_number(row['value'])} | {row['date']} |")
#       return lines


# ============================================================
# HAUPT-GENERATOR
# ============================================================

# Alle Sektions-Funktionen hier registrieren. Während der Installation
# kommen weitere dazu.
SECTIONS = [
    section_fx_rates,
    section_banking,
    # section_youtube,
    # section_stripe,
    # section_google_analytics,
    # section_marketing,
]


def generate(conn):
    """Erzeugt den Markdown-Inhalt der Kennzahlen-Datei."""
    today = datetime.now().strftime("%Y-%m-%d")
    lines = [
        "# Kennzahlen",
        "",
        f"> Automatisch aus der Datenbank erzeugt. Letztes Update: {today}",
        f"> Quelle: `data/data.db` | Neu erzeugen: `python scripts/generate_metrics.py`",
        "",
    ]

    # Alle registrierten Sektions-Generatoren laufen
    for section_fn in SECTIONS:
        try:
            section_lines = section_fn(conn)
            if section_lines:
                lines.extend(section_lines)
        except Exception as e:
            lines.append(f"<!-- Fehler in {section_fn.__name__}: {e} -->")
            lines.append("")

    # Frische-Tabelle (findet alle Tabellen automatisch)
    lines.append("## Datenfrische")
    lines.append("| Quelle | Letzter Datensatz | Status |")
    lines.append("|--------|-------------------|--------|")

    tables = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' "
        "AND name != 'collection_log' AND name NOT LIKE 'sqlite_%' "
        # PrimaerBau: die Mail-Tabellen gehoeren dem Mail-Abruf, nicht DataOS
        "AND name NOT LIKE 'mail_%' "
        "ORDER BY name"
    ).fetchall()

    for t in tables:
        name = t["name"]
        try:
            spalte = {"banking_transactions": "booking_date", "banking_accounts": "last_synced",
                      "banking_sync_state": "last_success"}.get(name, "date")
            row = conn.execute(f"SELECT MAX({spalte}) as d FROM {name}").fetchone()
            if row and row["d"]:
                lines.append(f"| {name} | {row['d']} | verbunden |")
            else:
                lines.append(f"| {name} |: | leer |")
        except Exception:
            lines.append(f"| {name} |: | keine Datums-Spalte |")

    lines.append("")
    return "\n".join(lines)


def main():
    """Erzeugt key-metrics.md aus der Datenbank."""
    if not DB_PATH.exists():
        print(f"Datenbank nicht gefunden unter {DB_PATH}")
        print("Erst sammeln: python scripts/collect.py")
        return

    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row

    content = generate(conn)
    conn.close()

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(content, encoding="utf-8")
    print(f"Kennzahlen geschrieben nach: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
