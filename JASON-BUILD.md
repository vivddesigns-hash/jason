# Jason — Complete Build Record

**Last updated:** 2026-07-17. Living document — kept current as Jason evolves.
Purpose: if a session is ever lost, a fresh Claude (or engineer) can read this
and rebuild/operate Jason with zero prior context.

Companion docs: `README.md` (quick ref), `HANDOVER.md` (plain-English handover).
Secrets are **not** in this doc — see §Credentials for where they live.

---

## 1. What Jason is

Jason is Dwight Jones's (FloatAI) **personal AI agent** — a rebuild of a
file-defined agent Dwight previously ran on a third-party platform, now on
infrastructure he controls. It has a soul (persona), file-based memory, 48
skills, an HQ bridge for email/calendar/ClickUp, and a web chat UI.

**Two founding decisions:** (1) runtime = the **Claude Agent SDK** (chosen
because the 48 skills are already in native Claude Skill format); (2) interface
= a **web chat** (explicitly not Telegram).

Founder/principal: **Dwight Jones**, FloatAI (ventures: Ashlan Clinic, Calm Desk,
D-Major HQ, content-copilot, Kingdom Audio/KAI, BCCF).

---

## 2. Where it runs

| | |
|---|---|
| **Live URL** | https://jason.tryfloatai.com |
| **Server** | Hetzner CPX22, Falkenstein — `128.140.119.38` (SSH `root@128.140.119.38`, key-only) |
| **OS / Python** | Ubuntu 24.04, Python 3.12 via `uv` venv at `/opt/myagent/.venv` |
| **App dir** | `/opt/myagent` (runs as non-root user `jason`, HOME `/home/jason`) |
| **Services** | `systemd`: `jason.service` (uvicorn, 127.0.0.1:8787) + `caddy.service` (TLS reverse proxy, 443→8787) |
| **TLS** | Caddy + auto Let's Encrypt; DNS A record `jason.tryfloatai.com → 128.140.119.38` |
| **Firewall** | ufw allows 22 + 80 + 443 only (8787 is localhost-only) |
| **Model** | `claude-haiku-4-5-20251001` (set in `agent/core.py`; can raise to Opus) |
| **Backup** | private repo **github.com/vivddesigns-hash/jason** (code only; `memory/` + secrets gitignored) |

> **Old box warning:** do NOT deploy on `95.217.216.204` — it's saturated
> (load ~13 on 8 cores from FloatAI/next-server/redis). Jason has its own box.

---

## 3. Architecture / how a message flows

1. Browser → `POST /api/chat {session_id, prompt}` (cookie-authenticated).
2. `web/server.py` calls `agent.core.stream_chat(session_id, prompt)`.
3. `agent/persona.py` assembles the **system prompt fresh each turn**: reads
   `soul/SOUL.md`, `soul/IDENTITY.md`, `soul/NOW.md` + the top-level memory files
   (`memory/essentials.md`, `threads.md`, `recent.md`, `buffer.md`), strips
   Vellum-style `_`-comment lines, and appends adapter notes for memory + HQ.
   (The SDK does NOT auto-load memory — this is how "always-in-context" works.)
4. `agent/core.py` runs `claude_agent_sdk.query()` with `ClaudeAgentOptions`:
   `model`, `cwd=/opt/myagent`, `setting_sources=["project"]`, `skills="all"`
   (loads `.claude/skills/`), `allowed_tools` (Read/Write/Edit/Glob/Grep/Bash/
   WebSearch/WebFetch/TodoWrite + `mcp__hq__*`), `permission_mode="bypassPermissions"`
   (⚠ required to run headless — but the SDK **refuses this as root**, hence the
   non-root `jason` user), `mcp_servers={"hq": hq_server}`, `resume=<prior claude session id>`.
5. Assistant text + tool events stream back as SSE → browser renders live.
6. Each chat's `session_id` maps to a Claude SDK session in `.sessions.json`, so
   conversations resume across turns and restarts. Transcripts persist at
   `/home/jason/.claude/projects/-opt-myagent/*.jsonl`.

**Memory model:** no `remember`/`recall` tools (those were the old runtime's).
Memory is files; Jason appends facts to `memory/buffer.md` and searches
`memory/` with built-in tools. Roadmap: reintroduce `remember`/`recall` as
in-process MCP tools via `create_sdk_mcp_server`.

**HQ bridge** (`agent/hq_mcp.py`) — in-process MCP server "hq", 3 tools:
- `hq_agent(message)` → `POST {HQ_API_URL}/api/agent` (NL: send email from
  business accounts, read/create calendar, contacts, ClickUp).
- `hq_confirm(action_id, approved)` → `POST /api/agent/confirm` (approval gate).
- `hq_push_document(title, content, collection, tags)` → `POST /api/documents`.
Persona enforces the email approval gate: draft → surface to Dwight → explicit
approval → `hq_confirm` → verify "done" → report. **Email read/draft/send is
confirmed working** (HQ Gmail token stabilized via Calm Desk).

---

## 4. Web app (`web/`) features

- **UI** (`web/static/index.html`): Calm Desk brand (Newsreader serif for Jason,
  Manrope UI, JetBrains Mono code; warm paper palette, no dark mode). Claude-style
  left sidebar: projects (D-Major Jones/Ashlan Clinic/Kingdom Audio KAI/BCCF) with
  nested chats, search, right-click menu (rename/pin/move/delete), Cmd+K/P/F.
- **Cross-device sync**: workspace state lives on the server (`state.json`),
  endpoints `GET/PUT /api/state` + `GET /api/rev`; client polls every 4s +
  loads on refresh (last-write-wins). All devices share one workspace.
- **Recover past chats** (`GET /api/history`): parses on-disk SDK transcripts and
  imports them as chats, self-mapped in `.sessions.json` so they're continuable.
- **Voice input**: Web Speech API (en-GB) — requires HTTPS (now live). Mic button
  transcribes into the composer.
- **Auth** (`web/server.py`): branded login page (`/login`) + signed session
  cookie (30 days) + recovery-code password reset. Creds hashed in
  `auth.json`. Logout button in the sidebar footer.

---

## 5. Credentials — where they live (NOT in git)

| Secret | Location | Notes |
|---|---|---|
| Login password | `auth.json` (hashed) on server | Value stored in Dwight's 1Password |
| Recovery code | `auth.json` (hashed) | One-time code in Dwight's 1Password; rotates on each reset |
| `ANTHROPIC_API_KEY` | `/opt/myagent/.env` | Jason's brain; never in any file/repo |
| `HQ_API_KEY` | `/opt/myagent/.env` | current active key (`hq_live_pP4b…`) |
| `CALM_DESK_API_KEY` | `/opt/myagent/.env` | de-plaintexted from the bridge skills |
| `HQ_API_URL` | `.env` | `https://industry-33.emergent.host` |

`.env`, `auth.json`, `state.json`, `.sessions.json` are all **gitignored**.
Secrets are never routed through the agent — injected by Dwight or copied
server-side without reading values.

---

## 6. Operating it

```bash
# on the server
systemctl status jason          # app health
systemctl restart jason         # after code changes
journalctl -u jason -n 50       # logs
systemctl restart caddy         # only if Caddyfile changed

# redeploy code from the Mac
cd ~/Developer/myagent
rsync -az --exclude='.git' --exclude='.venv' --exclude='.env' \
  --exclude='.sessions.json' --exclude='state.json' --exclude='auth.json' \
  ./ root@128.140.119.38:/opt/myagent/
ssh root@128.140.119.38 'chown -R jason:jason /opt/myagent && systemctl restart jason'
```

Local dev: `cd ~/Developer/myagent && cp .env.example .env` (fill keys) →
`./run.sh` (web) | `./run.sh heartbeat` | `./run.sh persona`.

---

## 7. Skills (48, in `.claude/skills/`)

Three tiers: **work now** (research/build/deploy/design — deep-niche-research,
frontend-design, emergent-build-prompt, deploy-nextjs-docker-hetzner, etc.);
**via HQ bridge** (gmail, google-calendar, slack, hq-send-email,
import-clickup-to-calmdesk, bridge-*); **need adapting** (old-runtime CLI:
telegram-setup, voice-setup, mcp-setup, notifications, self-upgrade). Bridge
skills reference `$CALM_DESK_API_KEY` (from `.env`).

---

## 8. Deploy gotchas (learned the hard way)

- `permission_mode="bypassPermissions"` = CLI `--dangerously-skip-permissions`,
  **refused as root** → must run as non-root user `jason`.
- `crypto.randomUUID()` and mic/`getUserMedia` need a **secure context** — they
  fail on plain `http://<ip>`, work on HTTPS/localhost. (This caused the early
  "send does nothing" bug.)
- SDK bundles its own CLI; **Python 3.10+ required** (system 3.9 too old → use uv 3.12).
- Don't run PUT-state tests against the live server — it overwrites the workspace
  (recover from transcripts + reseed at high rev if it happens).

---

## 9. Status & roadmap

**Done:** full agent runtime, web UI, cross-device sync, recover-past-chats,
voice, login+recovery-code auth, HTTPS domain, private GitHub backup, secrets
de-plaintexted, HQ email read/draft/send verified.

**Open / next:**
- [ ] Scheduled email briefings (5am / 12pm / 4:40pm UK) — needs a cron/systemd
      timer + a "report back" channel (Briefings chat and/or email). This is the
      "heartbeat" specialized to a schedule.
- [ ] `remember` / `recall` as in-process MCP tools.
- [ ] Background memory consolidation (buffer → concepts).
- [ ] Consider raising the model from Haiku to Opus for heavier work.

---

## 10. File map

```
/opt/myagent  (= ~/Developer/myagent on the Mac)
├── agent/          persona.py (system prompt) · core.py (SDK loop) · hq_mcp.py (HQ bridge)
├── web/            server.py (FastAPI+auth+sync) · static/index.html · static/login.html
├── heartbeat/      run_heartbeat.py (HEARTBEAT.md routine; for cron)
├── soul/           SOUL.md · IDENTITY.md (name=Jason) · NOW.md · HEARTBEAT.md
├── memory/         essentials/threads/recent/buffer + concepts/ (108) + archive/ (gitignored)
├── .claude/skills/ 48 skills
├── .env / auth.json / state.json / .sessions.json   (all gitignored, server-side)
└── run.sh · requirements.txt · README.md · HANDOVER.md · JASON-BUILD.md
```
