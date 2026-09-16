"""Direct Google Calendar + Gmail tools — one per connected account (see
agent/google_oauth.py). Built specifically to fix what the HQ-proxied path
couldn't do: set a real, verifiable calendar reminder. Every write tool here
returns the ACTUAL field Google sent back, never just "I asked for X" — see
soul/SOUL.md's Aug 15 2026 entry on why that distinction matters.
"""

from __future__ import annotations

import asyncio
import base64
import mimetypes
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Any

import httpx
from claude_agent_sdk import create_sdk_mcp_server, tool

from . import google_oauth as goauth

CAL_BASE = "https://www.googleapis.com/calendar/v3"
GMAIL_BASE = "https://www.googleapis.com/gmail/v1"
DRIVE_BASE = "https://www.googleapis.com/drive/v3"
DRIVE_UPLOAD_BASE = "https://www.googleapis.com/upload/drive/v3"
DRIVE_FOLDER_MIME = "application/vnd.google-apps.folder"


def _text(s: str) -> dict[str, Any]:
    return {"content": [{"type": "text", "text": s}]}


async def _auth_headers(account_email: str) -> dict[str, str] | None:
    token = await goauth.get_access_token(account_email)
    if not token:
        return None
    return {"Authorization": f"Bearer {token}"}


def _no_account(account_email: str) -> dict[str, Any]:
    connected = [a["email"] for a in goauth.list_connected_accounts()]
    if connected:
        hint = "Connected accounts: " + ", ".join(connected) + "."
    else:
        hint = "No Google accounts are connected yet — the operator needs to connect one from Settings."
    return _text(f"'{account_email}' isn't connected. {hint}")


@tool(
    "list_connected_google_accounts",
    "List which Google accounts are currently connected directly to Jason "
    "(email + when connected). Call this first if you're not sure which "
    "account to use, or the operator hasn't specified one.",
    {},
)
async def list_connected_google_accounts(args: dict) -> dict[str, Any]:
    accounts = goauth.list_connected_accounts()
    if not accounts:
        return _text("No Google accounts connected yet. The operator can connect one from Settings.")
    lines = [f"  - {a['email']}" for a in accounts]
    return _text("Connected Google accounts:\n" + "\n".join(lines))


@tool(
    "list_calendar_events",
    "List calendar events for a connected account within a time range.",
    {"account_email": str, "time_min": str, "time_max": str},
)
async def list_calendar_events(args: dict) -> dict[str, Any]:
    account_email = (args.get("account_email") or "").strip()
    headers = await _auth_headers(account_email)
    if not headers:
        return _no_account(account_email)
    params = {
        "timeMin": args.get("time_min"), "timeMax": args.get("time_max"),
        "singleEvents": "true", "orderBy": "startTime",
    }
    async with httpx.AsyncClient(timeout=20) as client:
        resp = await client.get(f"{CAL_BASE}/calendars/primary/events", headers=headers, params=params)
    if resp.status_code != 200:
        return _text(f"Calendar list failed (HTTP {resp.status_code}): {resp.text[:300]}")
    items = resp.json().get("items", [])
    if not items:
        return _text("No events in that range.")
    lines = []
    for ev in items:
        start = (ev.get("start") or {}).get("dateTime") or (ev.get("start") or {}).get("date")
        lines.append(f"  - [{ev['id']}] {ev.get('summary', '(no title)')} — {start}")
    return _text("\n".join(lines))


@tool(
    "create_calendar_event",
    "Create a calendar event on a connected account, WITH a real reminder "
    "attached (never rely on the account's default reminder — always set "
    "one explicitly here). `start`/`end` must be ISO-8601 WITH a numeric UTC "
    "offset you compute yourself from today's date (e.g. "
    "'2026-08-20T14:30:00+01:00') — never a timezone abbreviation like 'BST', "
    "that gets misread as UTC. `reminder_minutes_before`: 0 = fires exactly "
    "at the start time (the usual choice for a 'remind me' request), or a "
    "positive number of minutes ahead of it. Returns the REAL reminders "
    "field Google sent back — report that, not what you asked for.",
    {"account_email": str, "title": str, "start": str, "end": str, "reminder_minutes_before": int},
)
async def create_calendar_event(args: dict) -> dict[str, Any]:
    account_email = (args.get("account_email") or "").strip()
    headers = await _auth_headers(account_email)
    if not headers:
        return _no_account(account_email)
    minutes = args.get("reminder_minutes_before")
    if minutes is None:
        return _text("create_calendar_event needs `reminder_minutes_before` — every event Jason creates must have a reminder.")
    body = {
        "summary": args.get("title"),
        "start": {"dateTime": args.get("start")},
        "end": {"dateTime": args.get("end")},
        "reminders": {"useDefault": False, "overrides": [{"method": "popup", "minutes": int(minutes)}]},
    }
    async with httpx.AsyncClient(timeout=20) as client:
        resp = await client.post(f"{CAL_BASE}/calendars/primary/events", headers=headers, json=body)
    if resp.status_code not in (200, 201):
        return _text(f"Event creation failed (HTTP {resp.status_code}): {resp.text[:300]}")
    ev = resp.json()
    return _text(
        f"Created \"{ev.get('summary')}\" (id={ev['id']})\n"
        f"start: {ev.get('start', {}).get('dateTime')}\n"
        f"reminders (verified from Google's actual response, not assumed): {ev.get('reminders')}\n"
        f"link: {ev.get('htmlLink')}"
    )


@tool(
    "get_calendar_event",
    "Fetch full raw details of one calendar event by id, including its real "
    "reminders field — use this to verify a reminder is actually attached, "
    "not just trust what create_calendar_event's request asked for.",
    {"account_email": str, "event_id": str},
)
async def get_calendar_event(args: dict) -> dict[str, Any]:
    account_email = (args.get("account_email") or "").strip()
    headers = await _auth_headers(account_email)
    if not headers:
        return _no_account(account_email)
    event_id = (args.get("event_id") or "").strip()
    async with httpx.AsyncClient(timeout=20) as client:
        resp = await client.get(f"{CAL_BASE}/calendars/primary/events/{event_id}", headers=headers)
    if resp.status_code != 200:
        return _text(f"Event fetch failed (HTTP {resp.status_code}): {resp.text[:300]}")
    return _text(resp.text)


@tool(
    "delete_calendar_event",
    "Permanently delete a calendar event by id from a connected account.",
    {"account_email": str, "event_id": str},
)
async def delete_calendar_event(args: dict) -> dict[str, Any]:
    account_email = (args.get("account_email") or "").strip()
    headers = await _auth_headers(account_email)
    if not headers:
        return _no_account(account_email)
    event_id = (args.get("event_id") or "").strip()
    async with httpx.AsyncClient(timeout=20) as client:
        resp = await client.delete(f"{CAL_BASE}/calendars/primary/events/{event_id}", headers=headers)
    if resp.status_code not in (200, 204):
        return _text(f"Event deletion failed (HTTP {resp.status_code}): {resp.text[:300]}")
    return _text(f"Deleted event {event_id}.")


@tool(
    "list_gmail_messages",
    "List/search recent Gmail messages on a connected account. `query` uses "
    "normal Gmail search syntax (e.g. 'from:someone@example.com is:unread'), "
    "optional — omit for the most recent messages. Returns sender, subject, "
    "and a short preview for each — enough to triage without opening every "
    "message individually. Only call get_gmail_message for ones that are "
    "actually ambiguous from this alone; opening every result one by one is "
    "slow and usually unnecessary.",
    {"account_email": str, "query": str, "max_results": int},
)
async def list_gmail_messages(args: dict) -> dict[str, Any]:
    account_email = (args.get("account_email") or "").strip()
    headers = await _auth_headers(account_email)
    if not headers:
        return _no_account(account_email)
    params = {"maxResults": args.get("max_results") or 10}
    if args.get("query"):
        params["q"] = args["query"]
    async with httpx.AsyncClient(timeout=20) as client:
        resp = await client.get(f"{GMAIL_BASE}/users/me/messages", headers=headers, params=params)
    if resp.status_code != 200:
        return _text(f"Gmail list failed (HTTP {resp.status_code}): {resp.text[:300]}")
    ids = [m["id"] for m in resp.json().get("messages", [])]
    if not ids:
        return _text("No matching messages.")

    # One cheap metadata-only fetch per id, in parallel — sender/subject/
    # snippet without the full body, so a whole inbox can be triaged from
    # this one tool response instead of one round-trip per message.
    async def _meta(client: httpx.AsyncClient, msg_id: str) -> dict[str, Any]:
        mparams = {"format": "metadata", "metadataHeaders": ["Subject", "From"]}
        r = await client.get(f"{GMAIL_BASE}/users/me/messages/{msg_id}", headers=headers, params=mparams)
        if r.status_code != 200:
            return {"id": msg_id, "error": True}
        d = r.json()
        h = {x["name"]: x["value"] for x in d.get("payload", {}).get("headers", [])}
        return {
            "id": msg_id,
            "thread_id": d.get("threadId"),
            "from": h.get("From", "(unknown sender)"),
            "subject": h.get("Subject", "(no subject)"),
            "snippet": d.get("snippet", ""),
        }

    async with httpx.AsyncClient(timeout=20) as client:
        results = await asyncio.gather(*(_meta(client, i) for i in ids))

    lines = []
    for m in results:
        if m.get("error"):
            lines.append(f"  - [{m['id']}] (couldn't fetch details)")
            continue
        lines.append(f"  - [{m['id']}] From: {m['from']} | Subject: {m['subject']} | {m['snippet'][:100]}")
    return _text(
        f"{len(results)} message(s):\n" + "\n".join(lines)
        + "\n\nUse get_gmail_message by id only for ones this preview doesn't already answer."
    )


def _decode_b64url(data: str) -> str:
    padded = data + "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(padded).decode("utf-8", errors="replace")


def _strip_html(html: str) -> str:
    import re
    text = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", html, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<[^>]+>", "", text)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def _extract_body(payload: dict) -> tuple[str, list[str]]:
    """Walk a Gmail message payload (recursively, multipart-aware) for the
    real body text — prefer text/plain, fall back to text/html stripped of
    tags. Returns (body_text, attachment_filenames) so callers can at least
    flag that attachments exist even though we don't fetch their content."""
    plain, html, attachments = None, None, []

    def walk(part: dict) -> None:
        nonlocal plain, html
        mime = part.get("mimeType", "")
        filename = part.get("filename")
        body = part.get("body", {})
        if filename:
            attachments.append(filename)
        data = body.get("data")
        if data and mime == "text/plain" and plain is None:
            plain = _decode_b64url(data)
        elif data and mime == "text/html" and html is None:
            html = _decode_b64url(data)
        for sub in part.get("parts") or []:
            walk(sub)

    walk(payload)
    if plain:
        return plain, attachments
    if html:
        return _strip_html(html), attachments
    return "(no readable body — likely attachment-only or an unsupported format)", attachments


@tool(
    "get_gmail_message",
    "Fetch one Gmail message's FULL body (not just a snippet) by id, plus "
    "From/Subject/Date and a list of attachment filenames if any (attachment "
    "contents themselves aren't fetched).",
    {"account_email": str, "message_id": str},
)
async def get_gmail_message(args: dict) -> dict[str, Any]:
    account_email = (args.get("account_email") or "").strip()
    headers = await _auth_headers(account_email)
    if not headers:
        return _no_account(account_email)
    message_id = (args.get("message_id") or "").strip()
    async with httpx.AsyncClient(timeout=20) as client:
        resp = await client.get(f"{GMAIL_BASE}/users/me/messages/{message_id}", headers=headers, params={"format": "full"})
    if resp.status_code != 200:
        return _text(f"Gmail fetch failed (HTTP {resp.status_code}): {resp.text[:300]}")
    data = resp.json()
    payload = data.get("payload", {})
    headers_list = {h["name"]: h["value"] for h in payload.get("headers", [])}
    body, attachments = _extract_body(payload)
    out = (
        f"From: {headers_list.get('From', '?')}\n"
        f"Subject: {headers_list.get('Subject', '?')}\n"
        f"Date: {headers_list.get('Date', '?')}\n"
    )
    if attachments:
        out += f"Attachments (not fetched): {', '.join(attachments)}\n"
    out += f"\n{body}"
    return _text(out)


def _build_mime(to: str, subject: str, body: str, attachment_paths: str | None) -> bytes:
    """Build a MIME message, plain text if no attachments, multipart if any
    `attachment_paths` are given (newline- or comma-separated absolute paths —
    per Jason's file bridge, that's where an operator-uploaded file lands:
    /opt/myagent/uploads/<chat-id>/...). Missing/unreadable paths are skipped,
    not fatal — the send/draft still goes out with whatever attached cleanly."""
    paths = [p.strip() for p in (attachment_paths or "").replace(",", "\n").splitlines() if p.strip()]
    if not paths:
        mime = MIMEText(body or "")
        mime["to"] = to
        mime["subject"] = subject or ""
        return mime.as_bytes()

    mime = MIMEMultipart()
    mime["to"] = to
    mime["subject"] = subject or ""
    mime.attach(MIMEText(body or ""))
    for p in paths:
        f = Path(p)
        if not f.is_file():
            continue
        ctype, _ = mimetypes.guess_type(str(f))
        maintype, subtype = (ctype.split("/", 1) if ctype else ("application", "octet-stream"))
        part = MIMEBase(maintype, subtype)
        part.set_payload(f.read_bytes())
        encoders.encode_base64(part)
        part.add_header("Content-Disposition", "attachment", filename=f.name)
        mime.attach(part)
    return mime.as_bytes()


def _skipped_attachments_note(attachment_paths: str | None) -> str:
    paths = [p.strip() for p in (attachment_paths or "").replace(",", "\n").splitlines() if p.strip()]
    missing = [p for p in paths if not Path(p).is_file()]
    if not missing:
        return ""
    return f"\n(Note: couldn't find and skipped: {', '.join(missing)})"


@tool(
    "send_gmail_message",
    "Send an email from a connected account. Same approval rules as "
    "everything else that sends on the operator's behalf: draft it, show the "
    "exact text, wait for explicit approval — never call this in the same "
    "turn as drafting. `attachment_paths` (optional): one or more absolute "
    "server file paths, comma- or newline-separated — e.g. a file the "
    "operator uploaded, which lands under /opt/myagent/uploads/<chat-id>/.",
    {"account_email": str, "to": str, "subject": str, "body": str, "attachment_paths": str},
)
async def send_gmail_message(args: dict) -> dict[str, Any]:
    account_email = (args.get("account_email") or "").strip()
    headers = await _auth_headers(account_email)
    if not headers:
        return _no_account(account_email)
    raw = base64.urlsafe_b64encode(
        _build_mime(args.get("to"), args.get("subject"), args.get("body"), args.get("attachment_paths"))
    ).decode()
    async with httpx.AsyncClient(timeout=20) as client:
        resp = await client.post(f"{GMAIL_BASE}/users/me/messages/send", headers=headers, json={"raw": raw})
    if resp.status_code not in (200, 202):
        return _text(f"Send failed (HTTP {resp.status_code}): {resp.text[:300]}")
    note = _skipped_attachments_note(args.get("attachment_paths"))
    return _text(f"Sent. To: {args.get('to')}. Subject: {args.get('subject')}.{note}")


@tool(
    "create_gmail_draft",
    "Create a real Gmail draft (saved, NOT sent) on a connected account — "
    "for when the operator wants to review, add attachments themselves in "
    "Gmail, or finish it later before sending. Same approval rules as "
    "sending: show the exact text before creating it. `attachment_paths` "
    "(optional): one or more absolute server file paths, comma- or "
    "newline-separated. Returns the draft id — use it later with "
    "send_gmail_draft to actually send exactly what's in the draft.",
    {"account_email": str, "to": str, "subject": str, "body": str, "attachment_paths": str},
)
async def create_gmail_draft(args: dict) -> dict[str, Any]:
    account_email = (args.get("account_email") or "").strip()
    headers = await _auth_headers(account_email)
    if not headers:
        return _no_account(account_email)
    raw = base64.urlsafe_b64encode(
        _build_mime(args.get("to"), args.get("subject"), args.get("body"), args.get("attachment_paths"))
    ).decode()
    async with httpx.AsyncClient(timeout=20) as client:
        resp = await client.post(f"{GMAIL_BASE}/users/me/drafts", headers=headers, json={"message": {"raw": raw}})
    if resp.status_code not in (200, 201):
        return _text(f"Draft creation failed (HTTP {resp.status_code}): {resp.text[:300]}")
    data = resp.json()
    note = _skipped_attachments_note(args.get("attachment_paths"))
    return _text(
        f"Draft saved (id={data.get('id')}). To: {args.get('to')}. Subject: {args.get('subject')}.{note}\n"
        "Visible now in Gmail's Drafts folder — the operator can open it there to add anything by hand."
    )


@tool(
    "send_gmail_draft",
    "Send an existing Gmail draft exactly as it currently stands (including "
    "any attachments the operator added by hand in Gmail after "
    "create_gmail_draft made it) — use this instead of re-typing the "
    "content into send_gmail_message once a draft exists. Same approval "
    "rule: confirm with the operator before calling this.",
    {"account_email": str, "draft_id": str},
)
async def send_gmail_draft(args: dict) -> dict[str, Any]:
    account_email = (args.get("account_email") or "").strip()
    headers = await _auth_headers(account_email)
    if not headers:
        return _no_account(account_email)
    draft_id = (args.get("draft_id") or "").strip()
    if not draft_id:
        return _text("send_gmail_draft needs a `draft_id` (from create_gmail_draft's response).")
    async with httpx.AsyncClient(timeout=20) as client:
        resp = await client.post(f"{GMAIL_BASE}/users/me/drafts/send", headers=headers, json={"id": draft_id})
    if resp.status_code not in (200, 202):
        return _text(f"Draft send failed (HTTP {resp.status_code}): {resp.text[:300]}")
    return _text(f"Draft {draft_id} sent.")


@tool(
    "list_drive_files",
    "List files/folders in a connected account's Google Drive. Omit "
    "`folder_id` to list what's in 'My Drive' root. `query` (optional) "
    "adds a raw Drive search query on top (e.g. \"name contains 'invoice'\").",
    {"account_email": str, "folder_id": str, "query": str},
)
async def list_drive_files(args: dict) -> dict[str, Any]:
    account_email = (args.get("account_email") or "").strip()
    headers = await _auth_headers(account_email)
    if not headers:
        return _no_account(account_email)
    parts = [f"'{(args.get('folder_id') or 'root').strip()}' in parents", "trashed = false"]
    if args.get("query"):
        parts.append(args["query"])
    params = {"q": " and ".join(parts), "fields": "files(id,name,mimeType,parents)"}
    async with httpx.AsyncClient(timeout=20) as client:
        resp = await client.get(f"{DRIVE_BASE}/files", headers=headers, params=params)
    if resp.status_code != 200:
        return _text(f"List failed (HTTP {resp.status_code}): {resp.text[:300]}")
    files = resp.json().get("files", [])
    if not files:
        return _text("No files/folders found.")
    lines = []
    for f in files:
        kind = "folder" if f.get("mimeType") == DRIVE_FOLDER_MIME else "file"
        lines.append(f"  - [{f['id']}] {f.get('name')} ({kind})")
    return _text("\n".join(lines))


@tool(
    "get_drive_file",
    "Fetch metadata for one Drive file/folder by id — name, type, and "
    "current parent folder id(s), so you know exactly where it lives "
    "before organizing it further.",
    {"account_email": str, "file_id": str},
)
async def get_drive_file(args: dict) -> dict[str, Any]:
    account_email = (args.get("account_email") or "").strip()
    headers = await _auth_headers(account_email)
    if not headers:
        return _no_account(account_email)
    file_id = (args.get("file_id") or "").strip()
    if not file_id:
        return _text("get_drive_file needs a `file_id`.")
    async with httpx.AsyncClient(timeout=20) as client:
        resp = await client.get(
            f"{DRIVE_BASE}/files/{file_id}", headers=headers,
            params={"fields": "id,name,mimeType,parents,webViewLink"},
        )
    if resp.status_code != 200:
        return _text(f"Fetch failed (HTTP {resp.status_code}): {resp.text[:300]}")
    f = resp.json()
    kind = "folder" if f.get("mimeType") == DRIVE_FOLDER_MIME else f.get("mimeType", "?")
    return _text(
        f"[{f['id']}] {f.get('name')}\ntype: {kind}\nparents: {f.get('parents')}\nlink: {f.get('webViewLink')}"
    )


@tool(
    "create_drive_folder",
    "Create a new folder in a connected account's Google Drive. Omit "
    "`parent_folder_id` to create it at the root of 'My Drive'. Returns "
    "the real created folder id.",
    {"account_email": str, "name": str, "parent_folder_id": str},
)
async def create_drive_folder(args: dict) -> dict[str, Any]:
    account_email = (args.get("account_email") or "").strip()
    headers = await _auth_headers(account_email)
    if not headers:
        return _no_account(account_email)
    name = (args.get("name") or "").strip()
    if not name:
        return _text("create_drive_folder needs a `name`.")
    body: dict[str, Any] = {"name": name, "mimeType": DRIVE_FOLDER_MIME}
    if args.get("parent_folder_id"):
        body["parents"] = [args["parent_folder_id"]]
    async with httpx.AsyncClient(timeout=20) as client:
        resp = await client.post(f"{DRIVE_BASE}/files", headers=headers, json=body)
    if resp.status_code not in (200, 201):
        return _text(f"Folder creation failed (HTTP {resp.status_code}): {resp.text[:300]}")
    f = resp.json()
    return _text(f"Created folder \"{f.get('name')}\" (id={f['id']}).")


@tool(
    "create_drive_file",
    "Create a new file with real text content in a connected account's "
    "Google Drive. `mime_type` defaults to plain text — use "
    "'application/vnd.google-apps.document' to create it as a real Google "
    "Doc instead of a .txt file. Omit `parent_folder_id` to create it at "
    "the root of 'My Drive'.",
    {"account_email": str, "name": str, "content": str, "parent_folder_id": str, "mime_type": str},
)
async def create_drive_file(args: dict) -> dict[str, Any]:
    account_email = (args.get("account_email") or "").strip()
    headers = await _auth_headers(account_email)
    if not headers:
        return _no_account(account_email)
    name = (args.get("name") or "").strip()
    content = args.get("content") or ""
    if not name:
        return _text("create_drive_file needs a `name`.")
    mime_type = args.get("mime_type") or "text/plain"
    is_google_native = mime_type.startswith("application/vnd.google-apps")

    body: dict[str, Any] = {"name": name}
    if args.get("parent_folder_id"):
        body["parents"] = [args["parent_folder_id"]]
    if is_google_native:
        body["mimeType"] = mime_type

    async with httpx.AsyncClient(timeout=20) as client:
        resp = await client.post(f"{DRIVE_BASE}/files", headers=headers, json=body)
        if resp.status_code not in (200, 201):
            return _text(f"File creation failed (HTTP {resp.status_code}): {resp.text[:300]}")
        file_id = resp.json()["id"]

        if content:
            # Converting to a Google Doc requires uploading as plain text and
            # letting Drive's import handle the conversion — uploading raw
            # bytes with the google-apps mimeType directly is rejected.
            upload_ctype = "text/plain" if is_google_native else mime_type
            resp2 = await client.patch(
                f"{DRIVE_UPLOAD_BASE}/files/{file_id}",
                headers={**headers, "Content-Type": upload_ctype},
                params={"uploadType": "media"},
                content=content.encode("utf-8"),
            )
            if resp2.status_code != 200:
                return _text(
                    f"File \"{name}\" created (id={file_id}) but content upload failed "
                    f"(HTTP {resp2.status_code}): {resp2.text[:300]}"
                )

    return _text(f"Created \"{name}\" (id={file_id}).")


@tool(
    "update_drive_file",
    "Rename and/or move (organize) an existing Drive file or folder. Pass "
    "`new_name` to rename, `new_parent_folder_id` to move it into a "
    "different folder — either or both, whatever you're changing. Moving "
    "correctly removes it from its current folder(s), it doesn't just add "
    "a second location.",
    {"account_email": str, "file_id": str, "new_name": str, "new_parent_folder_id": str},
)
async def update_drive_file(args: dict) -> dict[str, Any]:
    account_email = (args.get("account_email") or "").strip()
    headers = await _auth_headers(account_email)
    if not headers:
        return _no_account(account_email)
    file_id = (args.get("file_id") or "").strip()
    if not file_id:
        return _text("update_drive_file needs a `file_id`.")
    new_name = args.get("new_name")
    new_parent = args.get("new_parent_folder_id")
    if not new_name and not new_parent:
        return _text("update_drive_file needs `new_name` and/or `new_parent_folder_id`.")

    body: dict[str, Any] = {}
    if new_name:
        body["name"] = new_name
    params: dict[str, Any] = {"fields": "id,name,parents"}

    async with httpx.AsyncClient(timeout=20) as client:
        if new_parent:
            # Moving means adding the new parent AND removing the old
            # one(s) — Drive doesn't do this from a plain body replacement,
            # it needs addParents/removeParents query params (verified
            # against Google's own docs, Aug 31).
            current = await client.get(f"{DRIVE_BASE}/files/{file_id}", headers=headers, params={"fields": "parents"})
            if current.status_code != 200:
                return _text(f"Couldn't look up current location (HTTP {current.status_code}): {current.text[:300]}")
            old_parents = ",".join(current.json().get("parents", []))
            params["addParents"] = new_parent
            if old_parents:
                params["removeParents"] = old_parents
        resp = await client.patch(f"{DRIVE_BASE}/files/{file_id}", headers=headers, json=body, params=params)
    if resp.status_code != 200:
        return _text(f"Update failed (HTTP {resp.status_code}): {resp.text[:300]}")
    f = resp.json()
    return _text(f"Updated [{f['id']}] {f.get('name')} — now in parents: {f.get('parents')}")


@tool(
    "create_gmail_send_as",
    "Add a custom 'send mail as' address (e.g. hello@yourbrand.com) to a "
    "connected Gmail account, so outgoing mail can be sent FROM that address "
    "— not just received. No SMTP/app-password needed: creates the alias "
    "directly via the API, which triggers Google's own ownership-verification "
    "email to that address automatically. That verification email will only "
    "arrive if forwarding (e.g. push_email_forwarding_dns) is already set up "
    "and live — do that first. Returns whether it needs verification.",
    {"account_email": str, "send_as_email": str, "display_name": str},
)
async def create_gmail_send_as(args: dict) -> dict[str, Any]:
    account_email = (args.get("account_email") or "").strip()
    headers = await _auth_headers(account_email)
    if not headers:
        return _no_account(account_email)
    send_as_email = (args.get("send_as_email") or "").strip()
    if not send_as_email:
        return _text("create_gmail_send_as needs a `send_as_email`.")
    body = {"sendAsEmail": send_as_email, "displayName": args.get("display_name") or send_as_email}
    async with httpx.AsyncClient(timeout=20) as client:
        resp = await client.post(f"{GMAIL_BASE}/users/me/settings/sendAs", headers=headers, json=body)
    if resp.status_code not in (200, 201):
        return _text(f"Failed to add send-as address (HTTP {resp.status_code}): {resp.text[:300]}")
    data = resp.json()
    status = data.get("verificationStatus", "unknown")
    if status == "accepted":
        return _text(f"{send_as_email} added and already usable to send from — no verification needed.")
    return _text(
        f"{send_as_email} added, verification status: {status}. Google just sent a confirmation "
        f"email to {send_as_email} — read it (via list_gmail_messages/get_gmail_message once it "
        "forwards in) and complete whatever confirmation it asks for."
    )


@tool(
    "tag_incoming_mail_by_address",
    "Auto-label incoming mail based on which address it was originally sent "
    "to (the Delivered-To/To header survives forwarding) — for when several "
    "business domains all forward into one Gmail inbox and you want to tell "
    "them apart at a glance. Creates the label if it doesn't exist yet, then "
    "a filter that applies it to anything addressed to `match_address`.",
    {"account_email": str, "match_address": str, "label_name": str},
)
async def tag_incoming_mail_by_address(args: dict) -> dict[str, Any]:
    account_email = (args.get("account_email") or "").strip()
    headers = await _auth_headers(account_email)
    if not headers:
        return _no_account(account_email)
    match_address = (args.get("match_address") or "").strip()
    label_name = (args.get("label_name") or "").strip()
    if not match_address or not label_name:
        return _text("tag_incoming_mail_by_address needs `match_address` and `label_name`.")

    async with httpx.AsyncClient(timeout=20) as client:
        resp = await client.get(f"{GMAIL_BASE}/users/me/labels", headers=headers)
        if resp.status_code != 200:
            return _text(f"Couldn't list labels (HTTP {resp.status_code}): {resp.text[:300]}")
        existing = next((l for l in resp.json().get("labels", []) if l["name"] == label_name), None)
        if existing:
            label_id = existing["id"]
        else:
            resp = await client.post(
                f"{GMAIL_BASE}/users/me/labels", headers=headers,
                json={"name": label_name, "labelListVisibility": "labelShow", "messageListVisibility": "show"},
            )
            if resp.status_code not in (200, 201):
                return _text(f"Couldn't create label '{label_name}' (HTTP {resp.status_code}): {resp.text[:300]}")
            label_id = resp.json()["id"]

        resp = await client.post(
            f"{GMAIL_BASE}/users/me/settings/filters", headers=headers,
            json={"criteria": {"to": match_address}, "action": {"addLabelIds": [label_id]}},
        )
        if resp.status_code not in (200, 201):
            return _text(f"Label '{label_name}' ready, but filter creation failed (HTTP {resp.status_code}): {resp.text[:300]}")

    return _text(f"Mail addressed to {match_address} will now be auto-labeled '{label_name}'.")


google_server = create_sdk_mcp_server(
    name="google", version="1.0.0",
    tools=[
        list_connected_google_accounts, list_calendar_events, create_calendar_event,
        get_calendar_event, delete_calendar_event, list_gmail_messages,
        get_gmail_message, send_gmail_message, create_gmail_draft, send_gmail_draft,
        create_gmail_send_as, tag_incoming_mail_by_address,
        list_drive_files, get_drive_file, create_drive_folder, create_drive_file, update_drive_file,
    ],
)
GOOGLE_TOOL_NAMES = [
    "mcp__google__list_connected_google_accounts", "mcp__google__list_calendar_events",
    "mcp__google__create_calendar_event", "mcp__google__get_calendar_event",
    "mcp__google__delete_calendar_event", "mcp__google__list_gmail_messages",
    "mcp__google__get_gmail_message", "mcp__google__send_gmail_message",
    "mcp__google__create_gmail_draft", "mcp__google__send_gmail_draft",
    "mcp__google__create_gmail_send_as", "mcp__google__tag_incoming_mail_by_address",
    "mcp__google__list_drive_files", "mcp__google__get_drive_file",
    "mcp__google__create_drive_folder", "mcp__google__create_drive_file", "mcp__google__update_drive_file",
]
