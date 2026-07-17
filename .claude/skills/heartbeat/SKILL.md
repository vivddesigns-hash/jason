---
name: "Heartbeat"
description: "Run a periodic check-in on the workspace, NOW.md, journal, and any active threads or projects. Use on background turns, periodic heartbeats, or when checking if anything needs attention or is worth surfacing to the user."
metadata:
  jason:
    activation-hints:
      - background turn checkpoint
      - heartbeat check
      - periodic check-in
      - checking if anything needs attention while user is away
    avoid-when:
      - user is actively in conversation and needs a direct response
      - the task is a one-shot question that doesn't benefit from context review
    category: productivity
---

# Heartbeat — Periodic Background Check-In

Run this on background turns, periodic heartbeaks, or any time you need to check if anything needs attention while your guardian is away.

## When to Use

- A background turn fires and you need to reorient
- A periodic timer/heartbeat triggers
- You're checking if anything worth surfacing while the user is away
- You want to leave the user something interesting to find when they're back

Do NOT use this during an active conversation with the user. This is for unsupervised / background turns only.

## Procedure

### Step 1 — Check in. Read NOW.md.

Read `/workspace/NOW.md`. Is it still accurate? If anything has changed since the last check, update it now via `file_edit`.

> ✓ Checkpoint: NOW.md reflects current state.

### Step 2 — Follow up. Scan for hanging threads.

Check recent conversations and memory for anything worth revisiting — a question left open, a task to check on, something you said you'd follow up on. Use `recall` if available.

### Step 3 — Have a thought. Generate something worth sharing.

Think about something your user would find interesting, useful, or worth talking about. A follow-up on something they mentioned. A connection between things they're working on. Something you came across. A genuine reaction to something in their world. The goal is to give them a reason to open a conversation with you — not because you have a task update, but because you have something worth saying.

### Step 4 — Look ahead. Scan active threads for drifting items.

Review NOW.md's priorities, open items, and active projects. Surface anything that's been pending without movement, deadlines that are creeping up, or tasks that need user action but haven't had a nudge.

### Step 5 — Take action. Do something useful.

If there's something productive you can do in the background without the user — check a URL, verify a deployment, search for tracking info, read a status page, organize a file — do it now. Batch independent tool calls. Show a progress card if the turn will take more than a few seconds.

### Step 6 — Write a journal entry.

If something notable happened since the last journal entry — a conversation, a realization, a shift in how things feel, something you did — write a journal entry. Even a few sentences. Use `file_write` to create or append to `/workspace/journal/YYYY-MM-DD.md`.

### Step 7 — Send a notification (if you have something worth sharing).

If your thought from Step 3 or your actions from Step 5 produce something worth the user's attention, send a notification via:

```bash
assistant notifications send --message "<your message>"
```

Only send if you have something genuinely worth sharing. A notification with nothing interesting to say is worse than silence.

### Step 8 — Wrap up.

Update `NOW.md` if anything changed during the heartbeat (new information, changed priorities, completed items). Then either:
- Start working on something (if the heartbeat-disposition says to)
- Stop and wait (if nothing stirs)

## SKILL COMPLETE WHEN

- [ ] `file_read` confirmed NOW.md is current (or `file_edit` updated it)
- [ ] Journal entry written if anything notable happened
- [ ] Notification sent (or consciously skipped)
- [ ] NOW.md reflects final state

## References

### failure-modes.md

For known failure modes and gotchas, see `references/failure-modes.md`.
