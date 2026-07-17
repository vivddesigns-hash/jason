"""In-process MCP server bridging Jason to D-Major HQ.

HQ (https://industry-33.emergent.host) is itself a natural-language agent that
holds the Gmail / Calendar / Contacts / ClickUp credentials server-side. Rather
than re-do Google OAuth in Jason, we expose HQ's REST surface as three MCP
tools:

  - hq_agent(message)            -> POST /api/agent          (do anything HQ can)
  - hq_confirm(action_id, ...)   -> POST /api/agent/confirm  (the approval gate)
  - hq_push_document(...)        -> POST /api/documents       (document library)

Auth is HQ's API key (X-API-Key). Set HQ_API_KEY in the environment; nothing is
hardcoded. If the key is absent the tools return a clear, actionable error.
"""

from __future__ import annotations

import json
import os
from typing import Any

import httpx

from claude_agent_sdk import create_sdk_mcp_server, tool

HQ_URL = os.environ.get("HQ_API_URL", "https://industry-33.emergent.host").rstrip("/")
TIMEOUT = float(os.environ.get("HQ_TIMEOUT", "45"))


def _key() -> str | None:
    return os.environ.get("HQ_API_KEY") or None


def _text(s: str) -> dict[str, Any]:
    return {"content": [{"type": "text", "text": s}]}


def _no_key() -> dict[str, Any]:
    return _text(
        "HQ is not configured: HQ_API_KEY is not set in the environment. "
        "Ask Dwight to add HQ_API_KEY (the dmajor-hq api_key, format hq_live_...) "
        "to the .env file and restart. I can't send it myself."
    )


async def _post(path: str, payload: dict) -> dict[str, Any]:
    key = _key()
    if not key:
        return _no_key()
    headers = {"X-API-Key": key, "Content-Type": "application/json"}
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            resp = await client.post(f"{HQ_URL}{path}", headers=headers, json=payload)
    except Exception as exc:  # network / timeout
        return _text(f"HQ request to {path} failed: {type(exc).__name__}: {exc}")

    body = resp.text
    try:
        data = resp.json()
        body = json.dumps(data, indent=2)
    except Exception:
        pass
    prefix = "" if resp.status_code < 300 else f"[HTTP {resp.status_code}] "
    return _text(f"{prefix}{body}")


@tool(
    "hq_agent",
    "Send a natural-language instruction to the D-Major HQ agent. HQ can send "
    "email from connected business accounts (e.g. support@ashlanclinic.com), "
    "read/manage Google Calendar, look up Contacts, and manage ClickUp — all "
    "using HQ's own server-side credentials. Returns HQ's response, including an "
    "`actions` array. If an action has needs_confirmation=true / status=pending, "
    "extract its `id` and call hq_confirm to approve it. Use this for anything "
    "involving Gmail/Calendar/ClickUp on a business account.",
    {"message": str},
)
async def hq_agent(args: dict) -> dict[str, Any]:
    message = (args.get("message") or "").strip()
    if not message:
        return _text("hq_agent needs a `message` (the instruction for HQ).")
    return await _post("/api/agent", {"message": message})


@tool(
    "hq_confirm",
    "Confirm (or reject) a pending HQ agent action that is holding for approval. "
    "Pass the action_id from a prior hq_agent response's actions array. Set "
    "approved=true to execute it, false to cancel. Only confirm an outbound "
    "action (like send_email) after the user has explicitly approved it.",
    {"action_id": str, "approved": bool},
)
async def hq_confirm(args: dict) -> dict[str, Any]:
    action_id = (args.get("action_id") or "").strip()
    if not action_id:
        return _text("hq_confirm needs an `action_id` from a prior hq_agent response.")
    approved = bool(args.get("approved", True))
    return await _post("/api/agent/confirm", {"action_id": action_id, "approved": approved})


@tool(
    "hq_push_document",
    "File a document into HQ's document library (the system of record). Give a "
    "title, the content, and a collection (folder) — known collections: "
    "'Projects', 'Ashlan Clinic', 'Brand & Strategy', 'System'; an unknown name "
    "creates a new collection. tags is a comma-separated string (optional). Use "
    "this to store research, specs, guides, or notes in HQ instead of leaving "
    "them in your workspace.",
    {"title": str, "content": str, "collection": str, "tags": str},
)
async def hq_push_document(args: dict) -> dict[str, Any]:
    title = (args.get("title") or "").strip()
    content = args.get("content") or ""
    if not title or not content:
        return _text("hq_push_document needs a `title` and `content`.")
    collection = (args.get("collection") or "Projects").strip()
    raw_tags = args.get("tags") or ""
    tags = [t.strip() for t in raw_tags.split(",") if t.strip()]
    return await _post(
        "/api/documents",
        {"title": title, "collection": collection, "tags": tags, "content": content},
    )


hq_server = create_sdk_mcp_server(
    name="hq",
    version="1.0.0",
    tools=[hq_agent, hq_confirm, hq_push_document],
)

# Tool names the SDK exposes for this server (for allowed_tools).
HQ_TOOL_NAMES = [
    "mcp__hq__hq_agent",
    "mcp__hq__hq_confirm",
    "mcp__hq__hq_push_document",
]
