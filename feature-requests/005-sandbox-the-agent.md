# FR-005: Sandbox the Agent (No Shared Machine Access)

- **Requested by:** Security review (2026-07-18)
- **Priority:** CRITICAL — subscription blocker
- **Findings:** C1 (see SECURITY-REVIEW-2026-07-18.md)
- **Product:** JasonAI
- **Roadmap:** Phase 1c (foundation)

## The problem
`agent/core.py` runs the model with `permission_mode="bypassPermissions"`, the
`Bash` tool enabled, and `add_dirs` pointed at the whole Mac home. Anyone who can
chat — or any hidden instruction inside a web page, email, or uploaded file the
agent reads (indirect prompt injection) — can run arbitrary shell commands and
read/write every file the process can reach, **including `.env` (HQ + Anthropic
keys)**. The `DISALLOWED_TOOLS` guard (`rm -rf /*`, `sudo *`) is cosmetic and
trivially bypassed.

This is acceptable for a personal agent on your own Mac behind a password. It is
NOT acceptable once other people use it.

## The fix
- Run each user's agent in an **isolated sandbox** (e.g. a per-user container) with
  no access to the host or to other users' data.
- Remove raw `Bash` for hosted users, or replace it with a tightly locked-down,
  allow-listed shell that cannot escape the sandbox.
- Keep secrets (HQ key, Anthropic key) **out of the agent-reachable environment** —
  broker privileged actions through a separate service the agent can't read.
- Replace the cosmetic deny-list with enforcement that can't be trivially bypassed.

## Acceptance criteria
- An agent turn cannot read another user's files or the host's secrets.
- An agent turn cannot execute arbitrary commands on the host.
- A prompt-injection payload in fetched web/email/file content cannot reach the
  host shell or secret store.
