# Jason — Build Report & Handover

**Read this first.** This is a complete status report on "Jason," a personal AI
agent built for Dwight. It's written so another Claude (or engineer) who knows
Dwight's server and businesses can pick it up, finish it, and deploy it without
needing the prior conversation. Plain-English explanations are included on
purpose.

---

## 1. What Jason is (in plain terms)

Jason is Dwight's **own personal AI agent** — a rebuild of the personal agent
Dwight had previously been running on a third-party platform. The goal was:
recreate everything that agent could do, on infrastructure Dwight controls
(FloatAI), with room to grow.

Two decisions Dwight made up front:

1. **Runtime = the Claude Agent SDK.** This is Anthropic's official library for
   building agents (it's Claude Code packaged as a Python library). It was
   chosen because Jason's 55 "skills" are already written in Anthropic's native
   Skill format, so they drop straight in with no rewriting.
2. **Interface = a web chat** (a chat page in a browser), **not** Telegram.
   Dwight explicitly did not want Telegram.

**What "the agent" actually is:** a personality/instructions file (`SOUL.md`), a
memory folder, and 55 skill folders — all fed to Claude on every message. Jason
reads and writes his own memory files, can search the web, run shell commands,
and — new in this build — can drive Dwight's **HQ** platform to send business
email, manage calendar, and manage ClickUp.

**Jargon decoder:**
- **Skill** = a folder with a `SKILL.md` file that teaches the agent how to do
  one specific task (e.g. "deep niche research", "send email via HQ"). The agent
  reads a skill's instructions only when a task needs it.
- **MCP server** = a standard way to give an AI agent a set of tools. "Wiring HQ
  as an MCP server" means: I gave Jason three buttons — *ask HQ to do
  something*, *confirm an HQ action*, *file a document in HQ* — that call HQ's
  existing API. It runs inside Jason's own process (no separate service to host).
- **System prompt** = the big block of instructions the agent gets at the start
  of every conversation. Jason's is assembled fresh each message from his soul +
  memory (~41,000 characters).

---

## 2. Where it lives

```
~/Developer/myagent          (on Dwight's Mac; a git repo, all work committed)
```

Nothing is deployed to the Hetzner server yet. It has been built and tested
locally on the Mac. It is **not** pushed to GitHub (no remote set).

---

## 3. What's built, and what was verified

Everything below is done and committed. The ✅ items were actually run and
confirmed, not just written.

| Area | Status |
|---|---|
| Jason's `SOUL.md` (persona + 20+ "Working with Dwight" contracts) ported | ✅ |
| `IDENTITY.md` — **named "Jason"**, role = personal agent / chief of staff | ✅ |
| `NOW.md` (scratchpad) + `HEARTBEAT.md` (daily routine) ported | ✅ |
| Full `memory/` tree ported: essentials, threads, recent, buffer, **108** concept files, **16** days of archive | ✅ |
| All **48** skills ported into `.claude/skills/` | ✅ |
| Persona loader assembles soul + memory into the system prompt each turn (~41K chars) | ✅ verified |
| Agent runtime driving the Claude Agent SDK (`claude-opus-4-8`) | ✅ imports/options verified |
| Web chat (browser UI + streaming backend) | ✅ boots, serves HTTP 200 |
| Conversation memory across turns and restarts (session resume) | ✅ code in place |
| **HQ bridge** (email / calendar / ClickUp / contacts / documents) as an in-process MCP server | ✅ registers, tools callable, safe when unconfigured |
| Daily heartbeat runner (for cron) | ✅ written |
| Python environment set up (see §6) | ✅ |
| **A live conversation with Jason** | ❌ **NOT yet run** — needs API keys (see §5). This is the one thing left to prove it end-to-end. |

**Important nuance:** I deliberately did **not** run Jason "live" (an actual
message → Claude reply). A live run spends Anthropic credits on Dwight's account
and lets the agent take real actions (it runs with permissions to use the shell
and touch files). That first live run should be Dwight's, with his own keys.
Everything *around* the live call is tested.

---

## 4. How Jason works (the flow)

When someone sends a message in the web chat:

1. The web server (`web/server.py`) receives it and calls the agent core.
2. The core (`agent/core.py`) builds the instructions:
   - `agent/persona.py` reads `soul/SOUL.md`, `soul/IDENTITY.md`, `soul/NOW.md`,
     and the top-level memory files, strips `_`-comment lines, and
     glues them into one system prompt. (The SDK does **not** auto-load memory
     on its own, so we do it ourselves, fresh every message — that's how
     Jason "always remembers" his essentials.)
   - It appends instructions on **how memory works here** (Jason writes new facts
     by appending to `memory/buffer.md` and recalls by searching `memory/` with
     his file tools — there is no separate `remember`/`recall` command yet).
   - It appends instructions on **how to use HQ** (the three HQ tools + Dwight's
     email approval rule).
3. It calls the Claude Agent SDK, which loads the 48 skills from
   `.claude/skills/` and runs the agent loop (Claude thinks, uses tools, replies).
4. The reply is streamed back to the browser token-by-token.
5. The conversation's session id is saved (`.sessions.json`) so the next message
   continues the same thread — even after a restart.

**The HQ bridge specifically** (`agent/hq_mcp.py`) gives Jason three tools:
- `hq_agent(message)` → calls `POST https://industry-33.emergent.host/api/agent`
  with a plain-English instruction. HQ then does the work (send email from a
  business address, read/create calendar events, look up contacts, manage
  ClickUp) using **HQ's own stored Google/ClickUp credentials**.
- `hq_confirm(action_id, approved)` → calls `POST /api/agent/confirm`. HQ holds
  risky actions (like sending an email) for approval; this confirms them.
- `hq_push_document(title, content, collection, tags)` → calls
  `POST /api/documents` to file a doc into HQ's library.

**Why this matters:** it means Jason can do email/calendar/ClickUp **without
setting up a fresh Google OAuth integration** (the slow, painful verification
process). He borrows HQ's existing connection. Jason's persona also enforces
Dwight's email rule: draft the email → show Dwight the exact text → wait for his
explicit OK → only then confirm the send → report the result.

---

## 5. What Dwight needs to do (the only blockers)

Jason needs **two secret keys** put into a `.env` file. Both are things Dwight
already has; I cannot read or set secrets myself.

```bash
cd ~/Developer/myagent
cp .env.example .env      # creates the file
# then edit .env and fill in the two values below
```

`.env` contents:

```
ANTHROPIC_API_KEY=sk-ant-...      # Dwight's Anthropic API key
HQ_API_KEY=hq_live_...            # the D-Major HQ API key (about 51 chars)
HQ_API_URL=https://industry-33.emergent.host   # already correct, leave as-is
PORT=8787                          # leave as-is
```

**Where each key comes from:**
- `ANTHROPIC_API_KEY` — from the Anthropic Console (console.anthropic.com →
  API keys). This is what pays for and authorizes Jason's thinking. Without it,
  Jason can't reply at all.
- `HQ_API_KEY` — the **D-Major HQ** API key. In the old Jason setup this was
  stored as `dmajor-hq:api_key`. Dwight likely has it in 1Password (it was in
  `~/Desktop/api-keys-for-1password.txt` at one point). Format starts with
  `hq_live_`. **Optional** — if it's left blank, Jason still runs fine; he just
  can't use the HQ email/calendar/ClickUp tools (they return a "not configured"
  message instead of erroring).

**Then run it:**

```bash
cd ~/Developer/myagent
./run.sh                  # starts the web chat at http://localhost:8787
```

Open http://localhost:8787 in a browser and talk to Jason. A good first test
that exercises the HQ bridge: *"Jason, what's on my calendar today?"*

That's the whole ask. Two keys in a file, then run one command.

---

## 6. Environment already set up (so it "just works" locally)

- The Mac's system Python is 3.9, which is **too old** for the Agent SDK
  (needs 3.10+). To avoid touching system Python, I used **`uv`** (already
  installed) to create an isolated Python 3.12 environment at
  `~/Developer/myagent/.venv` and installed all dependencies into it.
- `run.sh` automatically activates that environment. Nothing else to install
  locally.
- If Jason is moved to the **Hetzner server**, that environment must be recreated
  there (`uv venv --python 3.12 .venv && uv pip install -r requirements.txt`),
  or use whatever Python 3.10+ is on the box.

---

## 7. What Jason can and can't do today

The 48 skills fall into three groups:

- **Work now** (~1/3): research, web browsing, building/deploy specs, frontend
  design, code review, etc. — anything that uses Claude's built-in file, web,
  and shell tools. Examples: `deep-niche-research`, `frontend-design`,
  `emergent-build-prompt`, `deploy-nextjs-docker-hetzner`, `reggae-feel-model`.
- **Work once HQ_API_KEY is set** (~1/3): Gmail, Google Calendar, ClickUp,
  Contacts, HQ documents — via the new HQ bridge.
- **Need adapting** (~1/3): skills that call Jason's `assistant` command-line
  tool (which doesn't exist here) — e.g. `jason-*`, `telegram-setup`,
  `voice-setup`, `notifications`, `self-upgrade`. These are present but won't
  run until rewritten for this runtime (or retired).

---

## 8. Not done yet / open decisions (for the helper Claude to advise on)

1. **First live run** — needs the two keys (§5). Prove one real conversation.
2. **Deploy to Hetzner** — currently only on the Mac. To make Jason always-on:
   - a service unit (systemd) running `uvicorn web.server:app` on a port,
   - a cron entry for the daily heartbeat: `0 8 * * * cd /path/to/myagent &&
     ./run.sh heartbeat >> heartbeat.log 2>&1`,
   - a Python 3.10+ environment on the box (see §6),
   - the `.env` file with both keys placed on the server (not in git).
   The helper Claude knows the Hetzner box (root@95.217.216.204) and can pick the
   port / reverse-proxy / domain.
3. **⚠️ Security — the web chat has NO login yet.** It's fine on localhost. Do
   **not** expose it to the public internet without putting authentication in
   front of it (basic auth, an SSH tunnel, or a login page). Anyone who can
   reach the URL can talk to Jason as Dwight, with Jason's tools and memory.
4. **Permissions** — Jason runs with `bypassPermissions` (auto-approves tool use)
   because a web chat has no human clicking "allow" on each action. The most
   destructive shell patterns are blocked, but this is worth a review before
   deploy.
5. **`remember` / `recall` tools** — Jason had first-class remember/recall
   commands. Jason currently does memory with plain file edits/searches. The
   clean upgrade is to add `remember`/`recall` as in-process MCP tools (the same
   pattern used for HQ in `agent/hq_mcp.py`).
6. **Memory consolidation** — Jason had a background job that filed new facts
   from `buffer.md` into the right concept files. Not rebuilt yet.
7. **Adapt the Jason-only skills** (§7, group 3).

---

## 9. File map

```
~/Developer/myagent/
├── HANDOVER.md            ← this report
├── README.md             quick reference
├── run.sh                ./run.sh (web) | heartbeat | persona
├── requirements.txt      Python deps
├── .env.example          template for the two secret keys (copy to .env)
├── .venv/                Python 3.12 environment (created by uv; gitignored)
│
├── agent/
│   ├── persona.py        builds the system prompt from soul + memory
│   ├── core.py           drives the Claude Agent SDK; session resume
│   └── hq_mcp.py         the HQ bridge (3 tools: agent / confirm / document)
│
├── web/
│   ├── server.py         FastAPI: /api/chat (streaming) + serves the UI
│   └── static/index.html the chat page
│
├── heartbeat/
│   └── run_heartbeat.py  runs HEARTBEAT.md once (wire to cron)
│
├── soul/
│   ├── SOUL.md           persona + "Working with Dwight" contracts
│   ├── IDENTITY.md       name = Jason
│   ├── NOW.md            scratchpad
│   └── HEARTBEAT.md      daily check-in checklist
│
├── memory/               essentials / threads / recent / buffer
│   ├── concepts/         108 concept files
│   └── archive/          16 days of dated records
│
└── .claude/skills/       all skills (native Claude Skill format)
```

---

## 10. Command reference

```bash
cd ~/Developer/myagent

./run.sh              # start the web chat  → http://localhost:8787
./run.sh heartbeat    # run the daily heartbeat routine once
./run.sh persona      # print the assembled system prompt (no API key needed)
```

---

*End of report. The two immediate blockers are the two keys in §5; the biggest
decision is §8 (deploy + security). Everything else is built.*
