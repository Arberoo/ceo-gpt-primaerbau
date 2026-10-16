"""
Daten: Sammel-Orchestrator

Findet und startet alle aktiven Sammler (collect_*.py im scripts-Ordner).
Nach der Sammlung wird die key-metrics.md neu erzeugt, damit /prime immer
frische Zahlen lädt.

Robustheit: bei DNS-Resolver-Aussetzern (Mac-Sleep/Wake-Bug, stale Cache)
oder Read-Timeouts wird einmal nach 30 Sekunden retried, statt den Job
ganz fallen zu lassen.

Nutzung:
    python scripts/collect.py                          # Alle Sammler
    python scripts/collect.py --sources youtube,stripe  # Nur bestimmte
    python scripts/collect.py --date 2026-02-20         # Datum überschreiben
"""

import sys
import os
import time
import argparse
import importlib.util
from datetime import datetime, timezone
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent

RETRY_DELAY_SECONDS = 30


def discover_collectors():
    """Alle collect_*.py Dateien im scripts-Ordner finden."""
    collectors = {}
    for filepath in sorted(SCRIPT_DIR.glob("collect_*.py")):
        # Den Orchestrator selber überspringen
        if filepath.name == "collect.py":
            continue
        # Name extrahieren: collect_youtube.py -> youtube
        name = filepath.stem.replace("collect_", "")
        collectors[name] = filepath
    return collectors


def import_collector(name, filepath):
    """Sammler-Modul dynamisch laden."""
    spec = importlib.util.spec_from_file_location(f"collect_{name}", str(filepath))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def is_transient_network_error(reason):
    """Typische Mac-Sleep/Wake-Symptome erkennen (Stale DNS-Cache, TCP-Stack
    noch nicht wieder warm). Wenn so was zuschlägt, hilft 30s warten und
    nochmal probieren, statt den ganzen Tageslauf zu kippen."""
    if not reason:
        return False
    needles = (
        # DNS
        "NameResolutionError",
        "nodename nor servname provided",
        "Name or service not known",
        "Temporary failure in name resolution",
        "Failed to resolve",
        # Timeouts und Connect-Aussetzer
        "Read timed out",
        "Connection timed out",
        "Connection refused",
        "Connection reset",
        "Connection aborted",
    )
    return any(n in reason for n in needles)


def run_one(name, filepath, conn, today):
    """Einen Sammler ausführen. Gibt (status, records, reason) zurück.
    Keine Prints, kein Logging, damit Retry sauber bleibt.
    """
    try:
        mod = import_collector(name, filepath)
        result = mod.collect()
        status = result.get("status", "unknown")
        if status == "success":
            records = mod.write(conn, result, today)
            return ("success", records, "")
        if status == "skipped":
            return ("skipped", 0, result.get("reason", ""))
        return ("error", 0, result.get("reason", ""))
    except Exception as e:
        return ("exception", 0, str(e))


def main():
    parser = argparse.ArgumentParser(description="Daten aus allen Quellen sammeln")
    parser.add_argument(
        "--sources", type=str, default=None,
        help="Komma-Liste der Quellen (Standard: alle)"
    )
    parser.add_argument(
        "--date", type=str, default=None,
        help="Sammel-Datum überschreiben (YYYY-MM-DD, Standard: heute)"
    )
    args = parser.parse_args()

    today = args.date or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    # Verfügbare Sammler finden
    available = discover_collectors()
    if not available:
        print(f"[{timestamp}] Keine Sammler gefunden. Leg collect_*.py Dateien in scripts/ an.",
              file=sys.stderr)
        sys.exit(1)

    # Bestimmen, welche laufen sollen
    if args.sources:
        names = [s.strip() for s in args.sources.split(",")]
        unknown = [s for s in names if s not in available]
        if unknown:
            print(f"[{timestamp}] Unbekannte Quellen ignoriert: {', '.join(unknown)}",
                  file=sys.stderr)
        names = [s for s in names if s in available]
    else:
        names = list(available.keys())

    # Datenbank initialisieren
    sys.path.insert(0, str(SCRIPT_DIR))
    from db import init_db, log_collection

    conn = init_db()
    print(f"[{timestamp}] Sammlung gestartet, {len(names)} Quellen für Datum={today}",
          file=sys.stderr)

    results = []
    retry_queue = []  # Sammler mit transientem Netz-Fehler, kriegen einen zweiten Versuch

    # Erste Runde
    for name in names:
        filepath = available[name]
        print(f"  Sammle {name}...", file=sys.stderr, end="")

        status, records, reason = run_one(name, filepath, conn, today)

        if status == "success":
            log_collection(conn, name, "success", records)
            print(f" OK ({records} Datensätze)", file=sys.stderr)
            results.append((name, "success", records))
        elif status == "skipped":
            log_collection(conn, name, "skipped", reason=reason)
            print(f" ÜBERSPRUNGEN ({reason})", file=sys.stderr)
            results.append((name, "skipped", 0))
        elif is_transient_network_error(reason):
            print(" Netz-Aussetzer, Retry in der zweiten Runde", file=sys.stderr)
            retry_queue.append((name, filepath))
        else:
            log_collection(conn, name, status, reason=reason)
            label = "FEHLER" if status == "error" else "EXCEPTION"
            print(f" {label} ({reason})", file=sys.stderr)
            results.append((name, status, 0))

    # Retry-Runde nur, wenn transiente Aussetzer aufgetreten sind. Mac-Sleep-Wake-Bug
    # erholt sich typischerweise innerhalb von Sekunden, sobald der Resolver
    # neu auflöst.
    if retry_queue:
        print(
            f"[{timestamp}] {len(retry_queue)} Sammler hatten Netz-Aussetzer, "
            f"warte {RETRY_DELAY_SECONDS}s und probier nochmal...",
            file=sys.stderr,
        )
        time.sleep(RETRY_DELAY_SECONDS)
        retry_timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        print(f"[{retry_timestamp}] Retry-Runde startet", file=sys.stderr)

        for name, filepath in retry_queue:
            print(f"  Retry {name}...", file=sys.stderr, end="")
            status, records, reason = run_one(name, filepath, conn, today)
            if status == "success":
                log_collection(conn, name, "success", records)
                print(f" OK ({records} Datensätze)", file=sys.stderr)
                results.append((name, "success", records))
            elif status == "skipped":
                log_collection(conn, name, "skipped", reason=reason)
                print(f" ÜBERSPRUNGEN ({reason})", file=sys.stderr)
                results.append((name, "skipped", 0))
            else:
                log_collection(conn, name, status, reason=reason)
                label = "FEHLER nach Retry" if status == "error" else "EXCEPTION nach Retry"
                print(f" {label} ({reason})", file=sys.stderr)
                results.append((name, status, 0))

    conn.close()

    # Zusammenfassung
    successes = sum(1 for _, s, _ in results if s == "success")
    total_records = sum(r for _, _, r in results)
    skipped = sum(1 for _, s, _ in results if s == "skipped")
    errors = sum(1 for _, s, _ in results if s in ("error", "exception"))

    summary = (f"[{timestamp}] Fertig: {successes} erfolgreich, "
               f"{skipped} übersprungen, {errors} Fehler, {total_records} Datensätze gesamt")
    print(summary, file=sys.stderr)
    print(summary)

    # Nach der Sammlung: Kennzahlen neu erzeugen
    if successes > 0:
        try:
            from generate_metrics import main as regen
            regen()
            print(f"[{timestamp}] Kennzahlen neu erzeugt", file=sys.stderr)
        except Exception as e:
            print(f"[{timestamp}] Warnung: Kennzahlen-Regeneration fehlgeschlagen: {e}", file=sys.stderr)

    sys.exit(0 if successes > 0 else 1)


if __name__ == "__main__":
    main()
