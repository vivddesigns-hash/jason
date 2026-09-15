"""Direct file operations on a customer's paired Mac — the FAST path for
simple file tasks (list/read/rename/move/create folder/write a new file),
completely bypassing JasonMax's screenshot-driven Computer Use loop. One
request/response round-trip per operation over the same paired-helper
WebSocket bridge, no vision model in the loop at all — this is why it's fast
where Computer Use is slow: a plain function call instead of
screenshot -> vision-model-guesses-a-click -> verify.

Still no delete, and no overwrite of an existing file/folder — the two
genuinely destructive operations, and the ones with no visual "did that
actually work" tell the way a misplaced Computer Use click at least has
(you'd see it on screen). create_folder/write_file (added 2026-07-25) fill a
real gap: routine "create this folder" / "save this file" requests used to
have no fast-path answer at all and fell through to Computer Use, which is
where several real reliability bugs got found the hard way (premature
"done" before a save actually completed, typing into a window that lost
focus mid-task). Every operation is checked against the account's allowed
file roots (enforced Electron-side, in main.js) before it runs, and logged
to a structured audit trail here — same discipline as JasonMax's Phase 1
safety work (audit trail before anything more powerful gets built on top of
it).

Admin-only for now, by deliberate choice — new and unproven, same phased-
rollout reasoning already applied to Computer Use's own safety work.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from claude_agent_sdk import create_sdk_mcp_server, tool

from . import computer_use_bridge as bridge
from .persona import DATA_DIR

AUDIT_LOG_DIR = DATA_DIR / "mac_files_logs"


def _text(s: str) -> dict[str, Any]:
    return {"content": [{"type": "text", "text": s}]}


def _safe_email(email: str) -> str:
    return email.replace("@", "_at_").replace(".", "_").replace("/", "_")


def _log(user_email: str, entry: dict) -> None:
    d = AUDIT_LOG_DIR / _safe_email(user_email)
    d.mkdir(parents=True, exist_ok=True)
    path = d / f"{time.strftime('%Y-%m')}.jsonl"
    entry["ts"] = time.time()
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


async def _run(user_email: str, action: str, params: dict) -> dict:
    try:
        result = await bridge.send_command(user_email, action, params, timeout=15.0)
    except (RuntimeError, TimeoutError) as exc:
        _log(user_email, {"action": action, "params": params, "error": str(exc)})
        raise
    _log(user_email, {"action": action, "params": params, "result": result})
    return result


def build_mac_files_server(user_email: str):
    """Fresh MCP server per turn, closing over the requesting account — same
    per-turn-factory pattern as JasonMax's computer_use server, so no shared
    state leaks across concurrent users."""

    @tool(
        "list_files",
        "List files and folders in a directory on the user's paired Mac. Fast "
        "— does not touch the mouse/keyboard/screen at all. Only works within "
        "the folders this Mac has granted access to; a path outside that "
        "returns a clear error, not a silent failure or made-up listing.",
        {"path": str},
    )
    async def list_files(args: dict) -> dict[str, Any]:
        path = (args.get("path") or "").strip()
        if not bridge.is_helper_connected(user_email):
            return _text("No paired Mac is currently connected.")
        try:
            result = await _run(user_email, "list_dir", {"path": path})
        except Exception as exc:
            return _text(f"Couldn't list that folder: {exc}")
        if result.get("error"):
            return _text(result["error"])
        entries = result.get("entries", [])
        if not entries:
            return _text(f"{path or '(home folder)'} is empty.")
        lines = [f"- {'[folder]' if e['is_dir'] else '[file]'} {e['name']}" for e in entries]
        return _text(f"Contents of {path or '(home folder)'}:\n" + "\n".join(lines))

    @tool(
        "read_file",
        "Read a plain text file's contents from the user's paired Mac. Fast, "
        "no GUI involved. Refuses files outside the allowed folders, refuses "
        "binary files, and refuses anything over 500KB with a clear message "
        "rather than returning garbage or a truncated silent partial read.",
        {"path": str},
    )
    async def read_file(args: dict) -> dict[str, Any]:
        path = (args.get("path") or "").strip()
        if not path:
            return _text("read_file needs a `path`.")
        if not bridge.is_helper_connected(user_email):
            return _text("No paired Mac is currently connected.")
        try:
            result = await _run(user_email, "read_file", {"path": path})
        except Exception as exc:
            return _text(f"Couldn't read that file: {exc}")
        if result.get("error"):
            return _text(result["error"])
        return _text(result.get("content", ""))

    @tool(
        "rename_file",
        "Rename a file or folder in place (same folder, new name) on the "
        "user's paired Mac. Fast, no GUI involved. Refuses paths outside the "
        "allowed folders, and refuses to overwrite an existing item at the "
        "destination name rather than silently replacing it.",
        {"path": str, "new_name": str},
    )
    async def rename_file(args: dict) -> dict[str, Any]:
        path = (args.get("path") or "").strip()
        new_name = (args.get("new_name") or "").strip()
        if not path or not new_name:
            return _text("rename_file needs both `path` and `new_name`.")
        if not bridge.is_helper_connected(user_email):
            return _text("No paired Mac is currently connected.")
        try:
            result = await _run(user_email, "rename_file", {"path": path, "new_name": new_name})
        except Exception as exc:
            return _text(f"Couldn't rename that: {exc}")
        if result.get("error"):
            return _text(result["error"])
        return _text(result.get("message", "Renamed."))

    @tool(
        "move_file",
        "Move a file or folder to a different folder on the user's paired "
        "Mac, optionally renaming it in the same step. Fast, no GUI involved. "
        "Refuses paths outside the allowed folders on either end, and refuses "
        "to overwrite an existing item at the destination rather than "
        "silently replacing it.",
        {"path": str, "destination_dir": str, "new_name": str},
    )
    async def move_file(args: dict) -> dict[str, Any]:
        path = (args.get("path") or "").strip()
        destination_dir = (args.get("destination_dir") or "").strip()
        new_name = (args.get("new_name") or "").strip()
        if not path or not destination_dir:
            return _text("move_file needs both `path` and `destination_dir`.")
        if not bridge.is_helper_connected(user_email):
            return _text("No paired Mac is currently connected.")
        try:
            result = await _run(
                user_email, "move_file",
                {"path": path, "destination_dir": destination_dir, "new_name": new_name},
            )
        except Exception as exc:
            return _text(f"Couldn't move that: {exc}")
        if result.get("error"):
            return _text(result["error"])
        return _text(result.get("message", "Moved."))

    @tool(
        "create_folder",
        "Create a new folder on the user's paired Mac. Fast, no GUI involved. "
        "Refuses paths outside the allowed folders, and refuses if something "
        "already exists at that path rather than silently doing nothing. "
        "Creates any missing parent folders too (like `mkdir -p`).",
        {"path": str},
    )
    async def create_folder(args: dict) -> dict[str, Any]:
        path = (args.get("path") or "").strip()
        if not path:
            return _text("create_folder needs a `path`.")
        if not bridge.is_helper_connected(user_email):
            return _text("No paired Mac is currently connected.")
        try:
            result = await _run(user_email, "create_folder", {"path": path})
        except Exception as exc:
            return _text(f"Couldn't create that folder: {exc}")
        if result.get("error"):
            return _text(result["error"])
        return _text(result.get("message", "Created."))

    @tool(
        "write_file",
        "Write a NEW plain-text file on the user's paired Mac (e.g. an HTML "
        "mockup, a note, a config file). Fast, no GUI involved, no screenshot "
        "or vision model needed — use this instead of computer_use_task for "
        "any file-creation task. Refuses paths outside the allowed folders, "
        "refuses anything over 500KB, and — like every other tool here — "
        "refuses to overwrite an existing file rather than silently replacing "
        "it (use a different name, or move/rename the old one first). Creates "
        "any missing parent folders automatically.",
        {"path": str, "content": str},
    )
    async def write_file(args: dict) -> dict[str, Any]:
        path = (args.get("path") or "").strip()
        content = args.get("content") or ""
        if not path:
            return _text("write_file needs a `path`.")
        if not bridge.is_helper_connected(user_email):
            return _text("No paired Mac is currently connected.")
        try:
            result = await _run(user_email, "write_file", {"path": path, "content": content})
        except Exception as exc:
            return _text(f"Couldn't write that file: {exc}")
        if result.get("error"):
            return _text(result["error"])
        return _text(result.get("message", "Written."))

    @tool(
        "get_file_info",
        "Get a file or folder's REAL creation date, last-modified date, and "
        "size on the user's paired Mac. Fast, no GUI involved. Use this "
        "before renaming anything into a date-based naming convention — "
        "never guess a date or use today's date for an existing file; call "
        "this and use the returned creation date instead. Works on both "
        "files and folders. Refuses paths outside the allowed folders.",
        {"path": str},
    )
    async def get_file_info(args: dict) -> dict[str, Any]:
        path = (args.get("path") or "").strip()
        if not path:
            return _text("get_file_info needs a `path`.")
        if not bridge.is_helper_connected(user_email):
            return _text("No paired Mac is currently connected.")
        try:
            result = await _run(user_email, "get_file_info", {"path": path})
        except Exception as exc:
            return _text(f"Couldn't get info for that path: {exc}")
        if result.get("error"):
            return _text(result["error"])
        kind = "folder" if result.get("is_dir") else "file"
        size = result.get("size_bytes")
        size_line = f"\nSize: {size:,} bytes" if size is not None else ""
        return _text(
            f"{path} ({kind})\n"
            f"Created: {result.get('created_date')} (full: {result.get('created_at')})\n"
            f"Modified: {result.get('modified_date')} (full: {result.get('modified_at')})"
            f"{size_line}"
        )

    server = create_sdk_mcp_server(
        name="mac_files", version="1.0.0",
        tools=[list_files, read_file, rename_file, move_file, create_folder, write_file, get_file_info],
    )
    return server


MAC_FILES_TOOL_NAMES = [
    "mcp__mac_files__list_files",
    "mcp__mac_files__read_file",
    "mcp__mac_files__rename_file",
    "mcp__mac_files__create_folder",
    "mcp__mac_files__write_file",
    "mcp__mac_files__move_file",
    "mcp__mac_files__get_file_info",
]
