"""Web chat server: FastAPI + SSE, driving the Agent SDK core.

Auth: a branded login page + signed session cookie (30 days). Password and a
one-time recovery code are stored hashed in auth.json. "Forgot password" uses
the recovery code to set a new password (and issues a fresh recovery code).
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets as pysecrets
import time
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from agent.core import stream_chat, _load_sessions, _save_sessions
from agent.persona import BASE

STATIC = BASE / "web" / "static"
AUTH_FILE = BASE / "auth.json"
SESSION_DAYS = 30
COOKIE = "jason_session"

app = FastAPI(title="Jason")


# ---------- auth store ----------
def _hash(value: str, salt: str) -> str:
    return hashlib.pbkdf2_hmac("sha256", value.encode(), bytes.fromhex(salt), 200_000).hex()


def _new_code() -> str:
    return "-".join(pysecrets.token_hex(2).upper() for _ in range(4))  # e.g. A1B2-C3D4-E5F6-7890


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
    """Create auth.json if missing. Password seeds from BASIC_AUTH_PASS (so the
    existing password carries over); recovery code is written once to
    recovery-code.txt for the operator to read, then it should be deleted."""
    pw = os.environ.get("BASIC_AUTH_PASS") or "changeme"
    salt, rsalt = pysecrets.token_hex(16), pysecrets.token_hex(16)
    code = _new_code()
    data = {
        "password_hash": _hash(pw, salt), "salt": salt,
        "recovery_hash": _hash(code, rsalt), "recovery_salt": rsalt,
        "session_secret": pysecrets.token_hex(32),
    }
    _save_auth(data)
    try:
        (BASE / "recovery-code.txt").write_text(code + "\n")
    except Exception:
        pass
    return data


def _auth() -> dict:
    return _load_auth() or _seed_auth()


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


_EXEMPT = {"/login", "/api/login", "/api/forgot", "/favicon.ico"}


@app.middleware("http")
async def auth_gate(request: Request, call_next):
    path = request.url.path
    if path in _EXEMPT or path.startswith("/static/"):
        return await call_next(request)
    auth = _load_auth()
    token = request.cookies.get(COOKIE, "")
    if auth and _valid_session(token, auth["session_secret"]):
        return await call_next(request)
    if path.startswith("/api/"):
        return JSONResponse({"error": "unauthorized"}, status_code=401)
    return RedirectResponse("/login")


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
    body = await request.json()
    code = (body.get("recovery_code") or "").strip().upper()
    newpw = body.get("new_password") or ""
    auth = _auth()
    if len(newpw) < 6:
        return JSONResponse({"ok": False, "error": "New password must be at least 6 characters."}, status_code=400)
    if _hash(code, auth["recovery_salt"]) != auth["recovery_hash"]:
        return JSONResponse({"ok": False, "error": "Invalid recovery code."}, status_code=401)
    salt, rsalt = pysecrets.token_hex(16), pysecrets.token_hex(16)
    newcode = _new_code()
    auth.update({"password_hash": _hash(newpw, salt), "salt": salt,
                 "recovery_hash": _hash(newcode, rsalt), "recovery_salt": rsalt})
    _save_auth(auth)
    return _set_cookie(JSONResponse({"ok": True, "recovery_code": newcode}), auth["session_secret"])


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
