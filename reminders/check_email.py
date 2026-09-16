"""Runs every 15 minutes via systemd timer jason-email-watch.timer. Finds
newly-unread Gmail messages since the last run and, for each one Jason
hasn't seen before, asks a fast/cheap model (Haiku) a single yes/no
question: is this actually worth interrupting Dwight for right now. Only
pushes a notification for the ones that come back yes — clicking it opens
that exact message in Gmail.

Deliberately NOT a full agent turn like heartbeat (that would load the
whole persona/memory/tool set for what's really a one-line classification),
but NOT purely mechanical like check_reminders.py/check_calendar.py either
— "is this email important" genuinely needs a judgment call a timestamp
comparison can't make, so a small isolated model call is the middle ground.

Wire this to systemd, e.g.:
    jason-email-watch.service (oneshot) + jason-email-watch.timer (OnCalendar=*:0/15)
"""

from __future__ import annotations

import asyncio
import json
import os
from datetime import datetime, timedelta, timezone

import anthropic
import httpx

from agent import google_oauth as goauth
from agent.persona import DATA_DIR
from agent.push import send_push

GMAIL_BASE = "https://www.googleapis.com/gmail/v1"
USERS_FILE = DATA_DIR / "users.json"
STATE_FILE = DATA_DIR / "email_watch_state.json"

ADMIN_EMAIL = "dwightjonesuk@gmail.com"  # same single-admin assumption as check_reminders.py

CLASSIFY_MODEL = "claude-haiku-4-5-20251001"  # fast + cheap — this is a one-line
                                               # yes/no classification, not a task
                                               # that needs the flagship model

MAX_CANDIDATES_PER_RUN = 20  # cap in case a lot piled up since the last run
# Prune seen-message records older than this so the state file doesn't grow
# forever — well past how long a message could plausibly still be "new".
STATE_TTL_HOURS = 48


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
        mid: ts for mid, ts in state.items()
        if datetime.fromisoformat(ts) > cutoff
    }


async def _fetch_unread_ids(headers: dict, now: datetime) -> list[str]:
    params = {"q": "is:unread newer_than:2d", "maxResults": MAX_CANDIDATES_PER_RUN}
    async with httpx.AsyncClient(timeout=20) as client:
        resp = await client.get(f"{GMAIL_BASE}/users/me/messages", headers=headers, params=params)
    if resp.status_code != 200:
        print(f"[{now.isoformat()}] gmail list failed (HTTP {resp.status_code}): {resp.text[:300]}")
        return []
    return [m["id"] for m in resp.json().get("messages", [])]


async def _fetch_message_meta(headers: dict, msg_id: str, now: datetime) -> dict | None:
    params = {"format": "metadata", "metadataHeaders": ["Subject", "From"]}
    async with httpx.AsyncClient(timeout=20) as client:
        resp = await client.get(f"{GMAIL_BASE}/users/me/messages/{msg_id}", headers=headers, params=params)
    if resp.status_code != 200:
        print(f"[{now.isoformat()}] gmail get failed for {msg_id} (HTTP {resp.status_code}): {resp.text[:300]}")
        return None
    data = resp.json()
    hdrs = {h["name"]: h["value"] for h in data.get("payload", {}).get("headers", [])}
    return {
        "id": data.get("id"),
        "thread_id": data.get("threadId"),
        "subject": hdrs.get("Subject", "(no subject)"),
        "from": hdrs.get("From", "(unknown sender)"),
        "snippet": data.get("snippet", ""),
    }


def _is_worth_interrupting(client: anthropic.Anthropic, meta: dict) -> bool:
    prompt = (
        "An email just arrived. Decide if it is genuinely worth interrupting "
        "the recipient RIGHT NOW with a push notification, versus something "
        "that can wait until they next check their inbox normally.\n\n"
        "Say YES only for things like: a real person needing a timely reply, "
        "a meeting/appointment change, something time-sensitive or urgent, "
        "a genuinely important personal or business matter.\n"
        "Say NO for: newsletters, marketing, automated notifications, "
        "routine receipts/confirmations, spam, anything not time-sensitive.\n\n"
        f"From: {meta['from']}\n"
        f"Subject: {meta['subject']}\n"
        f"Preview: {meta['snippet']}\n\n"
        "Reply with exactly one word: YES or NO."
    )
    resp = client.messages.create(
        model=CLASSIFY_MODEL,
        max_tokens=5,
        messages=[{"role": "user", "content": prompt}],
    )
    answer = "".join(b.text for b in resp.content if hasattr(b, "text")).strip().upper()
    return answer.startswith("YES")


async def main() -> None:
    now = datetime.now(timezone.utc)

    u = _load_users()
    admin = (u or {}).get("admin")
    subscription = (admin or {}).get("push_subscription")
    if not subscription:
        print(f"[{now.isoformat()}] no push subscription registered — skipping")
        return

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print(f"[{now.isoformat()}] ANTHROPIC_API_KEY not set — skipping")
        return

    token = await goauth.get_access_token(ADMIN_EMAIL)
    if not token:
        print(f"[{now.isoformat()}] no Google account connected for {ADMIN_EMAIL} — skipping")
        return
    headers = {"Authorization": f"Bearer {token}"}

    ids = await _fetch_unread_ids(headers, now)
    if not ids:
        return

    state = _prune_state(_load_state(), now)
    new_ids = [i for i in ids if i not in state]
    if not new_ids:
        return

    client = anthropic.Anthropic(api_key=api_key)
    changed = False

    for msg_id in new_ids:
        meta = await _fetch_message_meta(headers, msg_id, now)
        if not meta:
            continue  # don't mark as seen — retry next run
        state[msg_id] = now.isoformat()
        changed = True

        try:
            worth_it = _is_worth_interrupting(client, meta)
        except Exception as exc:
            print(f"[{now.isoformat()}] classification failed for {msg_id}: {exc}")
            continue

        if not worth_it:
            continue

        thread_id = meta["thread_id"] or msg_id
        result = send_push(
            subscription,
            title=meta["subject"],
            body=f"{meta['from']} — {meta['snippet'][:120]}",
            url=f"https://mail.google.com/mail/u/0/#inbox/{thread_id}",
        )
        if result.ok:
            print(f"[{now.isoformat()}] notified: {meta['subject']!r} from {meta['from']!r}")
        elif result.gone:
            print(f"[{now.isoformat()}] push subscription gone — clearing it: {result.error}")
            if admin is not None:
                admin.pop("push_subscription", None)
                USERS_FILE.write_text(json.dumps(u, indent=2), encoding="utf-8")
            break
        else:
            print(f"[{now.isoformat()}] push failed for {msg_id}: {result.error}")

    if changed:
        _save_state(state)


if __name__ == "__main__":
    asyncio.run(main())
