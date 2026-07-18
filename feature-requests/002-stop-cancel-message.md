# FR-002: Stop / Cancel a Message While Jason Is Working

- **Requested by:** Dwight Jones
- **Date:** 2026-07-18
- **Status:** Proposed — needs developer build
- **Priority:** High (foundation / feel-in-control)
- **Product:** JasonAI

## The problem
While Jason is generating a response (or running tools), the user has no way to
stop it. If they sent the wrong thing, or Jason is heading down the wrong path,
they're stuck watching until it finishes. That feels trapped, not calm.

## The feature
A **Stop button** that appears while Jason is working and halts the current
response immediately. Any partial answer already on screen stays, clearly marked
as stopped, and the user can send a new message right away.

## Grounding in the code
- Chat streams over SSE from `web/server.py` (`POST /api/chat`), driven by
  `agent/core.py` `stream_chat()`, which drives the Claude Agent SDK `query()`.
- Need three things:
  1. **Cancellable generation** — make the in-flight run stoppable server-side
     (cancel the async task / use the SDK's interrupt path; may require moving
     from one-shot `query()` to the streaming client if `query()` can't be
     interrupted cleanly). Ensure no tool work keeps running in the background
     after a stop.
  2. **Stop endpoint / signal** — a way for the frontend to tell the server to
     abort the current turn for this session.
  3. **Frontend Stop button** in `web/static/index.html` — shown only while
     streaming; on click it aborts and restores the composer.

## Acceptance criteria
- A Stop button appears while Jason is working and is hidden otherwise.
- Clicking it halts the response within ~1 second.
- No background tool/model work continues after a stop.
- The partial response remains visible, marked as stopped.
- The user can immediately send a new message; conversation continuity is intact.
