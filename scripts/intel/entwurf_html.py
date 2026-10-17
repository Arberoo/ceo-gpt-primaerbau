"""HTML-Entwurf mit eingebetteten Bildern (z. B. Signatur mit Foto und Logo) ablegen.

Der Live-Mailzugriff (mail_pb_*, save_draft) haengt Bilder nur als normale Anhaenge an,
nicht eingebettet. Dieses Skript legt einen Entwurf als multipart/related an, damit Foto
und Logo in der Signatur sichtbar sind. Bewusst eng:

- legt NUR im Entwuerfe-Ordner (IMAP-Kennzeichen \\Drafts) ab, mit Kennzeichen \\Draft
- sendet nichts (kein SMTP), Empfaenger traegt Luljeta beim Abschicken selbst ein
  (optional --an fuer einen vorgegebenen Empfaenger)

Signatur: Vorlage data/signatur/<name>.html (beginnt mit Name und Berufsbezeichnung fett,
der Mailtext endet daher nur mit dem Gruss) mit Platzhaltern cid:foto und cid:logo,
Bilder data/signatur/*.png (lokal, nie GitHub).

Usage:
    python scripts/intel/entwurf_html.py pb_info --betreff "..." --text text.html \
        --signatur luljeta [--antwort-auf UID [--ordner INBOX]] [--an a@b.de] [--anhang datei ...]

Antworten immer mit --antwort-auf (Wunsch Luljeta, 16.10.2026): dann haengt der bisherige
Verlauf unten dran wie bei 'Antworten' in Outlook. --in-reply-to allein verknuepft nur.
"""

import sys
import argparse
import mimetypes
from pathlib import Path
from email.message import EmailMessage
from email.utils import make_msgid, formatdate

sys.path.insert(0, str(Path(__file__).resolve().parent))
import imap_common as C  # noqa: E402

SIG_DIR = C.WORKSPACE / "data" / "signatur"
BILDER = {"foto": "luljeta-foto.png", "logo": "primaerbau-logo.png"}


def ordner_mit(mb, kennzeichen: str) -> str | None:
    for f in mb.folder.list():
        if C.special_use_of(getattr(f, "flags", ())) == kennzeichen:
            return f.name
    return None


def verlauf_html(m) -> str:
    """Originalmail wie bei 'Antworten' in Outlook: Trennlinie, Kopf (Von/Gesendet/An/Betreff), Text."""
    import html as h
    import re
    absender = h.escape(f"{m.from_values.full}" if m.from_values else m.from_)
    an = h.escape("; ".join(v.full for v in m.to_values))
    cc = h.escape("; ".join(v.full for v in m.cc_values))
    gesendet = m.date.astimezone().strftime("%d.%m.%Y %H:%M") if m.date else ""
    kopf = (f"<b>Von:</b> {absender}<br><b>Gesendet:</b> {gesendet}<br><b>An:</b> {an}<br>"
            + (f"<b>Cc:</b> {cc}<br>" if cc else "")
            + f"<b>Betreff:</b> {h.escape(m.subject)}")
    if m.html:
        koerper = m.html
        treffer = re.search(r"<body[^>]*>(.*)</body>", koerper, re.S | re.I)
        if treffer:
            koerper = treffer.group(1)
        koerper = re.sub(r"<(script|style|head)[^>]*>.*?</\1>", "", koerper, flags=re.S | re.I)
    else:
        koerper = h.escape(m.text).replace("\n", "<br>")
    return ("<div style=\"border:none;border-top:solid #E1E1E1 1.0pt;padding:3.0pt 0 0 0;margin-top:12pt\">"
            f"<p>{kopf}</p></div><div>{koerper}</div>")


def main() -> int:
    ap = argparse.ArgumentParser(description="HTML-Entwurf mit Signatur-Bildern ablegen")
    ap.add_argument("konto")
    ap.add_argument("--betreff", required=True)
    ap.add_argument("--text", required=True, help="HTML-Datei mit dem Mailtext (ohne Signatur)")
    ap.add_argument("--signatur", default="luljeta", help="Name der Vorlage in data/signatur/")
    ap.add_argument("--in-reply-to")
    ap.add_argument("--antwort-auf", metavar="UID",
                    help="UID der Mail, auf die geantwortet wird: Verlauf wird unten angehaengt "
                         "(wie Antworten in Outlook), In-Reply-To/References automatisch")
    ap.add_argument("--ordner", default="INBOX", help="Ordner der Mail aus --antwort-auf")
    ap.add_argument("--an")
    ap.add_argument("--cc")
    ap.add_argument("--anhang", action="append", default=[], help="Datei anhaengen (mehrfach moeglich)")
    args = ap.parse_args()

    konto = C.load_accounts(args.konto)[0]
    domain = konto["username"].split("@", 1)[1]
    cids = {k: make_msgid(domain=domain) for k in BILDER}

    sig = (SIG_DIR / f"{args.signatur}.html").read_text(encoding="utf-8")
    for k, cid in cids.items():
        sig = sig.replace(f"cid:{k}", f"cid:{cid[1:-1]}")
    text = Path(args.text).read_text(encoding="utf-8")
    # Name und Berufsbezeichnung stehen fett in der Signatur-Vorlage (Wunsch Luljeta, 15.10.2026).
    # Der Mailtext endet nur mit dem Gruss, sonst stuende der Name doppelt da.
    if "Luljeta Bajraktari" in sig and "Luljeta Bajraktari" in text:
        print("FEHLER: Der Mailtext enthaelt den Namen schon, er kommt aus der Signatur. Text nur mit dem Gruss enden lassen.")
        return 1
    # Luljeta schreibt in Calibri 11 pt (Outlook-Standard, geprueft 15.10.2026), Ersatz Arial
    schrift = "font-family:Calibri,Arial,sans-serif;font-size:11pt"

    # Antwort: Originalmail holen und als Verlauf unter die Signatur haengen
    orig, verlauf = None, ""
    if args.antwort_auf:
        mt = C.imp("imap_tools")
        mb = C.connect(konto)
        try:
            mb.folder.set(args.ordner, readonly=True)
            treffer = list(mb.fetch(mt.A(uid=args.antwort_auf), mark_seen=False))
        finally:
            mb.logout()
        if not treffer:
            print(f"FEHLER: Mail UID {args.antwort_auf} in '{args.ordner}' nicht gefunden.")
            return 1
        orig = treffer[0]
        verlauf = verlauf_html(orig)

    html = (f"<html><head><style>body,p,div,td{{{schrift}}}</style></head>"
            f"<body style=\"{schrift}\">{text}{sig}{verlauf}</body></html>")

    msg = EmailMessage()
    msg["From"] = f"{konto.get('full_name', 'PrimärBau GmbH')} <{konto['username']}>"
    if args.an:
        msg["To"] = args.an
    if args.cc:
        msg["Cc"] = args.cc
    msg["Subject"] = args.betreff
    msg["Date"] = formatdate(localtime=True)
    msg["Message-ID"] = make_msgid(domain=domain)
    if orig is not None:
        mid = (orig.headers.get("message-id") or ("",))[0].strip()
        refs = (orig.headers.get("references") or ("",))[0].strip()
        if mid:
            msg["In-Reply-To"] = mid
            msg["References"] = f"{refs} {mid}".strip()
    elif args.in_reply_to:
        msg["In-Reply-To"] = args.in_reply_to
        msg["References"] = args.in_reply_to
    msg.set_content("Bitte HTML-Ansicht verwenden.")
    msg.add_alternative(html, subtype="html")
    html_teil = msg.get_payload()[1]
    for k, datei in BILDER.items():
        html_teil.add_related((SIG_DIR / datei).read_bytes(), "image", "png",
                              cid=cids[k], filename=datei, disposition="inline")
    # Eingebettete Bilder des Verlaufs (Logos, Signaturen) mitnehmen, sonst fehlen sie unten
    if orig is not None:
        for a in orig.attachments:
            if a.content_id and a.content_type.startswith("image/"):
                haupt, unter = a.content_type.split("/", 1)
                html_teil.add_related(a.payload, haupt, unter, cid=f"<{a.content_id.strip('<>')}>",
                                      filename=a.filename or None, disposition="inline")
    for pfad in map(Path, args.anhang):
        typ = mimetypes.guess_type(pfad.name)[0] or "application/octet-stream"
        haupt, unter = typ.split("/", 1)
        msg.add_attachment(pfad.read_bytes(), maintype=haupt, subtype=unter, filename=pfad.name)

    mb = C.connect(konto)
    try:
        entwuerfe = ordner_mit(mb, "\\Drafts")
        if not entwuerfe:
            print("FEHLER: Entwuerfe-Ordner nicht gefunden.")
            return 1
        mb.append(msg.as_bytes(), entwuerfe, flag_set=["\\Draft", "\\Seen"])
        print(f"Entwurf abgelegt in '{entwuerfe}': {args.betreff} | {msg['Message-ID']}")
        return 0
    finally:
        try:
            mb.logout()
        except Exception:
            pass


if __name__ == "__main__":
    sys.exit(main())
