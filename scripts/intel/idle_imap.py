"""IntelOS - IMAP-IDLE-Dauerlaeufer: neue Mails SOFORT nach data/data.db.

Haelt je Postfach (config/imap-accounts.json) und Ordner (INBOX + Gesendete) eine
eigene Verbindung im IMAP-IDLE. Meldet der Server etwas (neue Mail, Aenderung),
holt der Laeufer sofort alle neuen UIDs und speichert sie in mail_messages
(gleiches Schema und gleiche Zeilen wie scripts/intel/collect_imap.py).

Regeln (Standard module-installs/intelligenz-imap/reference/dateneingang.md):
- READ-ONLY: Ordner werden mit EXAMINE geoeffnet, Abruf mit BODY.PEEK
  (mark_seen=False). Nichts wird als gelesen markiert, verschoben oder geloescht.
- IDLE wird alle RENEW_SECONDS (30 s) beendet, der Ordner neu geoeffnet und
  abgeglichen. Grund: HostedOffice meldet neue Mails per IDLE nicht zuverlaessig
  und zeigt einer offenen Leitung einen eingefrorenen Ordnerstand. Neue UIDs werden
  per UID FETCH ermittelt (nicht SEARCH, dessen Index hinterherhinkt).
- Cursor (mail_folders.last_uid) wird erst NACH erfolgreichem Speichern
  fortgeschrieben. Doppelte Meldungen erzeugen dank UNIQUE(label, folder, uid)
  keine Dubletten. UIDVALIDITY-Wechsel -> Ordner wird ueber collect_imap neu gezogen.
- Verbindungsabbruch -> Wiederverbindung mit wachsender Wartezeit (5 s bis 5 Min.),
  danach Luecke ab dem gespeicherten Cursor nachholen.
- Status (Verbindung, letzter erfolgreicher Abgleich, Fehler) steht laufend in
  data/mail_sofort_status.json, Protokoll in data/imap_idle.log.

Die uebrigen Ordner (Archiv, Unterordner usw.) gleicht weiter die stuendliche
Aufgabe "CEO-GPT PrimaerBau Mail-Abruf" (collect_imap.py) ab.

Usage:
    python scripts/intel/idle_imap.py            # Dauerbetrieb (normal ueber die Windows-Aufgabe)
    python scripts/intel/idle_imap.py --status   # Zustand verstaendlich anzeigen
"""

import sys
import json
import time
import sqlite3
import logging
import argparse
import threading
from pathlib import Path
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler

sys.path.insert(0, str(Path(__file__).resolve().parent))
import imap_common as C  # noqa: E402
import collect_imap as CI  # noqa: E402

DATA = C.WORKSPACE / "data"
STATUS_FILE = DATA / "mail_sofort_status.json"
LOG_FILE = DATA / "imap_idle.log"
LOCK_FILE = DATA / "imap_idle.lock"
DB_FILE = DATA / "data.db"

# IDLE alle 30 s beenden, Ordner neu oeffnen und selbst nachsehen. HostedOffice meldet neue
# Mails im Posteingang per IDLE nicht zuverlaessig (getestet 14.10.2026: keine Meldung in 5 Min.),
# darum garantiert erst das Nachsehen die Ankunft binnen ~30 s. RFC 2177 verlangt < 29 Min.
RENEW_SECONDS = 30
BACKOFF_START, BACKOFF_MAX = 5, 300
SOCKET_TIMEOUT = 60
BATCH = 50
STALE_AFTER = 15 * 60           # Herzschlag aelter als das -> Laeufer gilt als gestoppt

log = logging.getLogger("idle")
_status_lock = threading.Lock()
_status: dict = {}
_stop = threading.Event()


# ---------- Status ----------

def _now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")  # Ortszeit, leichter lesbar


def set_status(key: str, **fields) -> None:
    with _status_lock:
        _status.setdefault(key, {}).update(fields)


def write_status() -> None:
    with _status_lock:
        payload = {
            "laeufer": "IMAP-IDLE (sofort)",
            "herzschlag": _now(),
            "erneuerung_sekunden": RENEW_SECONDS,
            "ordner": dict(sorted(_status.items())),
        }
    tmp = STATUS_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(STATUS_FILE)


# ---------- Datenbank ----------

def db() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_FILE), timeout=60)
    conn.execute("PRAGMA busy_timeout=60000")
    return conn


class StaleView(Exception):
    """Server kennt neue Mails (UIDNEXT), die offene Leitung kann sie aber nicht holen."""


def sync_new(conn: sqlite3.Connection, label: str, mb, name: str) -> tuple:
    """Holt alle UIDs > Cursor im (bereits per EXAMINE geoeffneten) Ordner.

    Gibt (neu gespeichert, UIDNEXT falls der Server mehr Mails kennt als geholt wurden, sonst None).
    """
    st = CI.folder_status(mb, name)
    row = conn.execute("SELECT uidvalidity, last_uid FROM mail_folders WHERE label=? AND name=?",
                       (label, name)).fetchone()
    if row is None or (st["UIDVALIDITY"] and row[0] is not None and int(row[0]) != st["UIDVALIDITY"]):
        # Neuer Ordner oder UIDVALIDITY-Reset: collect_imap regelt das (inkl. Neuaufbau).
        log.info("%s/%s: Erstabgleich bzw. UIDVALIDITY-Wechsel, Ordner wird komplett abgeglichen", label, name)
        written, _, _ = CI.backfill_folder(conn, label, mb, type("F", (), {"name": name})(), BATCH)
        mb.folder.set(name, readonly=True)
        return written, None

    last_uid = int(row[1] or 0)
    behind = st["UIDNEXT"] if st["UIDNEXT"] and st["UIDNEXT"] - 1 > last_uid else None
    now = C.now_iso()
    written, maxuid, buf = 0, last_uid, []
    new = CI.uids_after(mb, last_uid)  # ohne SEARCH, siehe dort
    if not new:
        conn.execute("UPDATE mail_folders SET msg_count=?, uidnext=?, synced_at=? WHERE label=? AND name=?",
                     (st["MESSAGES"], st["UIDNEXT"], C.now_iso(), label, name))
        conn.commit()
        return 0, behind
    for msg in mb.fetch(uid_list=new, mark_seen=False, bulk=BATCH):
        try:
            uid = int(msg.uid)
        except (TypeError, ValueError):
            continue
        if uid <= last_uid:
            continue
        buf.append(CI.msg_row(label, name, msg, now))
        maxuid = max(maxuid, uid)
        if len(buf) >= BATCH:
            written += CI._flush(conn, buf)
            buf = []
            conn.execute("UPDATE mail_folders SET last_uid=MAX(last_uid, ?) WHERE label=? AND name=?",
                         (maxuid, label, name))
            conn.commit()
    if buf:
        written += CI._flush(conn, buf)  # committet
    # Cursor erst nach dem Speichern, und nie rueckwaerts
    conn.execute("UPDATE mail_folders SET last_uid=MAX(last_uid, ?), msg_count=?, uidnext=?, synced_at=? "
                 "WHERE label=? AND name=?",
                 (maxuid, st["MESSAGES"], st["UIDNEXT"], C.now_iso(), label, name))
    conn.commit()
    behind = st["UIDNEXT"] if st["UIDNEXT"] and st["UIDNEXT"] - 1 > maxuid else None
    return written, behind


# ---------- Ein Ordner, eine Verbindung ----------

def sent_folder_name(account: dict) -> str | None:
    mb = C.connect(account)
    try:
        for f in mb.folder.list():
            if C.special_use_of(getattr(f, "flags", ())) == "\\Sent":
                return f.name
    finally:
        try:
            mb.logout()
        except Exception:
            pass
    return None


def connect(account: dict):
    mt = C.imp("imap_tools")
    mb = mt.MailBox(account["imap_host"], int(account.get("imap_port", 993)), timeout=SOCKET_TIMEOUT)
    return mb.login(account.get("username") or account["label"], account["password"])


def watch(account: dict, folder: str) -> None:
    label = account["label"]
    key = f"{label}/{folder}"
    conn = db()
    backoff = BACKOFF_START
    known_gap = None  # UIDNEXT, bei dem auch eine frische Anmeldung nichts fand (z. B. sofort geloeschte Mail)
    set_status(key, zustand="startet", fehler=None)
    while not _stop.is_set():
        mb = None
        try:
            mb = connect(account)
            mb.folder.set(folder, readonly=True)  # EXAMINE: nichts wird veraendert
            n, behind = sync_new(conn, label, mb, folder)  # Luecke seit letztem Cursor nachholen
            known_gap = behind
            log.info("%s: verbunden, nachgeholt +%d", key, n)
            set_status(key, zustand="verbunden", seit=_now(), letzter_abgleich=_now(), fehler=None)
            if n:
                set_status(key, letzte_neue=_now())
            backoff = BACKOFF_START
            while not _stop.is_set():
                mb.idle.start()
                started = time.monotonic()
                resp = mb.idle.poll(timeout=RENEW_SECONDS)
                mb.idle.stop()  # wirft bei toter Verbindung -> Wiederverbindung
                if not resp and time.monotonic() - started < 1:
                    raise ConnectionError("Verbindung vom Server geschlossen")
                if resp:
                    log.info("%s: Meldung vom Server %s", key, b" | ".join(resp)[:200])
                # HostedOffice/Exchange friert den Ordnerstand einer offenen Leitung ein (getestet
                # 14.10.2026): Nach dem Neuoeffnen meldet STATUS die neue UIDNEXT, holen laesst sich
                # die Mail aber erst nach frischer Anmeldung. Darum: Ordner neu oeffnen, abgleichen,
                # und wenn der Server mehr kennt als geholt wurde, sofort neu anmelden.
                mb.folder.set(folder, readonly=True)
                n, behind = sync_new(conn, label, mb, folder)
                if behind and behind != known_gap:
                    raise StaleView(f"Server kennt UIDNEXT {behind}, Leitung sieht die Mail nicht")
                fields = {"letzter_abgleich": _now(), "zustand": "verbunden"}
                if n:
                    fields["letzte_neue"] = _now()
                    log.info("%s: +%d neue Mail(s) gespeichert", key, n)
                set_status(key, **fields)
        except StaleView as e:
            log.info("%s: %s, melde neu an", key, e)
        except Exception as e:
            log.warning("%s: Verbindung unterbrochen (%r), neuer Versuch in %d s", key, e, backoff)
            set_status(key, zustand="getrennt, verbindet neu", fehler=f"{type(e).__name__}: {e}"[:300],
                       fehler_zeit=_now())
            _stop.wait(backoff)
            backoff = min(backoff * 2, BACKOFF_MAX)
        finally:
            if mb is not None:
                try:
                    mb.logout()
                except Exception:
                    pass
    conn.close()


# ---------- Start ----------

class _LogWriter:
    """Leitet print() aus collect_imap ins Protokoll (pythonw hat keine Konsole)."""
    def write(self, s):
        for line in s.splitlines():
            if line.strip():
                log.info(line.rstrip())

    def flush(self):
        pass


def single_instance():
    import msvcrt
    LOCK_FILE.parent.mkdir(parents=True, exist_ok=True)
    fh = open(LOCK_FILE, "a+")
    try:
        msvcrt.locking(fh.fileno(), msvcrt.LK_NBLCK, 1)
    except OSError:
        return None
    return fh


def show_status() -> int:
    if not STATUS_FILE.exists():
        print("Der Sofort-Abruf ist noch nie gelaufen.")
        return 1
    s = json.loads(STATUS_FILE.read_text(encoding="utf-8"))
    beat = datetime.fromisoformat(s["herzschlag"])
    age = (datetime.now(timezone.utc) - beat).total_seconds()
    running = age < STALE_AFTER
    print(f"Sofort-Abruf: {'LAEUFT' if running else 'GESTOPPT'} (letztes Lebenszeichen vor {int(age)} s)")
    for key, f in s["ordner"].items():
        print(f"  {key:<35} {f.get('zustand', '?'):<26} letzter Abgleich: {f.get('letzter_abgleich', '-')}"
              + (f"  Fehler: {f['fehler']}" if f.get("fehler") else ""))
    return 0 if running else 1


def main() -> int:
    ap = argparse.ArgumentParser(description="IMAP-IDLE-Dauerlaeufer (neue Mails sofort in data.db)")
    ap.add_argument("--status", action="store_true", help="Zustand anzeigen und beenden")
    args = ap.parse_args()
    if args.status:
        return show_status()

    DATA.mkdir(exist_ok=True)
    handler = RotatingFileHandler(LOG_FILE, maxBytes=2_000_000, backupCount=1, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s", "%Y-%m-%d %H:%M:%S"))
    logging.basicConfig(level=logging.INFO, handlers=[handler])
    sys.stdout = sys.stderr = _LogWriter()

    lock = single_instance()
    if lock is None:
        log.info("Laeuft bereits, zweiter Start beendet.")
        return 0

    conn = db()
    C.ensure_tables(conn)
    accounts = C.load_accounts()
    for a in accounts:
        C.upsert_account(conn, a)
    conn.close()

    threads = []
    for a in accounts:
        folders = ["INBOX"]
        for attempt in range(5):
            try:
                sent = sent_folder_name(a)
                break
            except Exception as e:
                log.warning("%s: Ordnerliste nicht abrufbar (%r), Versuch %d", a["label"], e, attempt + 1)
                time.sleep(BACKOFF_START * (2 ** attempt))
        else:
            sent = "Gesendete Elemente"
        if sent:
            folders.append(sent)
        for f in folders:
            t = threading.Thread(target=watch, args=(a, f), name=f"{a['label']}/{f}", daemon=True)
            t.start()
            threads.append(t)
    log.info("Gestartet: %s", ", ".join(t.name for t in threads))

    try:
        while True:
            write_status()
            time.sleep(15)
    except KeyboardInterrupt:
        _stop.set()
        write_status()
    return 0


if __name__ == "__main__":
    sys.exit(main())
