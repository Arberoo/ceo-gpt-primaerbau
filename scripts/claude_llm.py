"""Zentraler LLM-Helfer für das CEO-GPT.

Ein einziger Einstiegspunkt für Text- und Vision-Synthese. Standard läuft über die
Claude-Subscription (claude-agent-sdk, CLAUDE_CODE_OAUTH_TOKEN, kein API-Key), genau
wie die proaktiven Agenten. Optionaler Rückfall auf OpenRouter über einen Env-Schalter.

    from claude_llm import complete
    text = complete("Fasse das zusammen: ...", system="Du bist ...")

Bewusst NICHT hier (bleiben auf OpenRouter, kein Claude-Ersatz):
  - Audio-Transkription (Whisper)        -> apps/command/bot.py, scripts/transcribe.py
  - Bild-GENERIERUNG (Nano Banana)       -> scripts/meet_background.py, meet_edit.py
  - schnelles Voice-Front-Modell         -> apps/voice-spike/claude_brain.py

Schalter (.env):
  CEO_LLM_BACKEND   claude | openrouter   (Default claude)
  CEO_LLM_FALLBACK  1 | 0                 (Default 1: bei Claude-Fehler auf OpenRouter,
                                           falls OPENROUTER_API_KEY vorhanden)
  CEO_LLM_MODEL     OpenRouter-Modell-ID für den Rückfall (Default google/gemini-2.5-flash)
"""

import asyncio
import base64
import json
import os
import urllib.request
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
USAGE_LEDGER = ROOT / "data" / "agents" / "usage.jsonl"
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
DEFAULT_OR_MODEL = "google/gemini-2.5-flash"

_NET_HINTS = (
    "nodename nor servname", "Name or service not known", "Temporary failure in name",
    "Failed to resolve", "NameResolutionError", "Read timed out", "Connection timed out",
    "Connection refused", "Connection reset", "TimeoutError",
)


def _ensure_claude_on_path():
    p = str(Path.home() / ".local" / "bin")
    if p not in os.environ.get("PATH", ""):
        os.environ["PATH"] = os.environ.get("PATH", "") + ":" + p


def _log_usage(agent, model, usage, cost, dur):
    """Verbrauch eines Claude-Aufrufs protokollieren (geteiltes Ledger mit den Agenten)."""
    try:
        USAGE_LEDGER.parent.mkdir(parents=True, exist_ok=True)
        u = usage or {}
        rec = {
            "ts": datetime.now().isoformat(timespec="seconds"),
            "agent": agent or "llm", "model": model or "",
            "in": int(u.get("input_tokens", 0) or 0),
            "out": int(u.get("output_tokens", 0) or 0),
            "cache_create": int(u.get("cache_creation_input_tokens", 0) or 0),
            "cache_read": int(u.get("cache_read_input_tokens", 0) or 0),
            "cost_usd": round(float(cost or 0), 6), "ms": int(dur or 0),
        }
        with open(USAGE_LEDGER, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    except Exception:
        pass


def _read_image(image, media_type=None):
    """image -> (base64-str, media_type). Akzeptiert Pfad (str/Path) oder rohe bytes."""
    if isinstance(image, (str, Path)):
        path = Path(image)
        data = path.read_bytes()
        if not media_type:
            ext = path.suffix.lower()
            media_type = {
                ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
                ".webp": "image/webp", ".gif": "image/gif",
            }.get(ext, "image/jpeg")
    else:
        data = image
        media_type = media_type or "image/jpeg"
    return base64.b64encode(data).decode(), media_type


def _claude(user, system, image, image_media_type, agent, max_turns):
    """Single-Shot-Claude-Aufruf über die Subscription. Text raus, None bei Fehler."""
    _ensure_claude_on_path()
    if not (os.environ.get("CLAUDE_CODE_OAUTH_TOKEN") or os.environ.get("ANTHROPIC_API_KEY")):
        print("[claude_llm] keine Claude-Auth (CLAUDE_CODE_OAUTH_TOKEN fehlt)", flush=True)
        return None
    try:
        from claude_agent_sdk import query, ClaudeAgentOptions
    except Exception as exc:
        print(f"[claude_llm] SDK-Import fehlgeschlagen: {exc}", flush=True)
        return None

    opts = ClaudeAgentOptions(
        system_prompt=system or "",
        max_turns=max_turns,
        setting_sources=[],   # kein Projekt-CLAUDE.md/Hooks -> schlank + kontrolliert
    )

    if image is not None:
        b64, mtype = _read_image(image, image_media_type)
        async def _prompt():
            yield {
                "type": "user",
                "message": {"role": "user", "content": [
                    {"type": "text", "text": user},
                    {"type": "image", "source": {
                        "type": "base64", "media_type": mtype, "data": b64}},
                ]},
            }
        prompt_arg = _prompt()
    else:
        prompt_arg = user

    async def _go():
        result_text, parts = None, []
        model, usage, cost, dur = None, None, None, None
        async for msg in query(prompt=prompt_arg, options=opts):
            if getattr(msg, "model", None):
                model = msg.model
            r = getattr(msg, "result", None)
            if isinstance(r, str) and r.strip():
                result_text = r.strip()
            content = getattr(msg, "content", None)
            if isinstance(content, list):
                for b in content:
                    t = getattr(b, "text", None)
                    if t and t.strip():
                        parts.append(t.strip())
            if getattr(msg, "total_cost_usd", None) is not None:
                cost = getattr(msg, "total_cost_usd", None)
                usage = getattr(msg, "usage", None)
                dur = getattr(msg, "duration_ms", None)
        return (result_text or " ".join(parts).strip() or None), model, usage, cost, dur

    try:
        text, model, usage, cost, dur = asyncio.run(_go())
        _log_usage(agent, model, usage, cost, dur)
        return text
    except Exception as exc:
        print(f"[claude_llm] Claude-Aufruf fehlgeschlagen: {type(exc).__name__}: {str(exc)[:200]}", flush=True)
        return None


def _openrouter(user, system, model, temperature, max_tokens, image, image_media_type,
                want_json, timeout, retry):
    """Rückfall-Pfad: OpenRouter (OpenAI-kompatibel). Text raus, None bei Fehler."""
    import time
    key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    if not key:
        return None
    if image is not None:
        b64, mtype = _read_image(image, image_media_type)
        content = [{"type": "text", "text": user},
                   {"type": "image_url", "image_url": {"url": f"data:{mtype};base64,{b64}"}}]
        user_msg = {"role": "user", "content": content}
    else:
        user_msg = {"role": "user", "content": user}
    messages = ([{"role": "system", "content": system}] if system else []) + [user_msg]
    payload = {"model": model or os.environ.get("CEO_LLM_MODEL", DEFAULT_OR_MODEL),
               "messages": messages}
    if temperature is not None:
        payload["temperature"] = temperature
    if max_tokens is not None:
        payload["max_tokens"] = max_tokens
    if want_json:
        payload["response_format"] = {"type": "json_object"}
    body = json.dumps(payload).encode("utf-8")
    for attempt in (1, 2):
        try:
            req = urllib.request.Request(
                OPENROUTER_URL, data=body, method="POST",
                headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json",
                         "HTTP-Referer": "https://ceogpt.de", "X-Title": "CEO-GPT LLM"})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                out = json.loads(resp.read().decode("utf-8"))
            return (out["choices"][0]["message"]["content"] or "").strip()
        except Exception as exc:
            if attempt == 1 and retry and any(h in repr(exc) for h in _NET_HINTS):
                time.sleep(20)
                continue
            print(f"[claude_llm] OpenRouter-Rückfall scheiterte: {type(exc).__name__}: {str(exc)[:160]}", flush=True)
            return None
    return None


def complete(user, system=None, *, agent=None, image=None, image_media_type=None,
             max_tokens=None, temperature=None, want_json=False, allow_fallback=None,
             max_turns=1, timeout=120, retry=True):
    """Eine Antwort vom Modell holen.

    user        Nutzer-Prompt (str).
    system      optionaler System-Prompt.
    agent       Label fürs Verbrauchs-Ledger.
    image       optionales Bild (Pfad oder bytes) für Vision.
    max_tokens/temperature/want_json  best effort: greifen am OpenRouter-Rückfall;
                Claude über die Subscription steuert diese nicht 1:1.
    Rückgabe: Text (str) oder None bei Fehler.
    """
    backend = (os.environ.get("CEO_LLM_BACKEND") or "claude").strip().lower()
    if allow_fallback is None:
        allow_fallback = os.environ.get("CEO_LLM_FALLBACK", "1").strip() not in ("0", "false", "no")

    if backend == "openrouter":
        return _openrouter(user, system, os.environ.get("CEO_LLM_MODEL"), temperature,
                           max_tokens, image, image_media_type, want_json, timeout, retry)

    text = _claude(user, system, image, image_media_type, agent, max_turns)
    if text:
        return text
    if allow_fallback and os.environ.get("OPENROUTER_API_KEY", "").strip():
        print("[claude_llm] Rückfall auf OpenRouter.", flush=True)
        return _openrouter(user, system, os.environ.get("CEO_LLM_MODEL"), temperature,
                           max_tokens, image, image_media_type, want_json, timeout, retry)
    return text


if __name__ == "__main__":
    import sys
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
    if len(sys.argv) > 1 and sys.argv[1] == "--vision":
        img = sys.argv[2]
        out = complete("Was ist auf diesem Bild? Antworte in einem kurzen Satz.", image=img, agent="selftest")
    else:
        out = complete("Antworte mit genau dem Wort: bereit.", agent="selftest")
    print("--- Ergebnis ---")
    print(out)
