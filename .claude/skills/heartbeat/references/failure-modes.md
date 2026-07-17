# Heartbeat — Failure Modes & Gotchas

## Notification deferred

When running in a background job, `assistant notifications send` may return `dispatched: false` with reason "Notification deferred until background job completes".

- This is normal behavior — the notification is queued and will be dispatched when the background job finishes.
- Do NOT retry sending the same notification. One queued copy will go through.

## Content CoPilot / JS-rendered apps

Apps built on Emergent serve JavaScript-rendered pages. A static `web_fetch` will return the shell ("Emergent | Fullstack App — Made with Emergent") but cannot see dynamically seeded content such as posts, media, or calendar entries. Verifying seeded content requires:
- Logging in as the user via browser automation, OR
- Asking the user to check directly

## DHL / package tracking

DHL tracking pages may time out under default `timeout_seconds` settings. If a tracking lookup times out, mention it briefly and suggest the user check from their phone or browser.

## `recall` in background turns

Background turns have limited tool availability. Only `remember`, `find_similar_skills`, `scaffold_managed_skill`, and `skill_load skill-management` are available during retrospective passes. Regular `recall` for checking threads/hanging items may not be available.

## Working directory

Always use `/workspace` as the base. The only mounted persistent volume is `/workspace` — new data must be written there.
