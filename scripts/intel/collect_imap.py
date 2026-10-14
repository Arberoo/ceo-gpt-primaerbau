"""IntelOS - IMAP Collector. STUFE 2: alles rueckwirkend lokal extrahieren.

Zieht ALLE Mails ALLER Ordner jedes Kontos (config/imap-accounts.json) nach
data/data.db (Tabelle mail_messages). READ-ONLY, markiert nichts als gelesen
(BODY.PEEK via mark_seen=False). Idempotent + wiederaufnehmbar ueber (label,
folder, UID) plus UIDVALIDITY pro Ordner. Vollstaendigkeits-Check am Ende
(Exit 0 = alles lokal, 2 = noch Luecken, einfach erneut laufen lassen).

UIDVALIDITY-Reset wird erkannt: aendert der Server den Wert eines Ordners,
sind alle alten UIDs ungueltig, der Ordner wird dann lokal verworfen und neu
gezogen.

Gmail-Konten (provider="gmail"): nur All Mail + Spam + Trash, um die
Label-als-Ordner-Dubletten zu vermeiden.

Usage:
    python scripts/intel/collect_imap.py                 # alle Konten, alle Ordner
    python scripts/intel/collect_imap.py --account info
    python scripts/intel/collect_imap.py --folder INBOX
    python scripts/intel/collect_imap.py --batch 100
"""

import re
import sys
import argparse
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).resolve().parent))
import imap_common as C  # noqa: E402

STATUS_OPTS = ("MESSAGES", "UIDVALIDITY", "UIDNEXT")


def _quote(name: str) -> str:
    return '"%s"' % name.replace('"', '\\"')


def folder_status(mb, name: str) -> dict:
    try:
        st = mb.folder.status(name, STATUS_OPTS)
        return {k: int(st.get(k, 0) or 0) for k in STATUS_OPTS}
    except Exception:
        pass
    try:
        typ, data = mb.client.status(_quote(name), "(%s)" % " ".join(STATUS_OPTS))
        if typ == "OK" and data and data[0]:
            s = data[0].decode(errors="ignore")
            return {k: (int(re.search(k + r"\s+(\d+)", s).group(1)) if re.search(k + r"\s+(\d+)", s) else 0) for k in STATUS_OPTS}
    except Exception:
        pass
    return {k: 0 for k in STATUS_OPTS}


def uids_after(mb, last_uid: int) -> list:
    """UIDs > last_uid im geoeffneten Ordner, per UID FETCH statt SEARCH.

    HostedOffice/Exchange beantwortet SEARCH aus einem Suchindex, der neue Mails erst
    verzoegert kennt (getestet 14.10.2026). Mit SEARCH koennte eine Mail hinter dem
    Cursor verschwinden. UID FETCH sieht jede Mail sofort.
    """
    typ, data = mb.client.uid("FETCH", f"{last_uid + 1}:*", "(UID)")
    uids = set()
    for item in data or []:
        raw = item[0] if isinstance(item, tuple) else item
        m = re.search(rb"UID (\d+)", raw or b"")
        if m and int(m.group(1)) > last_uid:
            uids.add(int(m.group(1)))
    return [str(u) for u in sorted(uids)]


def _received(msg) -> str:
    d = getattr(msg, "date", None)
    if d is not None:
        try:
            if d.tzinfo is None:
                return d.strftime("%Y-%m-%dT%H:%M:%SZ")
            return d.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        except Exception:
            pass
    return (getattr(msg, "date_str", "") or "")


def _addr_list(values, fallback) -> str:
    try:
        if values:
            return ", ".join(getattr(v, "email", "") for v in values if getattr(v, "email", ""))
    except Exception:
        pass
    try:
        return ", ".join(fallback or ())
    except Exception:
        return ""


def msg_row(label: str, folder: str, msg, now: str):
    fromv = getattr(msg, "from_values", None)
    from_name = getattr(fromv, "name", "") if fromv else ""
    from_email = getattr(fromv, "email", "") if fromv else (getattr(msg, "from_", "") or "")
    to_rec = _addr_list(getattr(msg, "to_values", None), getattr(msg, "to", ()))
    cc_rec = _addr_list(getattr(msg, "cc_values", None), getattr(msg, "cc", ()))
    text = (getattr(msg, "text", "") or getattr(msg, "html", "") or "")
    preview = re.sub(r"\s+", " ", text).strip()[:300]
    msgid = ""
    try:
        msgid = (msg.obj.get("Message-ID") or msg.obj.get("Message-Id") or "").strip()
    except Exception:
        msgid = ""
    flags = ",".join(str(x) for x in (getattr(msg, "flags", ()) or ()))
    size = int(getattr(msg, "size", 0) or 0)
    has_attach = 1 if getattr(msg, "attachments", None) else 0
    return (label, folder, int(msg.uid), msgid, None, None, from_name, from_email,
            to_rec, cc_rec, getattr(msg, "subject", "") or "", preview,
            _received(msg), flags, size, has_attach, now)


def _flush(conn, rows) -> int:
    written = 0
    for r in rows:
        cur = conn.execute(
            "INSERT OR IGNORE INTO mail_messages "
            "(label, folder, uid, message_id, gm_msgid, gm_labels, from_name, from_email, "
            "to_recipients, cc_recipients, subject, body_preview, received_at, flags, size_bytes, has_attach, collected_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", r)
        written += cur.rowcount
    conn.commit()
    return written


def folders_to_sync(mb, account: dict, only_folder: str | None):
    folders = list(mb.folder.list())
    if only_folder:
        return [f for f in folders if getattr(f, "name", "") == only_folder]
    if account.get("provider") == "gmail":
        keep = []
        for f in folders:
            role = C.special_use_of(getattr(f, "flags", ()))
            nm = getattr(f, "name", "")
            if role in ("\\All", "\\Junk", "\\Trash") or "All Mail" in nm or nm.endswith("Spam") or nm.endswith("Trash"):
                keep.append(f)
        return keep or folders
    return folders


def backfill_folder(conn, label: str, mb, folder, batch: int) -> tuple:
    name = getattr(folder, "name", str(folder))
    st = folder_status(mb, name)
    cur_uidval, total = st["UIDVALIDITY"], st["MESSAGES"]

    row = conn.execute("SELECT uidvalidity, last_uid FROM mail_folders WHERE label=? AND name=?", (label, name)).fetchone()
    stored_uidval, last_uid = (row[0], row[1] or 0) if row else (None, 0)

    if stored_uidval is not None and cur_uidval and int(stored_uidval) != int(cur_uidval):
        conn.execute("DELETE FROM mail_messages WHERE label=? AND folder=?", (label, name))
        last_uid = 0
        print(f"    {name}: UIDVALIDITY-Reset, Ordner wird neu gezogen.")

    conn.execute(
        "INSERT INTO mail_folders (label, name, uidvalidity, last_uid, uidnext, msg_count, synced_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?) "
        "ON CONFLICT(label, name) DO UPDATE SET uidvalidity=excluded.uidvalidity, "
        "uidnext=excluded.uidnext, msg_count=excluded.msg_count, synced_at=excluded.synced_at",
        (label, name, cur_uidval, last_uid, st["UIDNEXT"], total, C.now_iso()))
    conn.commit()

    if total == 0:
        return 0, 0, 0

    try:
        mb.folder.set(name, readonly=True)
    except Exception as e:
        print(f"    {name}: kann nicht geoeffnet werden ({e!r}), uebersprungen.")
        return 0, 0, total

    now = C.now_iso()
    written, seen, maxuid, buf = 0, 0, last_uid, []
    try:
        new = uids_after(mb, last_uid)
        for msg in (mb.fetch(uid_list=new, mark_seen=False, bulk=batch) if new else ()):
            try:
                uid = int(msg.uid)
            except (TypeError, ValueError):
                continue
            if uid <= last_uid:
                continue
            seen += 1
            buf.append(msg_row(label, name, msg, now))
            if uid > maxuid:
                maxuid = uid
            if len(buf) >= batch:
                written += _flush(conn, buf)
                buf = []
                conn.execute("UPDATE mail_folders SET last_uid=? WHERE label=? AND name=?", (maxuid, label, name))
                conn.commit()
    except Exception as e:
        print(f"    {name}: Abbruch beim Laden ({e!r}), bereits Geladenes ist gespeichert.")
    if buf:
        written += _flush(conn, buf)
    conn.execute("UPDATE mail_folders SET last_uid=? WHERE label=? AND name=?", (maxuid, label, name))
    conn.commit()

    stored = conn.execute("SELECT COUNT(*) FROM mail_messages WHERE label=? AND folder=?", (label, name)).fetchone()[0]
    print(f"    {name:<32} {stored:>7}/{total:<7} lokal (+{written} neu)")
    return written, stored, total


def collect_account(conn, account: dict, only_folder: str | None, batch: int) -> tuple:
    label = account.get("label", "?")
    print(f"\n=== {label} ({account.get('imap_host')}) ===")
    C.upsert_account(conn, account)
    mb = C.connect(account)
    acct_written = acct_stored = acct_total = 0
    try:
        folders = folders_to_sync(mb, account, only_folder)
        print(f"  {len(folders)} Ordner zu synchronisieren")
        for f in folders:
            try:
                w, s, t = backfill_folder(conn, label, mb, f, batch)
                acct_written += w
                acct_stored += s
                acct_total += t
            except Exception as e:
                print(f"    {getattr(f, 'name', f)}: Fehler ({e!r})")
    finally:
        try:
            mb.logout()
        except Exception:
            pass
    return acct_written, acct_stored, acct_total


def main() -> int:
    ap = argparse.ArgumentParser(description="IMAP Collector (Stufe 2: rueckwirkend alles lokal)")
    ap.add_argument("--account", default=None, help="nur dieses Konto (label)")
    ap.add_argument("--folder", default=None, help="nur dieser Ordner")
    ap.add_argument("--batch", type=int, default=50, help="Mails pro Abruf-Batch (Default 50)")
    args = ap.parse_args()

    conn = C.db_connect()
    C.ensure_tables(conn)
    accounts = C.load_accounts(only=args.account)

    tot_w = tot_s = tot_t = 0
    for account in accounts:
        try:
            w, s, t = collect_account(conn, account, args.folder, args.batch)
            tot_w += w; tot_s += s; tot_t += t
        except SystemExit:
            raise
        except Exception as e:
            print(f"  FEHLER bei '{account.get('label')}': {e!r}")

    try:
        conn.execute(
            "INSERT INTO collection_log (collected_at, source, status, reason, records_written) "
            "VALUES (?, 'imap', 'success', NULL, ?)", (C.now_iso(), tot_w))
        conn.commit()
    except Exception:
        pass
    conn.close()

    print(f"\nGesamt: {tot_s}/{tot_t} Mails lokal (+{tot_w} neu in diesem Lauf).")
    if tot_t and tot_s >= tot_t:
        print("VOLLSTAENDIG: alle Mails aller Ordner liegen lokal.")
        return 0
    print(f"NOCH NICHT VOLLSTAENDIG: {max(0, tot_t - tot_s)} fehlen. Einfach erneut laufen lassen (resumiert).")
    return 2


if __name__ == "__main__":
    sys.exit(main())
