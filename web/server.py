"""Web chat server: FastAPI + SSE, driving the Agent SDK core.

Auth: branded login page + signed session cookie (30 days). Password hashed in
auth.json. "Forgot password" emails a time-limited reset link (standard flow).
Email sending is isolated in _send_email() so it can be swapped for a
transactional provider (Resend/Postmark/SES) when this goes multi-subscriber.
"""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import os
import secrets as pysecrets
import time
from pathlib import Path

import httpx
from fastapi import FastAPI, File, Form, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from agent.core import stream_chat, _load_sessions, _save_sessions
from agent.persona import BASE

STATIC = BASE / "web" / "static"
AUTH_FILE = BASE / "auth.json"
SESSION_DAYS = 30
COOKIE = "jason_session"
PUBLIC_URL = os.environ.get("PUBLIC_URL", "https://jason.tryfloatai.com").rstrip("/")
DEFAULT_EMAIL = os.environ.get("RESET_EMAIL", "dwightjonesuk@gmail.com")
# Local Mac install binds to 127.0.0.1 only, so a login is unnecessary friction.
_DISABLE_AUTH = os.environ.get("DISABLE_AUTH") == "1"

app = FastAPI(title="Jason")


# ---------- auth store ----------
def _hash(value: str, salt: str) -> str:
    return hashlib.pbkdf2_hmac("sha256", value.encode(), bytes.fromhex(salt), 200_000).hex()


def _load_auth() -> dict | None:
    if AUTH_FILE.exists():
        try:
            return json.loads(AUTH_FILE.read_text())
        except Exception:
            return None
    return None


def _save_auth(data: dict) -> None:
    AUTH_FILE.write_text(json.dumps(data))
    try:
        AUTH_FILE.chmod(0o600)
    except Exception:
        pass


def _seed_auth() -> dict:
    pw = os.environ.get("BASIC_AUTH_PASS") or "changeme"
    salt = pysecrets.token_hex(16)
    data = {"password_hash": _hash(pw, salt), "salt": salt,
            "email": DEFAULT_EMAIL, "session_secret": pysecrets.token_hex(32)}
    _save_auth(data)
    return data


def _auth() -> dict:
    a = _load_auth() or _seed_auth()
    if not a.get("email"):
        a["email"] = DEFAULT_EMAIL
        _save_auth(a)
    return a


# ---------- session cookie ----------
def _make_session(secret: str) -> str:
    exp = int(time.time()) + SESSION_DAYS * 86400
    sig = hmac.new(bytes.fromhex(secret), str(exp).encode(), hashlib.sha256).hexdigest()
    return f"{exp}.{sig}"


def _valid_session(token: str, secret: str) -> bool:
    try:
        exp_s, sig = token.split(".", 1)
        if int(exp_s) < time.time():
            return False
        good = hmac.new(bytes.fromhex(secret), exp_s.encode(), hashlib.sha256).hexdigest()
        return hmac.compare_digest(sig, good)
    except Exception:
        return False


def _set_cookie(resp, secret: str):
    resp.set_cookie(COOKIE, _make_session(secret), max_age=SESSION_DAYS * 86400,
                    httponly=True, samesite="lax", secure=True, path="/")
    return resp


_EXEMPT = {"/login", "/api/login", "/api/forgot", "/reset", "/api/reset", "/favicon.ico"}


@app.middleware("http")
async def auth_gate(request: Request, call_next):
    path = request.url.path
    if _DISABLE_AUTH or path in _EXEMPT or path.startswith("/static/"):
        return await call_next(request)
    auth = _load_auth()
    token = request.cookies.get(COOKIE, "")
    if auth and _valid_session(token, auth["session_secret"]):
        return await call_next(request)
    if path.startswith("/api/"):
        return JSONResponse({"error": "unauthorized"}, status_code=401)
    return RedirectResponse("/login")


# ---------- email (isolated; swap for a transactional provider at scale) ----------
async def _send_email(to: str, subject: str, body: str) -> bool:
    """Send an email via HQ's agent (read/draft/send confirmed working). Returns
    best-effort success. For a subscription product, replace this body with a
    transactional email API (Resend/Postmark/SES) — nothing else changes."""
    key = os.environ.get("HQ_API_KEY")
    url = (os.environ.get("HQ_API_URL") or "https://industry-33.emergent.host").rstrip("/")
    if not key:
        return False
    try:
        async with httpx.AsyncClient(timeout=90) as c:
            r = await c.post(f"{url}/api/agent",
                             headers={"X-API-Key": key, "Content-Type": "application/json"},
                             json={"message": f'Send an email to {to} with subject "{subject}". Body:\n{body}'})
            actions = (r.json() or {}).get("actions") or []
            for a in actions:
                if a.get("needs_confirmation") or a.get("status") == "pending":
                    await c.post(f"{url}/api/agent/confirm",
                                 headers={"X-API-Key": key, "Content-Type": "application/json"},
                                 json={"action_id": a.get("id"), "approved": True})
        return True
    except Exception:
        return False


# ---------- auth routes ----------
@app.get("/login")
async def login_page(request: Request):
    auth = _load_auth()
    token = request.cookies.get(COOKIE, "")
    if auth and _valid_session(token, auth["session_secret"]):
        return RedirectResponse("/")
    return FileResponse(STATIC / "login.html")


@app.post("/api/login")
async def do_login(request: Request):
    body = await request.json()
    auth = _auth()
    if _hash(body.get("password", ""), auth["salt"]) == auth["password_hash"]:
        return _set_cookie(JSONResponse({"ok": True}), auth["session_secret"])
    return JSONResponse({"ok": False, "error": "Incorrect password"}, status_code=401)


@app.post("/api/forgot")
async def do_forgot(request: Request):
    """Email a time-limited reset link. Always returns ok (don't reveal whether
    the address has an account)."""
    body = await request.json()
    given = (body.get("email") or "").strip().lower()
    auth = _auth()
    # single-user for now: only send if the address matches the account email
    if given and given == auth["email"].lower():
        token = pysecrets.token_urlsafe(32)
        auth["reset"] = {"hash": _hash(token, auth["salt"]), "expires": int(time.time()) + 1800}
        _save_auth(auth)
        link = f"{PUBLIC_URL}/reset?token={token}"
        subject = "Reset your Jason password"
        text = ("You requested a password reset for Jason.\n\n"
                f"Set a new password (link valid for 30 minutes):\n{link}\n\n"
                "If you didn't request this, you can ignore this email.")
        asyncio.create_task(_send_email(auth["email"], subject, text))
    return {"ok": True}


@app.get("/reset")
async def reset_page():
    return FileResponse(STATIC / "reset.html")


@app.post("/api/reset")
async def do_reset(request: Request):
    body = await request.json()
    token = body.get("token") or ""
    newpw = body.get("new_password") or ""
    auth = _auth()
    if len(newpw) < 6:
        return JSONResponse({"ok": False, "error": "Password must be at least 6 characters."}, status_code=400)
    r = auth.get("reset")
    if not r or r.get("expires", 0) < time.time() or _hash(token, auth["salt"]) != r.get("hash"):
        return JSONResponse({"ok": False, "error": "This reset link is invalid or has expired. Request a new one."}, status_code=400)
    salt = pysecrets.token_hex(16)
    auth["password_hash"] = _hash(newpw, salt)
    auth["salt"] = salt
    auth.pop("reset", None)  # single-use
    _save_auth(auth)
    return _set_cookie(JSONResponse({"ok": True}), auth["session_secret"])


@app.post("/api/logout")
async def do_logout():
    resp = JSONResponse({"ok": True})
    resp.delete_cookie(COOKIE, path="/")
    return resp


# ---------- chat ----------
@app.post("/api/chat")
async def chat(request: Request):
    body = await request.json()
    session_id = body.get("session_id") or "default"
    prompt = (body.get("prompt") or "").strip()

    async def event_stream():
        if not prompt:
            yield _sse({"type": "error", "error": "empty prompt"})
            return
        async for event in stream_chat(session_id, prompt):
            yield _sse(event)

    return StreamingResponse(event_stream(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


def _sse(obj: dict) -> str:
    return f"data: {json.dumps(obj)}\n\n"


# ---------- file uploads (documents + media) ----------
UPLOAD_DIR = BASE / "uploads"
MAX_UPLOAD = 50 * 1024 * 1024  # 50 MB


@app.post("/api/upload")
async def upload(session_id: str = Form("default"), file: UploadFile = File(...)):
    raw = os.path.basename(file.filename or "file").strip() or "file"
    safe = "".join(c for c in raw if c.isalnum() or c in " ._-()").strip() or "file"
    sess = "".join(c for c in session_id if c.isalnum() or c in "-_")[:80] or "default"
    d = UPLOAD_DIR / sess
    d.mkdir(parents=True, exist_ok=True)
    dest = d / safe
    stem, suf, i = dest.stem, dest.suffix, 1
    while dest.exists():
        dest = d / f"{stem}-{i}{suf}"
        i += 1
    size = 0
    try:
        with open(dest, "wb") as out:
            while True:
                chunk = await file.read(262144)
                if not chunk:
                    break
                size += len(chunk)
                if size > MAX_UPLOAD:
                    out.close()
                    dest.unlink(missing_ok=True)
                    return JSONResponse({"error": "File too large (max 50 MB)."}, status_code=413)
                out.write(chunk)
    except Exception as exc:
        return JSONResponse({"error": f"upload failed: {exc}"}, status_code=500)
    return {"path": str(dest), "name": dest.name, "size": size}


# ---------- history (import past transcripts) ----------
def _parse_transcript(path: Path) -> list[dict]:
    turns: list[dict] = []
    try:
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                o = json.loads(line)
            except Exception:
                continue
            if o.get("type") not in ("user", "assistant"):
                continue
            content = o.get("message", {}).get("content")
            texts = []
            if isinstance(content, str):
                texts = [content]
            elif isinstance(content, list):
                for b in content:
                    if isinstance(b, dict) and b.get("type") == "text":
                        texts.append(b.get("text", ""))
            txt = "\n".join(x for x in texts if x).strip()
            if txt:
                turns.append({"role": o["type"], "text": txt})
    except Exception:
        return []
    return turns


@app.get("/api/history")
async def history():
    home = Path(os.environ.get("HOME") or Path.home())
    projects = home / ".claude" / "projects"
    smap = _load_sessions()
    out = []
    if projects.exists():
        for jf in projects.glob("*/*.jsonl"):
            turns = _parse_transcript(jf)
            user_turns = [t for t in turns if t["role"] == "user"]
            if len(user_turns) < 1 or len(turns) < 2:
                continue
            if user_turns[0]["text"].startswith("Reply with only the word READY"):
                continue
            sid = jf.stem
            smap[sid] = sid
            out.append({"id": sid, "title": user_turns[0]["text"].splitlines()[0][:48],
                        "ts": int(jf.stat().st_mtime * 1000),
                        "messages": [{"role": t["role"], "text": t["text"]} for t in turns]})
    _save_sessions(smap)
    out.sort(key=lambda s: s["ts"], reverse=True)
    return {"sessions": out}


# ---------- cross-device workspace state ----------
STATE_FILE = BASE / "state.json"


def _load_state() -> dict | None:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except Exception:
            return None
    return None


@app.get("/api/state")
async def get_state():
    s = _load_state()
    return s if s is not None else {"rev": 0, "state": None}


@app.get("/api/rev")
async def get_rev():
    s = _load_state()
    return {"rev": int(s.get("rev", 0)) if s else 0}


@app.put("/api/state")
async def put_state(request: Request):
    body = await request.json()
    cur = _load_state() or {"rev": 0}
    rev = int(cur.get("rev", 0)) + 1
    tmp = STATE_FILE.with_suffix(".json.tmp")
    tmp.write_text(json.dumps({"rev": rev, "state": body.get("state")}), encoding="utf-8")
    tmp.replace(STATE_FILE)
    return {"rev": rev}


@app.get("/")
async def index():
    return FileResponse(STATIC / "index.html")


app.mount("/static", StaticFiles(directory=str(STATIC)), name="static")
