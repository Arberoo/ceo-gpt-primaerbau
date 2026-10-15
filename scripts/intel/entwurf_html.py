"""HTML-Entwurf mit eingebetteten Bildern (z. B. Signatur mit Foto und Logo) ablegen.

Der Live-Mailzugriff (mail_pb_*, save_draft) haengt Bilder nur als normale Anhaenge an,
nicht eingebettet. Dieses Skript legt einen Entwurf als multipart/related an, damit Foto
und Logo in der Signatur sichtbar sind. Bewusst eng:

- legt NUR im Entwuerfe-Ordner (IMAP-Kennzeichen \\Drafts) ab, mit Kennzeichen \\Draft
- sendet nichts (kein SMTP), Empfaenger traegt Luljeta beim Abschicken selbst ein
  (optional --an fuer einen vorgegebenen Empfaenger)

Signatur: Vorlage data/signatur/<name>.html mit Platzhaltern cid:foto und cid:logo,
Bilder data/signatur/*.png (lokal, nie GitHub).

Usage:
    python scripts/intel/entwurf_html.py pb_info --betreff "..." --text text.html \
        --signatur luljeta [--in-reply-to "<id>"] [--an a@b.de]
"""

import sys
import argparse
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


def main() -> int:
    ap = argparse.ArgumentParser(description="HTML-Entwurf mit Signatur-Bildern ablegen")
    ap.add_argument("konto")
    ap.add_argument("--betreff", required=True)
    ap.add_argument("--text", required=True, help="HTML-Datei mit dem Mailtext (ohne Signatur)")
    ap.add_argument("--signatur", default="luljeta", help="Name der Vorlage in data/signatur/")
    ap.add_argument("--in-reply-to")
    ap.add_argument("--an")
    ap.add_argument("--cc")
    args = ap.parse_args()

    konto = C.load_accounts(args.konto)[0]
    domain = konto["username"].split("@", 1)[1]
    cids = {k: make_msgid(domain=domain) for k in BILDER}

    sig = (SIG_DIR / f"{args.signatur}.html").read_text(encoding="utf-8")
    for k, cid in cids.items():
        sig = sig.replace(f"cid:{k}", f"cid:{cid[1:-1]}")
    text = Path(args.text).read_text(encoding="utf-8")
    # Luljeta schreibt in Calibri 11 pt (Outlook-Standard, geprueft 15.10.2026), Ersatz Arial
    schrift = "font-family:Calibri,Arial,sans-serif;font-size:11pt"
    html = (f"<html><head><style>body,p,div,td{{{schrift}}}</style></head>"
            f"<body style=\"{schrift}\">{text}{sig}</body></html>")

    msg = EmailMessage()
    msg["From"] = f"{konto.get('full_name', 'PrimärBau GmbH')} <{konto['username']}>"
    if args.an:
        msg["To"] = args.an
    if args.cc:
        msg["Cc"] = args.cc
    msg["Subject"] = args.betreff
    msg["Date"] = formatdate(localtime=True)
    msg["Message-ID"] = make_msgid(domain=domain)
    if args.in_reply_to:
        msg["In-Reply-To"] = args.in_reply_to
        msg["References"] = args.in_reply_to
    msg.set_content("Bitte HTML-Ansicht verwenden.")
    msg.add_alternative(html, subtype="html")
    html_teil = msg.get_payload()[1]
    for k, datei in BILDER.items():
        html_teil.add_related((SIG_DIR / datei).read_bytes(), "image", "png",
                              cid=cids[k], filename=datei, disposition="inline")

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
