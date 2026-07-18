# Jason App — Full Code Review & Security Scan

- **Date:** 2026-07-18
- **Reviewer:** Jason (self-review)
- **Scope:** `web/server.py`, `agent/core.py`, `agent/persona.py`, `agent/hq_mcp.py`,
  `agent/memory_tools.py`, `web/static/index.html`, `run.sh`, `sync.sh`, `.env.example`,
  `.gitignore`. Not deep-reviewed: `agent/consolidate.py`, `heartbeat/`, `menubar/`,
  `login.html`, `reset.html` (low security surface).
- **Verdict:** Solid, clean, single-user personal agent. Security posture is
  appropriate for "my own powerful agent on my Mac, behind one password." Almost
  every serious finding is a **blocker for the multi-user subscription phase**, not
  an active hole in today's single-user setup.

---

## The one thing to understand first
Today the entire app is **single-user by design**: one account (`auth.json`), one
brain (`memory/`), one workspace (`state.json`), one machine. The login cookie
proves only "someone knows the password" — it carries no user identity. That's
fine for you. But the moment a second paying user exists, they'd share your
account model, and (worse) the agent's power isn't sandboxed. The whole "Phase 1
Foundation" in the roadmap is essentially the fix list below.

---

## CRITICAL (must be fixed before real subscribers)

### C1 — The agent is unsandboxed remote-code-execution by design
`agent/core.py` runs the model with `permission_mode="bypassPermissions"`, the
`Bash` tool enabled, and `add_dirs` pointed at the whole Mac home. So anyone who
can send a chat message — or any hidden instruction inside a web page, email, or
uploaded file the agent reads (indirect prompt injection) — can make it run
arbitrary shell commands and read/write every file the process can reach,
**including `.env` (the HQ key + Anthropic key)**. The `DISALLOWED_TOOLS` guard
(`rm -rf /*`, `sudo *`) is cosmetic — trivially bypassed (`rm -rf ~`, `python -c`, etc.).
- *Single-user local:* acceptable — it's your machine, your agent, behind a password.
- *Subscription:* unacceptable. Needs a sandbox per user (isolated container),
  no raw `Bash` (or a tightly locked-down shell), and secrets unreachable by the
  agent process.

### C2 — No user identity / no multi-tenant isolation
The session cookie is `{expiry}.{hmac(global_secret, expiry)}` — it identifies no
user. There is one `auth.json`, one `memory/`, one `state.json`, and `/api/history`
reads a single machine `HOME`. With more than one user, everyone would share one
brain, one workspace, and interchangeable cookies. Requires a real accounts model:
per-user records, per-user isolated memory/state, and user identity inside the
session. (This is the roadmap's "real accounts" item — it's the gate to charging.)

---

## HIGH

### H1 — Weak default password + "run open" guidance
`_seed_auth()` falls back to password **`changeme`** if `BASIC_AUTH_PASS` is unset,
and `.env.example` implies you can "run open (localhost only)." A public deploy
that forgets to set the password = an open door straight to the C1 agent. Fix:
refuse to boot on a non-local host without a strong password set; drop the
`changeme` fallback.

### H2 — Sessions can't be revoked; reset doesn't rotate the secret
Logout only deletes the cookie client-side, and password reset rotates the
password but **not** `session_secret`. So a leaked/stolen session stays valid up
to 30 days, and resetting your password after a compromise does **not** kick the
attacker out. Fix: rotate `session_secret` on reset (and offer "sign out
everywhere"); consider server-side session records when multi-user lands.

### H3 — No rate limiting anywhere
`/api/login` has no throttle/lockout (password brute-force), and `/api/chat` has
no per-user cap (runaway LLM cost / denial-of-wallet). Directly relevant to your
"daily message limits on the free tier" plan — that limiter is also your abuse
control. Fix: rate-limit login and meter chat per user/tier.

### H4 — Prompt-injection can drive HQ actions & exfiltrate secrets
The HQ tools (`hq_agent`, `hq_confirm`) let the agent send email / change ClickUp
using your business credentials, and the "get human approval first" rule lives
only in the system prompt (soft), not in code. Combined with C1, injected
instructions from a fetched page/email could send mail as you or read the HQ key.
Fix: enforce the approval gate in code for outbound/irreversible HQ actions, not
just in the prompt.

### H5 — `/api/history` exposes *all* Claude Code transcripts on the machine
It reads `~/.claude/projects/*/*.jsonl` — every Claude Code conversation on the
Mac, not just Jason's — and returns their text. On your personal machine that's
your own data, but it can surface unrelated project content into the app, and in
a hosted/multi-user world it leaks across the shared HOME. Fix: scope to Jason's
own sessions; per-user in the hosted model.

---

## MEDIUM / LOW

- **M1 — `DISABLE_AUTH` kill-switch.** One env var turns off *all* auth. Handy for
  localhost, dangerous if ever set on a public host. Gate it to loopback binds only.
- **M2 — `/api/state` PUT has no size limit** and writes one global file — a large
  body could fill the disk; multi-user needs per-user state anyway.
- **M3 — `sync.sh` root SSH + newer-wins rsync** of `memory/soul/state` between Mac
  and cloud can silently clobber on simultaneous edits, and syncs both directions
  (a compromise on one side propagates). Fine for careful single-user use; note it.
- **L1 — Project names aren't escaped** when rendered in the sidebar (`innerHTML`).
  Self-XSS only (you'd have to name your own project with a script tag). Low.
- **L2 — `Secure` cookie on `http://localhost`** may not be sent by some browsers
  (minor; local uses `DISABLE_AUTH` anyway).

---

## What's genuinely GOOD (the foundation is sound)
- **No secrets committed** — `.env`, `auth.json`, `state.json`, `memory/`,
  `uploads/` all gitignored.
- **Strong password hashing** — pbkdf2-hmac-sha256, 200k iterations, random salt.
- **Good cookie hygiene** — HttpOnly + Secure + SameSite=Lax; HMAC-signed with
  constant-time compare (`hmac.compare_digest`). CSRF is largely mitigated.
- **Textbook password reset** — single-use token, 30-min expiry, hashed at rest,
  no user enumeration (always returns ok).
- **Frontend is XSS-safe** — `md()` escapes untrusted text *before* innerHTML, so
  even web pages/emails the agent quotes back can't inject script. Nicely done.
- **Safe uploads** — basename + character-filtered filenames (no path traversal),
  50 MB streaming cap.
- **No CORS wildcard**, clean error handling, `auth.json` chmod 600, tidy code.

---

## Recommended order of fixing
1. **When you go multi-user (Phase 1c):** C2 + C1 together — they're the real
   architectural work (accounts + sandboxing). Don't onboard a second user before
   these land.
2. **Quick hardening you can do anytime:** H1 (kill `changeme` + refuse open boot),
   H2 (rotate secret on reset), H3 (rate limits — pairs with your free-tier caps).
3. **Before connecting more powerful/irreversible tools:** H4 (enforce HQ approval
   in code), H5 (scope history).
4. **Hygiene:** M1–M3, L1–L2 as you touch those areas.

None of this is on fire in your current single-user setup. It's the exact
punch-list that turns "my personal agent" into "a product other people can trust."
