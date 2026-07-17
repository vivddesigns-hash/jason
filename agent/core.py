"""Core agent runtime: drives the Claude Agent SDK.

Exposes `stream_chat(web_session_id, prompt)` — an async generator that yields
structured events (assistant text deltas, tool-use notices, done) for the web
layer to forward over SSE. Conversation continuity is handled by mapping each
browser session to a Claude Agent SDK session id and resuming it; the mapping
survives process restarts via a small JSON file, and the SDK persists the full
transcript to disk on its own.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import AsyncIterator

from claude_agent_sdk import (
    ClaudeAgentOptions,
    query,
)

from .persona import BASE, build_system_prompt
from .hq_mcp import HQ_TOOL_NAMES, hq_server
from .memory_tools import MEM_TOOL_NAMES, mem_server

MODEL = os.environ.get("JASON_MODEL", "claude-haiku-4-5-20251001")

# Extra directories the agent may read/write beyond the project dir. On a LOCAL
# Mac install, set JASON_EXTRA_DIRS to the Mac home (e.g. /Users/dwightjones) so
# Jason can work on your files. Empty on the cloud instance (server has no Mac).
EXTRA_DIRS = [d.strip() for d in os.environ.get("JASON_EXTRA_DIRS", "").split(",") if d.strip()]

# Built-in tools we grant. Memory + research + skills + light shell.
ALLOWED_TOOLS = [
    "Read",
    "Write",
    "Edit",
    "Glob",
    "Grep",
    "Bash",
    "WebSearch",
    "WebFetch",
    "TodoWrite",
] + HQ_TOOL_NAMES + MEM_TOOL_NAMES  # HQ bridge + memory (remember/recall)

# Guard the most destructive shell patterns even in bypass mode.
DISALLOWED_TOOLS = [
    "Bash(rm -rf /*)",
    "Bash(sudo *)",
]

_SESSIONS_FILE = BASE / ".sessions.json"


def _load_sessions() -> dict[str, str]:
    if _SESSIONS_FILE.exists():
        try:
            return json.loads(_SESSIONS_FILE.read_text())
        except Exception:
            return {}
    return {}


def _save_sessions(data: dict[str, str]) -> None:
    _SESSIONS_FILE.write_text(json.dumps(data, indent=2))


def _make_options(resume: str | None) -> ClaudeAgentOptions:
    return ClaudeAgentOptions(
        system_prompt=build_system_prompt(),  # fresh each turn (latest memory)
        model=MODEL,
        cwd=str(BASE),                         # so .claude/skills + memory/ resolve
        setting_sources=["project"],           # load .claude/skills from cwd
        skills="all",                          # enable all 55 ported skills
        allowed_tools=ALLOWED_TOOLS,
        disallowed_tools=DISALLOWED_TOOLS,
        permission_mode="bypassPermissions",   # headless: no human to approve
        add_dirs=EXTRA_DIRS,                    # local install: your Mac folders
        mcp_servers={"hq": hq_server, "mem": mem_server},  # HQ bridge + memory
        resume=resume,
    )


def _text_of(block) -> str | None:
    return getattr(block, "text", None)


def _tooluse_of(block):
    name = getattr(block, "name", None)
    if name is not None and hasattr(block, "input"):
        return name, getattr(block, "input", {})
    return None


async def stream_chat(web_session_id: str, prompt: str) -> AsyncIterator[dict]:
    """Yield events: {'type': 'text'|'tool'|'done'|'error', ...}."""
    sessions = _load_sessions()
    resume = sessions.get(web_session_id)
    options = _make_options(resume)

    try:
        async for message in query(prompt=prompt, options=options):
            # Assistant content: text + tool-use blocks
            content = getattr(message, "content", None)
            if content is not None and isinstance(content, list):
                for block in content:
                    text = _text_of(block)
                    if text:
                        yield {"type": "text", "text": text}
                        continue
                    tu = _tooluse_of(block)
                    if tu:
                        yield {"type": "tool", "name": tu[0]}

            # ResultMessage carries the session id to resume next turn
            sid = getattr(message, "session_id", None)
            subtype = getattr(message, "subtype", None)
            if sid and (subtype is not None or getattr(message, "result", None) is not None):
                sessions[web_session_id] = sid
                _save_sessions(sessions)
                yield {"type": "done", "session_id": sid}
    except Exception as exc:  # surface, don't crash the stream
        yield {"type": "error", "error": f"{type(exc).__name__}: {exc}"}
