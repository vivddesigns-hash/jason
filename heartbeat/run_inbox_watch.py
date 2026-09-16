"""Periodic email/calendar watch, run as a REAL Jason turn — not a separate
script pretending to judge on his behalf. Dwight was explicit about this:
he wants Jason himself deciding what's worth interrupting him for, using
his own Gmail/Calendar tools and his own judgment, the same as a real
assistant would — not a bolted-on classifier that bypasses him entirely
(an earlier version did exactly that, was flagged as not matching what was
asked, and was fully removed).

The schedule is Dwight's to change, not fixed by us: a systemd timer fires
this frequently (every 5 minutes — the finest granularity worth having),
but each firing checks INBOX_WATCH_CONFIG first and does nothing at all
(no LLM call, no cost) unless `interval_minutes` has actually elapsed
since the last real check. Dwight (or Jason on his behalf, since Jason has
ordinary Read/Edit access to his own data files) just edits that JSON file
to change the interval — no server access, no systemd changes, no asking
Claude Code to redeploy anything. Genuinely "at will."

Wire this to systemd, e.g.:
    jason-inbox-watch.service (oneshot) + jason-inbox-watch.timer (OnCalendar=*:0/5)
"""

from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone

from agent.core import stream_chat
from agent.persona import DATA_DIR, SOUL, _read

CONFIG_FILE = DATA_DIR / "inbox_watch_config.json"
DEFAULT_INTERVAL_MINUTES = 20


def _load_config() -> dict:
    if CONFIG_FILE.exists():
        try:
            return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"interval_minutes": DEFAULT_INTERVAL_MINUTES, "last_run_at": None}


def _save_config(config: dict) -> None:
    CONFIG_FILE.write_text(json.dumps(config, indent=2), encoding="utf-8")


def _due(config: dict, now: datetime) -> bool:
    last_run_raw = config.get("last_run_at")
    if not last_run_raw:
        return True  # never run before
    last_run = datetime.fromisoformat(last_run_raw)
    interval = config.get("interval_minutes", DEFAULT_INTERVAL_MINUTES)
    return (now - last_run).total_seconds() >= interval * 60


async def main() -> None:
    now = datetime.now(timezone.utc)
    config = _load_config()

    if not _due(config, now):
        return  # too soon since the last real check — no LLM call, no cost

    checklist = _read(SOUL / "INBOX_WATCH.md", strip=True)
    prompt = (
        "This is your periodic inbox/calendar watch (running in the background, "
        "the user is not watching). Work through the checklist below using your "
        "own real Gmail and Calendar tools and your own judgment — you decide "
        "what's worth surfacing, the same as you would in a live conversation if "
        "Dwight asked 'anything important?'. Most runs should find nothing worth "
        "interrupting him for — that's normal, stay quiet in that case.\n\n"
        "Delivery: if something genuinely clears the bar, use `assistant "
        "notifications send` directly (title + message + a link to the exact "
        "email or event, `--urgent` if it's actually time-sensitive). If "
        "there's nothing worth surfacing, don't call it — silence is the "
        "correct output most of the time.\n\n"
        + checklist
    )

    async for event in stream_chat("inbox-watch", prompt):
        if event["type"] == "text":
            print(event["text"], end="", flush=True)
        elif event["type"] == "tool":
            print(f"\n[· {event['name']}]", flush=True)
        elif event["type"] == "error":
            print(f"\n[error] {event['error']}", flush=True)
    print()

    config["last_run_at"] = now.isoformat()
    _save_config(config)


if __name__ == "__main__":
    asyncio.run(main())
