# FR-006: Auth Hardening

- **Requested by:** Security review (2026-07-18)
- **Priority:** HIGH — can be done anytime
- **Findings:** H1, H2, M1 (see SECURITY-REVIEW-2026-07-18.md)
- **Product:** JasonAI

## The problems
- **H1 — Weak default.** `_seed_auth()` falls back to password `changeme` if
  `BASIC_AUTH_PASS` is unset, and `.env.example` implies you can "run open." A
  public deploy that forgets the password is wide open to the (powerful) agent.
- **H2 — Sessions can't be revoked.** Logout only deletes the cookie client-side,
  and password reset rotates the password but NOT `session_secret` — so a leaked
  session stays valid up to 30 days, and resetting after a compromise does not
  evict the intruder.
- **M1 — `DISABLE_AUTH` kill-switch.** One env var turns off ALL auth; dangerous if
  ever set on a public host.

## The fix
- Refuse to boot on a non-loopback host unless a strong password (or real accounts)
  is configured; remove the `changeme` fallback.
- Rotate `session_secret` on password reset and add a "sign out everywhere" action;
  move toward server-side session records with multi-user (FR-004).
- Gate `DISABLE_AUTH` so it only applies when bound to loopback (127.0.0.1).

## Acceptance criteria
- The app cannot start on a public host without a real password / accounts.
- After a password reset, all previously issued sessions are invalid.
- `DISABLE_AUTH` has no effect on a public bind.
