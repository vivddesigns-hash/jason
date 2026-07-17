"""Background memory consolidation.

Runs Jason for one turn with a consolidation instruction: file each item in
memory/buffer.md into the most relevant memory/concepts/ page, then clear the
buffer. Scheduled (e.g. daily) on the always-on cloud instance; also runnable
manually via `./run.sh consolidate`.
"""

from __future__ import annotations

import asyncio

from agent.core import stream_chat
from agent.persona import MEM

PROMPT = """This is an automatic memory-consolidation run in the background. The
user is NOT watching — do not address them; keep any output to a couple of lines.

Read memory/buffer.md. For each fact in it:
1. Append it (concise, one line) to the single most relevant page in
   memory/concepts/ — match by topic (a person, health, preferences, schedule,
   a project name, a business, etc.). If nothing fits, create a new,
   topically-named memory/concepts/<topic>.md.
2. Merge obvious duplicates and keep the pages tidy.

When every buffer item has been filed, empty memory/buffer.md (leave just the
line "# Buffer"). Do NOT touch memory/archive/ — that is the permanent record.
Use your file tools directly. Report one line: how many items you filed."""


async def main() -> None:
    buf = MEM / "buffer.md"
    if buf.exists():
        body = "\n".join(
            l for l in buf.read_text(encoding="utf-8", errors="replace").splitlines()
            if l.strip() and not l.strip().startswith("#")
        )
        if not body.strip():
            print("buffer empty — nothing to consolidate")
            return
    async for event in stream_chat("consolidate", PROMPT):
        if event["type"] == "text":
            print(event["text"], end="", flush=True)
        elif event["type"] == "error":
            print(f"\n[error] {event['error']}", flush=True)
    print()


if __name__ == "__main__":
    asyncio.run(main())
