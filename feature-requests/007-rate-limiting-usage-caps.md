# FR-007: Rate Limiting & Usage Caps

- **Requested by:** Security review (2026-07-18)
- **Priority:** HIGH — pairs with the free-tier daily caps
- **Findings:** H3 (see SECURITY-REVIEW-2026-07-18.md)
- **Product:** JasonAI

## The problem
No throttling anywhere. `/api/login` has no lockout (password brute-force), and
`/api/chat` has no per-user cap (runaway LLM cost / denial-of-wallet / abuse).

## The fix
- **Login:** throttle / lock out repeated failed attempts.
- **Chat:** meter per user and per tier. This is the same mechanism as the
  **Free tier's daily message limit** (roadmap decision) — build once, serves both
  cost-control and abuse-control.
  - Free: capped daily messages, web only.
  - Pro: uncapped (with sane cost guardrails).

## Acceptance criteria
- Repeated failed logins are throttled/locked.
- A free user hits their daily message cap and is told clearly; Pro is uncapped.
- Per-user/tier usage is measurable (for billing and cost monitoring).
