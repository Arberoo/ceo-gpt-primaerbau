#!/usr/bin/env python3
"""Auto-Commit: täglicher Hintergrund-Commit + Push + Logbuch für das CEO-GPT.

Ablauf (läuft als systemd-Timer, einmal täglich):
  1. Gibt es überhaupt Änderungen? Wenn nein, sauber beenden.
  2. Sicher stagen (git add -A; die .gitignore hält Secrets/DB/Medien draußen).
  3. Sicherheitsnetz: keine Einzeldatei > 50 MB committen (würde Push blockieren).
  4. KI (claude -p) erzeugt NUR Text: Commit-Nachricht + Logbuch-Eintrag,
     aus dem Diff und den heutigen Arbeits-Gesprächen (das "Warum").
  5. HISTORY.md fortschreiben, committen, pushen (Wiederholung bei Netz-Aussetzern).

Design-Prinzip: Die Git-Mechanik ist deterministisch in Python. Die KI liefert
nur Text und kann nichts Destruktives tun. Fällt die KI aus, wird trotzdem
gespeichert und gepusht (mit schlichter Auto-Nachricht). Speichern > schöne Worte.

Kein Telegram. Still im systemd-Journal protokolliert.
"""

import os
import re
import sys
import time
import json
import urllib.request
import subprocess
from pathlib import Path
from datetime import datetime

REPO = Path(__file__).resolve().parent.parent
HISTORY = REPO / "HISTORY.md"



def _load_env():
    """.env laden. Nutzt python-dotenv falls vorhanden, sonst ein Mini-Parser,
    damit der Runner auch im Basis-Modul ohne Zusatz-Abhängigkeiten läuft."""
    env_path = REPO / ".env"
    try:
        from dotenv import load_dotenv
        load_dotenv(env_path)
        return
    except Exception:
        pass
    if env_path.exists():
        for line in env_path.read_text(errors="ignore").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def _transcript_dir():
    """Verzeichnis der Claude-Code-Mitschnitte dieses Projekts, dynamisch statt
    hartkodiert: ~/.claude/projects/<workspace-pfad mit Nicht-Buchstaben als '-'>."""
    munged = re.sub(r"[^a-zA-Z0-9]", "-", str(REPO))
    return Path.home() / ".claude" / "projects" / munged


_load_env()
TRANSCRIPT_DIR = _transcript_dir()

DIFF_LIMIT = 60_000        # Zeichen Diff, die an die KI gehen
TRANSCRIPT_LIMIT = 30_000  # Zeichen Gesprächs-Kontext
MAX_FILE_BYTES = 50 * 1024 * 1024  # 50 MB Einzeldatei-Grenze (GitHub blockt bei 100)

NET_HINTS = (
    "could not resolve host", "temporary failure in name resolution",
    "name or service not known", "failed to resolve", "nameresolutionerror",
    "connection reset", "connection refused", "connection timed out",
    "timed out", "operation timed out", "failed to connect",
    "couldn't connect", "network is unreachable", "broken pipe", "urlopen error",
)


def log(msg: str) -> None:
    print(f"[auto-commit] {msg}", flush=True)


def git(*args, check=True, capture=True):
    """Git-Aufruf im Repo. Gibt (rc, stdout, stderr)."""
    res = subprocess.run(
        ["git", *args], cwd=REPO,
        capture_output=capture, text=True,
    )
    if check and res.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} -> rc={res.returncode}\n{res.stderr}")
    return res.returncode, (res.stdout or "").strip(), (res.stderr or "").strip()


def has_changes() -> bool:
    _, out, _ = git("status", "--porcelain")
    return bool(out)


def unstage_oversized() -> list:
    """Sicherheitsnetz: entfernt zu große Dateien aus dem Stage (sonst Push-Blocker)."""
    dropped = []
    _, out, _ = git("diff", "--cached", "--name-only")
    for rel in out.splitlines():
        rel = rel.strip()
        if not rel:
            continue
        p = REPO / rel
        try:
            if p.is_file() and p.stat().st_size > MAX_FILE_BYTES:
                git("reset", "-q", "HEAD", "--", rel, check=False)
                dropped.append(rel)
        except OSError:
            continue
    return dropped


def recent_transcripts(max_chars: int) -> str:
    """Text aus den zuletzt geänderten Session-Mitschnitten (Quelle fürs Warum)."""
    if not TRANSCRIPT_DIR.is_dir():
        return ""
    files = sorted(
        TRANSCRIPT_DIR.glob("*.jsonl"),
        key=lambda f: f.stat().st_mtime, reverse=True,
    )
    cutoff = time.time() - 36 * 3600  # letzte ~1,5 Tage
    chunks, total = [], 0
    for f in files:
        if f.stat().st_mtime < cutoff:
            break
        try:
            txt = f.read_text(errors="ignore")
        except OSError:
            continue
        # Nur die menschlich lesbaren Text-Schnipsel grob herausziehen
        snippet = txt[-max_chars:]
        chunks.append(snippet)
        total += len(snippet)
        if total >= max_chars:
            break
    return ("\n\n".join(chunks))[:max_chars]


def build_context() -> str:
    """Diff + Datei-Liste + Gespräche als stdin-Kontext für die KI."""
    _, names, _ = git("diff", "--cached", "--name-status")
    _, diff, _ = git("diff", "--cached", "--stat")
    _, fulldiff, _ = git("diff", "--cached")
    parts = [
        "## GEÄNDERTE DATEIEN\n" + names,
        "## DIFFSTAT\n" + diff,
        "## DIFF (gekürzt)\n" + fulldiff[:DIFF_LIMIT],
    ]
    tr = recent_transcripts(TRANSCRIPT_LIMIT)
    if tr:
        parts.append("## AUSZÜGE AUS DEN HEUTIGEN ARBEITS-GESPRÄCHEN (für das Warum)\n" + tr)
    return "\n\n".join(parts)


INSTRUCTION = """\
Du schreibst den Commit und den Logbuch-Eintrag für das CEO-GPT, ein privates \
Business-Repo. Du bekommst die geänderten Dateien, den Diff und \
Auszüge aus den heutigen Arbeits-Gesprächen.

Schreib auf Deutsch, direkt und knapp (Stil: Hormozi-nah, keine Gedankenstriche \
als Satztrenner). Nutz die Gespräche, um das WARUM zu erfassen, nicht nur das WAS. \
Erfinde nichts; wenn die Gespräche nichts hergeben, beschreib sachlich die Änderungen.

Gib GENAU dieses Format zurück, nichts davor, nichts danach:

SUBJECT: <typ>: <knappe Beschreibung, max 50 Zeichen, Präsens, kein Punkt am Ende>
BODY:
- <Stichpunkt>
- <Stichpunkt>
HISTORY:
### <kurzer Titel>
- <was gemacht wurde und warum, 2 bis 5 Stichpunkte>

Erlaubte Typen: feat, update, fix, data, context, docs, refactor, chore. \
Schreib die drei Marker SUBJECT, BODY und HISTORY exakt so (Großbuchstaben, mit \
Doppelpunkt). SUBJECT ist genau EINE Zeile, kein Zeilenumbruch darin. Kein \
Fließtext davor oder danach.\
"""


def ask_llm(context: str) -> str:
    """Erzeugt Commit-Text über die Claude-Subscription (claude_llm.complete).

    Läuft über das claude-agent-sdk (CLAUDE_CODE_OAUTH_TOKEN), kein API-Key. Hat kein
    Claude-Token, fällt der zentrale Helfer automatisch auf OpenRouter zurück, sofern
    OPENROUTER_API_KEY gesetzt ist (CEO_LLM_FALLBACK=1, Default). Gibt "" zurück, wenn
    nichts geht (dann greift die Fallback-Nachricht). Speichern hat Vorrang.
    """
    import sys as _sys
    from pathlib import Path as _Path
    _sys.path.insert(0, str(_Path(__file__).resolve().parent))
    from claude_llm import complete

    text = complete(context, system=INSTRUCTION, agent="autocommit",
                    max_tokens=2048, temperature=0.2)
    if not text:
        log("LLM-Aufruf lieferte keinen Text, nutze Fallback")
        return ""
    return text.strip()


def parse_llm(text: str):
    """Zerlegt die KI-Antwort in (subject, body, history). Tolerant gegenüber
    Markdown (**SUBJECT**), Groß/Kleinschreibung und leichten Formatabweichungen.
    None-Felder, wenn ein Teil fehlt; der Aufrufer hat dafür einen Fallback."""
    subject = body = history = None

    m = re.search(r"SUBJECT:\s*\**\s*(.+)", text, re.IGNORECASE)
    if m:
        s = m.group(1).strip().strip("*`").strip()
        subject = s.splitlines()[0][:72] if s else None

    mb = re.search(r"BODY:\s*\**\s*\n?(.*?)(?=\n\s*\**\s*HISTORY:|\Z)",
                   text, re.IGNORECASE | re.DOTALL)
    if mb:
        body = mb.group(1).strip() or None

    mh = re.search(r"HISTORY:\s*\**\s*\n?(.*)", text, re.IGNORECASE | re.DOTALL)
    if mh:
        history = mh.group(1).strip().strip("*").strip() or None

    return subject, body, history


def update_history(entry: str, today: str) -> None:
    """Schreibt den Logbuch-Eintrag unter das heutige Datum (neueste oben)."""
    if not entry:
        return
    text = HISTORY.read_text() if HISTORY.exists() else "# CEO-GPT Historie\n"
    block = entry.strip() + "\n"
    day_header = f"## {today}"
    if day_header in text:
        # An den bestehenden Tagesabschnitt anhängen (nach dem Header)
        idx = text.index(day_header) + len(day_header)
        nl = text.index("\n", idx)
        text = text[: nl + 1] + "\n" + block + text[nl + 1 :]
    else:
        # Neuen Tagesabschnitt vor dem ersten bestehenden "## " einfügen
        m = re.search(r"^## \d{4}-\d{2}-\d{2}", text, re.MULTILINE)
        new_section = f"## {today}\n\n{block}\n"
        if m:
            text = text[: m.start()] + new_section + text[m.start() :]
        else:
            text = text.rstrip() + "\n\n" + new_section
    HISTORY.write_text(text)


def push_with_retry() -> bool:
    """Push zum eingestellten Upstream, ein Retry bei transientem Netzfehler.
    Fällt auf 'push -u origin HEAD' zurück, falls noch kein Upstream gesetzt ist."""
    for attempt in (1, 2):
        rc, _, err = git("push", check=False)
        if rc == 0:
            return True
        low = err.lower()
        if any(s in low for s in ("no upstream", "set-upstream", "no configured push destination")):
            rc2, _, err2 = git("push", "-u", "origin", "HEAD", check=False)
            if rc2 == 0:
                return True
            err, low = err2, err2.lower()
        log(f"push fehlgeschlagen (Versuch {attempt}): {err.splitlines()[0] if err else rc}")
        if attempt == 1 and any(h in low for h in NET_HINTS):
            time.sleep(30)
            continue
        return False
    return False


def main() -> int:
    dry = "--dry-run" in sys.argv
    today = datetime.now().strftime("%Y-%m-%d")

    if not has_changes():
        log("nichts zu tun, Working Tree ist sauber")
        return 0

    git("add", "-A")
    dropped = unstage_oversized()
    if dropped:
        log("zu große Dateien NICHT committet (>50MB): " + ", ".join(dropped))

    _, staged, _ = git("diff", "--cached", "--name-only")
    n_files = len([x for x in staged.splitlines() if x.strip()])
    if n_files == 0:
        log("nach Sicherheitsfilter nichts mehr zu committen")
        return 0

    context = build_context()
    raw = ask_llm(context)
    subject, body, history = parse_llm(raw) if raw else (None, None, None)

    if not subject:
        subject = f"chore: Auto-Sicherung {today}"
        log("KI lieferte keinen Text, nutze Fallback-Nachricht")
    if not history:
        history = f"### Auto-Sicherung {today}\n- {n_files} Datei(en) automatisch gesichert und gepusht\n- (aus dem Diff erfasst, keine Gesprächsdetails verfügbar)"

    msg_args = ["-m", subject]
    if body:
        msg_args += ["-m", body]

    if dry:
        log("DRY-RUN, würde committen:")
        print("------ SUBJECT ------\n" + subject)
        print("------ BODY ------\n" + (body or "(keiner)"))
        print("------ HISTORY ------\n" + history)
        print(f"------ {n_files} Dateien, kein echter Commit/Push ------")
        git("reset", "-q", check=False)
        return 0

    update_history(history, today)
    git("add", "--", "HISTORY.md")
    git("commit", "-q", *msg_args)
    log(f"committet: {subject} ({n_files} Dateien)")

    if push_with_retry():
        log("gepusht zu origin/main")
        return 0
    log("Commit liegt lokal, Push scheiterte (wird beim nächsten Lauf erneut versucht)")
    return 1


if __name__ == "__main__":
    sys.exit(main())
