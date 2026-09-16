"""Runs every 5 minutes via systemd timer jason-calendar-watch.timer. Finds
any calendar event starting soon that hasn't been notified about yet, and
pushes it — clicking the notification opens that exact event in Google
Calendar (its own htmlLink, no need to construct one). Deliberately NOT a
Claude agent turn, same reasoning as check_reminders.py: "is this event
starting soon" is fully deterministic, no judgment call involved, so it
should never be blocked on an LLM call.

Wire this to systemd, e.g.:
    jason-calendar-watch.service (oneshot) + jason-calendar-watch.timer (OnCalendar=*:0/5)
"""

from __future__ import annotations

import asyncio
import json
from datetime import datetime, timedelta, timezone

import httpx

from agent import google_oauth as goauth
from agent.persona import DATA_DIR
from agent.push import send_push

CAL_BASE = "https://www.googleapis.com/calendar/v3"
USERS_FILE = DATA_DIR / "users.json"
STATE_FILE = DATA_DIR / "calendar_watch_state.json"

ADMIN_EMAIL = "dwightjonesuk@gmail.com"  # the Google account to watch — same
                                          # single-admin assumption as check_reminders.py

# Notify once an event starts within this many minutes — wide enough that a
# 5-minute poll interval can't miss one landing between two runs.
NOTIFY_WITHIN_MINUTES = 15
# How far ahead to even fetch — a little more than NOTIFY_WITHIN_MINUTES so
# an event doesn't first become visible already inside the notify window.
LOOKAHEAD_MINUTES = 30
# Prune notified-event records older than this so the state file doesn't
# grow forever — well past any plausible reschedule-and-refire window.
STATE_TTL_HOURS = 24


def _load_users() -> dict | None:
    if USERS_FILE.exists():
        try:
            return json.loads(USERS_FILE.read_text(encoding="utf-8"))
        except Exception:
            return None
    return None


def _load_state() -> dict:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def _save_state(state: dict) -> None:
    STATE_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")


def _prune_state(state: dict, now: datetime) -> dict:
    cutoff = now - timedelta(hours=STATE_TTL_HOURS)
    return {
        eid: ts for eid, ts in state.items()
        if datetime.fromisoformat(ts) > cutoff
    }


async def _fetch_upcoming_events(now: datetime) -> list[dict]:
    token = await goauth.get_access_token(ADMIN_EMAIL)
    if not token:
        print(f"[{now.isoformat()}] no Google account connected for {ADMIN_EMAIL} — skipping")
        return []
    headers = {"Authorization": f"Bearer {token}"}
    params = {
        "timeMin": now.isoformat(),
        "timeMax": (now + timedelta(minutes=LOOKAHEAD_MINUTES)).isoformat(),
        "singleEvents": "true",
        "orderBy": "startTime",
    }
    async with httpx.AsyncClient(timeout=20) as client:
        resp = await client.get(f"{CAL_BASE}/calendars/primary/events", headers=headers, params=params)
    if resp.status_code != 200:
        print(f"[{now.isoformat()}] calendar fetch failed (HTTP {resp.status_code}): {resp.text[:300]}")
        return []
    return resp.json().get("items", [])


async def main() -> None:
    now = datetime.now(timezone.utc)

    u = _load_users()
    admin = (u or {}).get("admin")
    subscription = (admin or {}).get("push_subscription")
    if not subscription:
        print(f"[{now.isoformat()}] no push subscription registered — skipping")
        return

    events = await _fetch_upcoming_events(now)
    if not events:
        return

    state = _prune_state(_load_state(), now)
    changed = False

    for ev in events:
        eid = ev.get("id")
        if not eid or eid in state:
            continue  # already notified about this one
        start_raw = (ev.get("start") or {}).get("dateTime")
        if not start_raw:
            continue  # all-day event — no specific time to count down to
        start = datetime.fromisoformat(start_raw)
        minutes_away = (start - now).total_seconds() / 60
        if minutes_away > NOTIFY_WITHIN_MINUTES:
            continue  # not soon enough yet — will be picked up on a later run

        title = ev.get("summary") or "(no title)"
        when = start.strftime("%H:%M")
        result = send_push(
            subscription,
            title=title,
            body=f"Starts at {when}" if minutes_away > 0 else "Starting now",
            url=ev.get("htmlLink", "/"),
        )
        if result.ok:
            print(f"[{now.isoformat()}] notified: {title!r} ({eid})")
            state[eid] = now.isoformat()
            changed = True
        elif result.gone:
            print(f"[{now.isoformat()}] push subscription gone — clearing it: {result.error}")
            if admin is not None:
                admin.pop("push_subscription", None)
                USERS_FILE.write_text(json.dumps(u, indent=2), encoding="utf-8")
            break  # no subscription left to send the rest to this run
        else:
            print(f"[{now.isoformat()}] push failed for {eid}: {result.error}")
            # Not marked as notified — will retry on the next run within the window.

    if changed:
        _save_state(state)


if __name__ == "__main__":
    asyncio.run(main())
