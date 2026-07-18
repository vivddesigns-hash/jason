# FR-003: Pending / Queue Composer

- **Requested by:** Dwight Jones
- **Date:** 2026-07-18
- **Status:** Proposed — needs developer build + one decision (see Open question)
- **Priority:** High (foundation / feel-in-control)
- **Product:** JasonAI

## The problem
While Jason is working, if the user thinks of something to add, they have no good
option — they either interrupt or sit on the thought. There's also no clear
signal that a message is "in flight" / pending.

## The feature
1. **Keep the composer live while Jason works** — the user can keep typing.
2. **A clear "pending" state** — a small, calm indicator showing a message is
   queued/waiting (and, optionally, a "Jason is working…" status).
3. **Queue-and-send** — a lined-up addition sends automatically when Jason
   finishes the current turn.

## Open question (needs Dwight's steer)
When the user "quickly adds to the message," which do they mean?
- **(A) Queue a NEW follow-up** that auto-sends after Jason finishes the current
  turn. (Default assumption.)
- **(B) Amend/append to the message they JUST sent**, before Jason has really
  gotten going (a brief grace window to add a line to the same turn).
Recommend building **(A)** first (simpler, safer, clearly useful); (B) can be a
later grace-window enhancement.

## Grounding in the code
- Primarily a frontend change in `web/static/index.html` (composer stays
  enabled during streaming; render a pending chip; on turn-complete, flush the
  queued message through the normal `POST /api/chat` flow).
- Pairs naturally with FR-002 (Stop): together they give full send/hold/stop
  control over a turn.

## Acceptance criteria
- The user can type while Jason is working.
- A queued message shows a clear "pending" indicator.
- When Jason finishes, the queued message sends automatically (option A).
- Nothing is lost or double-sent if the user edits or clears the pending message.
