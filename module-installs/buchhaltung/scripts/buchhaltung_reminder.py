"""
Buchhaltungs-Reminder: pusht vor der Frist, die Buchhaltung des Vormonats zu machen.

Laeuft taeglich (launchd), schickt aber nur an den in der Config gesetzten
Sende-Tagen einen eskalierenden Reminder, die Belege fuer den Vormonat fertig zu
machen und an den Steuerberater zu geben.

Alles Nutzerspezifische (Frist, Sende-Tage, Steuerberater-Name, Sprache, Kanal)
kommt aus buchhaltung.config.json. Versand ueber die Telegram-Bot-API
(TELEGRAM_BOT_TOKEN + TELEGRAM_GROUP_ID aus der .env), nur wenn channel=telegram
und die Variablen gesetzt sind.

Aufruf:
    python3 scripts/buchhaltung_reminder.py            # echt senden (nur an Sende-Tagen)
    python3 scripts/buchhaltung_reminder.py --dry-run  # nur ausgeben
    python3 scripts/buchhaltung_reminder.py --force    # auch ausserhalb der Sende-Tage
"""
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent


def workspace_root() -> Path:
    d = HERE
    for _ in range(8):
        if (d / "CLAUDE.md").exists():
            return d
        if d.parent == d:
            break
        d = d.parent
    return HERE.parent


WS = workspace_root()

MONTHS = {
    "de": ["", "Januar", "Februar", "Maerz", "April", "Mai", "Juni",
           "Juli", "August", "September", "Oktober", "November", "Dezember"],
    "en": ["", "January", "February", "March", "April", "May", "June",
           "July", "August", "September", "October", "November", "December"],
}


def load_env() -> None:
    env_path = WS / ".env"
    if not env_path.exists():
        return
    try:
        from dotenv import load_dotenv
        load_dotenv(env_path)
        return
    except ImportError:
        pass
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip())


def load_config() -> dict:
    for p in [WS / ".claude" / "skills" / "buchhaltung" / "buchhaltung.config.json",
              WS / "buchhaltung.config.json", HERE / "buchhaltung.config.json"]:
        if p.exists():
            return json.loads(p.read_text(encoding="utf-8"))
    return {}


def prev_month_name(now: datetime, lang: str) -> str:
    m = now.month - 1 or 12
    return MONTHS.get(lang, MONTHS["de"])[m]


def build_message(now: datetime, cfg: dict) -> str | None:
    rem = cfg.get("reminder", {})
    send_days = set(rem.get("send_days", [1, 5, 8, 10]))
    deadline = cfg.get("accountant", {}).get("deadline_day", 10)
    lang = cfg.get("language", "de")
    stb = cfg.get("accountant", {}).get("name") or ("deinen Steuerberater" if lang == "de" else "your accountant")
    day = now.day
    if day not in send_days:
        return None
    vormonat = prev_month_name(now, lang)
    days_left = deadline - day
    ask_private = cfg.get("private_expenses", {}).get("ask_monthly", True)

    if lang == "en":
        privhint = ("\n\nPaid anything privately or in cash this month that is business related? "
                    "Capture it too.") if ask_private else ""
        if day == min(send_days):
            return (f"\U0001F9FE *New month, time for the books.*\n\n"
                    f"Close *{vormonat}* and hand the documents to {stb}. Deadline: *day {deadline}*.\n\n"
                    f"Four categories per month: sales invoices, purchase invoices, expenses, "
                    f"bank statement (CSV and PDF, full month).{privhint}\n\n"
                    f"▶ Reply `Buchhaltung` and I pull the status and we close the month.")
        if day >= deadline:
            return (f"\U0001F9FE \U0001F6A8 *Due today: bookkeeping {vormonat}.*\n\n"
                    f"The documents need to go to {stb} today. If anything is open, we finish it now."
                    f"{privhint}\n\n▶ Reply `Buchhaltung`, we pull the status and close.")
        return (f"\U0001F9FE *Bookkeeping {vormonat}: {days_left} days left until the deadline (day {deadline}).*\n\n"
                f"Done already? If not: bank export (CSV + PDF), collect missing receipts, "
                f"send the list to {stb}.{privhint}\n\n"
                f"▶ Reply `Buchhaltung` and we see what is missing.")

    privhint = ("\n\nDiesen Monat etwas privat oder bar bezahlt, das geschaeftlich ist? "
                "Mit erfassen.") if ask_private else ""
    if day == min(send_days):
        return (f"\U0001F9FE *Neuer Monat, Zeit fuer die Buchhaltung.*\n\n"
                f"Schliess den *{vormonat}* ab und gib die Unterlagen an {stb}. "
                f"Frist: *{deadline}. des Monats*.\n\n"
                f"Vier Kategorien pro Monat: Ausgangsrechnungen, Eingangsrechnungen, "
                f"Belege, Kontoauszug (als CSV UND PDF, voller Monat).{privhint}\n\n"
                f"▶ Antworte mit `Buchhaltung`, dann ziehe ich den Stand und wir machen den Monat zu.")
    if day >= deadline:
        return (f"\U0001F9FE \U0001F6A8 *HEUTE faellig: Buchhaltung {vormonat}.*\n\n"
                f"Die Unterlagen muessen heute an {stb} raus. Wenn noch was offen ist, "
                f"machen wir es jetzt fertig.{privhint}\n\n"
                f"▶ Antworte mit `Buchhaltung`, wir ziehen den Stand und schliessen ab.")
    return (f"\U0001F9FE *Buchhaltung {vormonat}: noch {days_left} Tage bis zur Frist ({deadline}.).*\n\n"
            f"Schon erledigt? Falls nicht: Bank-Export (CSV + PDF), fehlende Belege holen, "
            f"Buchungsliste an {stb}.{privhint}\n\n"
            f"▶ Antworte mit `Buchhaltung`, dann sehen wir sofort, was noch fehlt.")


def send_to_telegram(message: str) -> bool:
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.environ.get("TELEGRAM_GROUP_ID", "").strip()
    if not bot_token or not chat_id:
        print("FEHLER: TELEGRAM_BOT_TOKEN oder TELEGRAM_GROUP_ID nicht in der .env.", file=sys.stderr)
        return False
    data = urllib.parse.urlencode(
        {"chat_id": chat_id, "text": message, "parse_mode": "Markdown"}
    ).encode("utf-8")
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{bot_token}/sendMessage", data=data, method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            body = json.loads(resp.read().decode("utf-8"))
            if body.get("ok"):
                return True
            print(f"FEHLER: Telegram-Response: {body}", file=sys.stderr)
            return False
    except urllib.error.HTTPError as e:
        print(f"FEHLER: HTTP {e.code} {e.read().decode('utf-8', errors='replace')[:200]}", file=sys.stderr)
        return False
    except Exception as e:  # noqa: BLE001
        print(f"FEHLER beim Senden: {e}", file=sys.stderr)
        return False


def main() -> int:
    load_env()
    cfg = load_config()
    now = datetime.now()
    force = "--force" in sys.argv

    message = build_message(now, cfg)
    if message is None and force:
        send_days = sorted(set(cfg.get("reminder", {}).get("send_days", [1, 5, 8, 10])))
        nearest = min(send_days, key=lambda d: abs(d - now.day))
        message = build_message(now.replace(day=nearest), cfg)
    if message is None:
        sd = sorted(set(cfg.get("reminder", {}).get("send_days", [1, 5, 8, 10])))
        print(f"Tag {now.day} ist kein Sende-Tag ({sd}), kein Reminder.")
        return 0

    if "--dry-run" in sys.argv:
        print("=== DRY-RUN (keine Nachricht gesendet) ===")
        print(message)
        return 0

    channel = cfg.get("reminder", {}).get("channel", "telegram")
    if channel != "telegram":
        print(f"Reminder-Kanal '{channel}' nicht unterstuetzt, kein Versand. Nachricht:\n{message}")
        return 0

    ok = send_to_telegram(message)
    if ok:
        print("Buchhaltungs-Reminder an Telegram geschickt.")
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
