"""Hook beim Start jeder Sitzung (SessionStart, eingetragen in .claude/settings.json).

Luljeta merkt sich den Befehl /prime nicht. Darum gibt dieser Hook dem Mitarbeiter beim
Sitzungsstart den Auftrag mit, den /prime-Ablauf vor der ersten Antwort selbst auszufuehren.
Gibt nur Text aus, aendert nichts.
"""
import json
import sys

AUFTRAG = (
    "Neue Sitzung. Bevor du auf die erste Nachricht antwortest, fuehre den Ablauf aus "
    ".claude/commands/prime.md vollstaendig aus (still lesen, dann begruessen), "
    "ohne dass jemand /prime eintippen muss. Danach geh auf die erste Nachricht ein. "
    "Ausnahme: Hat die erste Nachricht selbst /prime aufgerufen, nicht doppelt ausfuehren."
)

json.dump({"hookSpecificOutput": {"hookEventName": "SessionStart",
                                  "additionalContext": AUFTRAG}}, sys.stdout)
