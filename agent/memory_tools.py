"""In-process MCP tools for Jason's memory: `remember` and `recall`.

Restores the first-class memory verbs (previously the agent used raw file tools).
`remember` appends a timestamped fact to the buffer + the day's archive;
consolidation later files buffer items into concept pages. `recall` searches
across the memory files and returns matching lines.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from claude_agent_sdk import create_sdk_mcp_server, tool

from .persona import BASE

MEM = BASE / "memory"


def _text(s: str) -> dict[str, Any]:
    return {"content": [{"type": "text", "text": s}]}


@tool(
    "remember",
    "Save a fact to long-term memory. Use this the moment you learn something "
    "concrete about Dwight or his work — a preference, name, date, plan, "
    "commitment, correction, health detail, or state. One clear fact per call. "
    "It is appended to your buffer and to today's archive; consolidation later "
    "files it into the right concept page. Remembering is cheap — err on the "
    "side of remembering. Corrections are the highest priority.",
    {"fact": str},
)
async def remember(args: dict) -> dict[str, Any]:
    fact = (args.get("fact") or "").strip()
    if not fact:
        return _text("remember needs a `fact`.")
    now = datetime.now()
    line = f"- [{now.strftime('%Y-%m-%d %H:%M')}] {fact}\n"
    try:
        MEM.mkdir(parents=True, exist_ok=True)
        with open(MEM / "buffer.md", "a", encoding="utf-8") as f:
            f.write(line)
        adir = MEM / "archive"
        adir.mkdir(parents=True, exist_ok=True)
        with open(adir / f"{now.strftime('%Y-%m-%d')}.md", "a", encoding="utf-8") as f:
            f.write(line)
    except Exception as exc:
        return _text(f"couldn't save to memory: {exc}")
    return _text(f"Remembered: {fact}")


@tool(
    "recall",
    "Search your memory before asking Dwight or hedging. Pass a few keywords "
    "(a name, topic, or project). Returns matching lines from essentials, "
    "threads, recent notes, the buffer, concept pages, and the archive. Call it "
    "whenever Dwight references someone or something you should already know, or "
    "when you feel a gap. Searching costs nothing; guessing costs trust.",
    {"query": str},
)
async def recall(args: dict) -> dict[str, Any]:
    q = (args.get("query") or "").strip()
    if not q:
        return _text("recall needs a `query`.")
    terms = [t.lower() for t in q.split() if t]

    files = []
    for name in ("essentials.md", "threads.md", "recent.md", "buffer.md", "core-pages.md"):
        p = MEM / name
        if p.exists():
            files.append(p)
    for sub in ("concepts", "archive"):
        d = MEM / sub
        if d.exists():
            files += sorted(d.glob("*.md"))

    hits: list[str] = []
    for p in files:
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        for line in text.splitlines():
            line = line.strip()
            if not line or line.startswith("#") or line.startswith("_"):
                continue
            ll = line.lower()
            if all(t in ll for t in terms):
                label = p.name if p.parent == MEM else f"{p.parent.name}/{p.name}"
                hits.append(f"[{label}] {line[:400]}")
                if len(hits) >= 50:
                    break
        if len(hits) >= 50:
            break

    if not hits:
        return _text(f"No memory found for '{q}'.")
    return _text(f"Recall for '{q}' ({len(hits)} match(es)):\n\n" + "\n".join(hits))


mem_server = create_sdk_mcp_server(name="mem", version="1.0.0", tools=[remember, recall])
MEM_TOOL_NAMES = ["mcp__mem__remember", "mcp__mem__recall"]
