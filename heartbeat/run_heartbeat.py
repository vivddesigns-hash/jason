"""Daily heartbeat: runs Jason's HEARTBEAT.md routine as a one-shot agent turn.

Wire this to cron on the host, e.g.:
    0 8 * * *  cd /path/to/myagent && ./run.sh heartbeat >> heartbeat.log 2>&1

It runs the agent once with the heartbeat checklist as the prompt, so the agent
checks NOW.md, follows up on threads, and journals — the same "stay present
between conversations" behaviour.
"""

from __future__ import annotations

import asyncio

from agent.core import stream_chat
from agent.persona import SOUL, _read


async def main() -> None:
    checklist = _read(SOUL / "HEARTBEAT.md", strip=True)
    prompt = (
        "This is your periodic heartbeat (running in the background, the user is "
        "not watching). Work through your heartbeat checklist below. Update "
        "soul/NOW.md and your memory as needed. Keep any output brief.\n\n"
        + checklist
    )
    async for event in stream_chat("heartbeat", prompt):
        if event["type"] == "text":
            print(event["text"], end="", flush=True)
        elif event["type"] == "tool":
            print(f"\n[· {event['name']}]", flush=True)
        elif event["type"] == "error":
            print(f"\n[error] {event['error']}", flush=True)
    print()


if __name__ == "__main__":
    asyncio.run(main())
