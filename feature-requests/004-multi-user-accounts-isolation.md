# FR-004: Multi-User Accounts & Per-User Isolation

- **Requested by:** Security review (2026-07-18)
- **Priority:** CRITICAL — subscription blocker
- **Findings:** C2 (see SECURITY-REVIEW-2026-07-18.md)
- **Product:** JasonAI
- **Roadmap:** Phase 1c (foundation / accounts)

## The problem
The app is single-user by design. There is one account (`auth.json`), one shared
brain (`memory/`), one workspace (`state.json`), and `/api/history` reads a single
machine `HOME`. The login cookie (`{expiry}.{hmac(global_secret, expiry)}`) carries
**no user identity** — any valid cookie is interchangeable. Two paying users would
share your memory and workspace, and could use each other's sessions.

## The fix
- Real accounts model: per-user records; sign-in via **email/password AND Google**
  (per FR / roadmap decision).
- **Per-user isolated memory and state** — each user gets their own `memory/` and
  `state.json` (or per-user rows/namespaces), never shared.
- **User identity inside the session** — bind the session to a user id, not just an
  expiry against one global secret.
- Scope `/api/history` (and everything else) to the signed-in user.

## Acceptance criteria
- Two users each have a completely separate, private brain and workspace.
- User A cannot see User B's memory, chats, files, or state.
- User A's session cookie does not authenticate as User B.
- Do NOT onboard a second real user until this and FR-005 are done.
