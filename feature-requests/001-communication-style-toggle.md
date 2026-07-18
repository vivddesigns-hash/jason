# FR-001: Communication-Style Toggle (Beginner / Intermediate / Dev King)

- **Requested by:** Dwight Jones
- **Date:** 2026-07-18
- **Status:** Proposed — needs developer build (Layer 2 below)
- **Priority:** Medium
- **Product:** Jason Agent

## The idea

Let each user choose how Jason explains things to them, via a simple toggle in
settings, so Jason automatically pitches every answer at the right level instead
of the user having to correct it in conversation.

Three modes:

| Mode | Who it's for | How Jason talks |
|------|--------------|-----------------|
| **Beginner** | Non-technical / creative users | Plain language, analogies, zero jargon. Explains what a thing *is* and *why it matters*. Never asks a question phrased in technical terms. Doesn't make the user run commands. |
| **Intermediate** | Comfortable but not a developer | Normal explanations, defines jargon on first use, some technical detail where useful. |
| **Dev King** | Developers / technical users | Full engineer-level. Uses correct technical terms freely, shows code/commands directly, skips the hand-holding. |

Default for a new user: **Beginner** (safest — easy to level up, jarring to be
talked down to after being over-teched).

## Origin

Came out of a real moment (Jul 18): Dwight, a creative visionary and non-coder,
was getting technical explanations full of dev jargon (.env, Mongo, ports,
baseline). He asked to be spoken to as a "capable novice." A per-user setting
would make Jason adapt to *any* user's comfort level automatically.

## Two layers

### Layer 1 — Per-user preference (Jason can already honor this today)
Jason re-reads its personality/preferences every turn, so for a single user this
already works as a remembered setting: the user states a mode, Jason adapts, and
can switch on command mid-conversation. **No build needed for this to function
for one user.** Already active for Dwight (mode: Beginner).

### Layer 2 — Productized UI toggle (THIS is the developer build)
The actual feature: a user-facing control so every user can set and change their
own mode.

**Needs:**
1. **Settings UI** — a 3-way toggle/segmented control (Beginner / Intermediate /
   Dev King) in Jason's settings screen, with a one-line description under each.
2. **Persistence** — store the choice per user, so it survives across sessions
   and devices.
3. **Prompt wiring** — inject the chosen mode into Jason's system prompt each
   turn (e.g. a "Communication style: <mode> — <behavior guidance>" block), so
   the model actually adapts. Reuse the three behavior descriptions in the table
   above as the injected guidance text.
4. **Mid-chat override (nice-to-have)** — let the user say "explain that like a
   Dev King" for a single answer without permanently changing their setting.

## Acceptance criteria

- A user can pick one of the three modes in settings and it saves.
- After choosing **Beginner**, technical answers contain no unexplained jargon
  and use analogies; after **Dev King**, the same question yields direct
  technical/code-level answers.
- The setting persists across new chats and sessions.
- Changing the mode takes effect on the very next message.

## Open questions

- Should the mode be global, or settable per-workspace/per-topic?
- Better labels than "Dev King"? (It's fun and clear — keep unless it reads
  unprofessional for some audiences.)
- Should Jason *suggest* a mode change when it detects a mismatch (e.g. a user
  keeps asking "what does that mean?")?
