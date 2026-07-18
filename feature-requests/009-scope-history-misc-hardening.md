# FR-009: Scope History + Misc Hardening

- **Requested by:** Security review (2026-07-18)
- **Priority:** MEDIUM / LOW — hygiene, do as you touch these areas
- **Findings:** H5, M2, M3, L1, L2 (see SECURITY-REVIEW-2026-07-18.md)
- **Product:** JasonAI

## The problems & fixes
- **H5 — `/api/history` reads ALL Claude Code transcripts** on the machine
  (`~/.claude/projects/*`), not just Jason's, and returns their text. → Scope it to
  Jason's own sessions; per-user in the hosted model.
- **M2 — `/api/state` PUT has no size limit** and writes one global file (disk DoS
  risk). → Cap body size; per-user state (ties to FR-004).
- **M3 — `sync.sh` root SSH + newer-wins rsync** of memory/soul/state can clobber on
  simultaneous edits and syncs both directions. → Safer sync strategy / locking;
  note for single-user care meanwhile.
- **L1 — Project names not escaped** in the sidebar `innerHTML` (self-XSS only). →
  Escape them.
- **L2 — `Secure` cookie on `http://localhost`** may not be sent by some browsers
  (minor; local uses `DISABLE_AUTH`). → Note only.

## Acceptance criteria
- History shows only the signed-in user's Jason chats.
- Oversized state writes are rejected.
- Project names render safely; sync can't silently clobber.
