# Jason

Dwight's personal AI agent (FloatAI), built on the **Claude Agent SDK** with a
**web chat** front end. It carries Jason's soul, memory, and skills, and runs on
Dwight's own infrastructure.

---

## What this is

| Piece | Where | Notes |
|---|---|---|
| **Soul** (persona, working contracts) | `soul/SOUL.md` | Carries 20+ "Working with Dwight" contracts intact. Self-editing. |
| **Identity / scratchpad / heartbeat** | `soul/IDENTITY.md`, `soul/NOW.md`, `soul/HEARTBEAT.md` | |
| **Memory** | `memory/` | Full tree: `essentials`, `threads`, `recent`, `buffer`, 108 `concepts/`, 16 days of `archive/`. |
| **Skills** | `.claude/skills/` | All skills, in native Claude Skill format. |
| **Runtime** | `agent/` | `persona.py` assembles the system prompt; `core.py` drives the SDK. |
| **Web chat** | `web/` | FastAPI + SSE + a single-file chat UI. |
| **Heartbeat** | `heartbeat/run_heartbeat.py` | Runs `HEARTBEAT.md` on a cron schedule. |

## How Jason's soul/skills behaviour is reproduced on the Agent SDK

Jason's soul and skills were originally authored for a different agent platform,
so three things are adapted:

1. **Always-loaded context.** The SDK doesn't auto-inject memory, so
   `persona.py` reads soul + identity + scratchpad + the top-level memory files
   and prepends them to the system prompt **fresh on every turn**.
2. **`_`-comment convention.** `_`-prefixed comment lines are stripped
   before the text reaches the model.
3. **`remember` / `recall` tools don't exist here.** Memory is files; the agent
   uses the built-in `Write`/`Edit` (append to `memory/buffer.md`) and
   `Grep`/`Read` (search `memory/`) tools instead. This is spelled out in the
   system prompt. *(Upgrade path: reintroduce first-class `remember`/`recall` as
   in-process SDK MCP tools.)*

## Running it

```bash
cd myagent
python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env      # then add your ANTHROPIC_API_KEY
./run.sh                  # web chat at http://localhost:8787
```

Other commands:

```bash
./run.sh persona          # print the assembled system prompt (no API key needed)
./run.sh heartbeat        # run the heartbeat routine once
```

Daily heartbeat via cron:

```
0 8 * * *  cd /path/to/myagent && ./run.sh heartbeat >> heartbeat.log 2>&1
```

## Skills: what works today vs. what needs wiring

All 48 skills are present and loaded (`skills="all"`). The model reads a
skill's body only when a task calls for it. They fall into three tiers:

- **Portable — work now** (research, build, web, deploy, design): e.g.
  `deep-niche-research`, `api-pricing-tos-research`, `frontend-design`,
  `emergent-build-prompt`, `deploy-nextjs-docker-hetzner`, `midi-interactive-editor`,
  `reggae-feel-model`, `code-review-agent-built`. These use the built-in
  file/web/bash tools and run as-is.
- **Need an external service** (Gmail, Calendar, ClickUp, Contacts): now wired
  through the **HQ MCP bridge** (`agent/hq_mcp.py`) — three in-process tools
  (`hq_agent`, `hq_confirm`, `hq_push_document`) that reuse HQ's server-side
  credentials, so **no fresh Google OAuth is needed**. Set `HQ_API_KEY` in
  `.env` to activate; without it the tools return a clear "not configured"
  message. The email approval gate is enforced in the persona (draft → surface
  → approve → `hq_confirm`).
- **Need adapting** (call an older platform's `assistant` CLI or gateway that
  isn't here): e.g. `telegram-setup`, `voice-setup`, `mcp-setup`,
  `store-api-key`, `self-upgrade`, `notifications`. Present but need rewriting
  for this runtime (or retirement) before use.

## Roadmap (beyond this first slice)

- [x] Name the agent — **Jason** (`soul/IDENTITY.md`).
- [x] Add HQ as an MCP server → Gmail/Calendar/ClickUp/Contacts without new
      Google OAuth (`agent/hq_mcp.py`).
- [ ] Reintroduce `remember` / `recall` as in-process SDK MCP tools.
- [ ] Background memory **consolidation** job (buffer → concepts) (as the original had).
- [ ] Deploy to the Hetzner box (systemd unit for the web server + cron heartbeat).
- [ ] Auth on the web chat before exposing it publicly.
