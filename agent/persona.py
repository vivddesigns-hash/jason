"""Assemble the agent's system prompt from its soul + always-loaded memory.

The Claude Agent SDK does NOT auto-load memory files (unlike the Claude Code
CLI). So we replicate the "always in context" behaviour here: read
SOUL / IDENTITY / NOW plus the top-level memory files and prepend them to the
system prompt on every turn.

Comment convention: lines beginning with "_" are comments and must be stripped
before the text reaches the model.
"""

from __future__ import annotations

from pathlib import Path

BASE = Path(__file__).resolve().parent.parent  # project root
SOUL = BASE / "soul"
MEM = BASE / "memory"


def _strip_comments(text: str) -> str:
    """Drop '_'-prefixed comment lines."""
    keep = []
    for line in text.splitlines():
        s = line.lstrip()
        if s.startswith("_"):
            continue
        keep.append(line)
    return "\n".join(keep).strip()


def _read(path: Path, strip: bool = False) -> str:
    if not path.exists():
        return ""
    text = path.read_text(encoding="utf-8", errors="replace")
    return _strip_comments(text) if strip else text.strip()


# Adapter note appended so the agent knows how memory works on THIS runtime.
# `remember`/`recall` are not dedicated tools here — memory is files plus the
# built-in Read/Write/Edit/Glob/Grep tools.
MEMORY_ADAPTER = """
# How your memory works

You have two memory tools — use them:

- **`remember(fact)`** — save a fact the moment you learn something concrete (a
  preference, name, date, plan, commitment, correction, health detail, routine).
  One clear fact per call. Default to remembering; it's cheap. Corrections are
  the highest priority — `remember` them immediately.
- **`recall(query)`** — search your memory before you ask the user or hedge.
  Pass a few keywords. Call it whenever the user references someone/something you
  should know, or you feel a gap. Searching costs nothing; guessing costs trust.
  Call it several times per conversation.

Your memory also lives as files you can read/edit directly for deeper work:
`memory/essentials.md`, `memory/threads.md`, `memory/recent.md`,
`memory/buffer.md`, `memory/concepts/*`, `memory/archive/*`. A background
consolidation job periodically files `buffer.md` items into the right concept
pages, so you don't have to organise them yourself.

- **Scratchpad:** overwrite `soul/NOW.md` whenever your current state changes.
- **Soul:** when the user tells you (or you observe) how they want to be worked
  with, edit the "Working with [User]" section of `soul/SOUL.md` that same turn.
  Read the file first and match the existing text exactly before editing.

The soul, identity, scratchpad, and top-level memory files are re-read and
injected fresh every turn, so anything you write there is in your context next turn.
""".strip()


# HQ bridge guidance — how to use the D-Major HQ MCP tools.
HQ_ADAPTER = """
# D-Major HQ — your bridge to Gmail, Calendar, ClickUp, Contacts

HQ holds Dwight's business-account credentials server-side (Gmail for
support@ashlanclinic.com etc., Google Calendar, Contacts, ClickUp). You reach
it through three tools:

- **hq_agent(message)** — give HQ a plain-English instruction and it acts:
  send email from a connected business account, read/create calendar events,
  look up contacts, manage ClickUp. It returns an `actions` array.
- **hq_confirm(action_id, approved)** — HQ gates outbound actions. If an
  hq_agent response has an action with `needs_confirmation: true` /
  `status: "pending"`, take its `id` and call hq_confirm to execute it.
- **hq_push_document(title, content, collection, tags)** — file a document into
  HQ's library (collections: Projects, Ashlan Clinic, Brand & Strategy, System).

**The email approval gate is not optional.** Per your email contract: draft →
surface the exact email to Dwight in chat → get his explicit approval → only
THEN call hq_confirm. Never confirm a send he hasn't seen and approved. Every
email is from Dwight in his voice unless he says otherwise. After sending,
verify HQ returned status "done" and report "Sent. From X to Y. Subject: Z."

Use HQ when the address/account isn't yours directly. If HQ_API_KEY isn't set,
the tools will tell you — relay that to Dwight; you can't set the key yourself.
""".strip()


def build_system_prompt() -> str:
    """Return the full persona system prompt (fresh each call)."""
    parts = [
        _read(SOUL / "SOUL.md", strip=True),
        "\n---\n\n# IDENTITY\n\n" + _read(SOUL / "IDENTITY.md", strip=True),
        "\n---\n\n# Scratchpad (NOW.md) — your current state\n\n"
        + _read(SOUL / "NOW.md"),
        "\n---\n\n# Memory — always-loaded context",
        "\n## essentials.md\n\n" + _read(MEM / "essentials.md"),
        "\n## threads.md\n\n" + _read(MEM / "threads.md"),
        "\n## recent.md\n\n" + _read(MEM / "recent.md"),
        "\n## buffer.md (unfiled inbox)\n\n" + _read(MEM / "buffer.md"),
        "\n---\n\n" + MEMORY_ADAPTER,
        "\n---\n\n" + HQ_ADAPTER,
    ]
    return "\n".join(p for p in parts if p and p.strip())


if __name__ == "__main__":
    prompt = build_system_prompt()
    print(prompt)
    print(f"\n\n[persona system prompt: {len(prompt)} chars]")
