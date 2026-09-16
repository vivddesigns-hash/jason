---
name: "Inbox Watch Schedule"
description: "Change how often the background email/calendar watch actually runs its real check. Use when Dwight asks to make it check more or less often, pause it, or asks how often it currently checks."
metadata:
  jason:
    emoji: ⏱️
    activation-hints:
      - user asks to change how often email/calendar gets checked
      - user asks how often the inbox watch runs
      - user asks to pause or resume the background email/calendar check
    avoid-when:
      - user is asking you to check email/calendar right now, in this conversation (just do it directly with your Gmail/Calendar tools)
    category: productivity
---

# Inbox Watch Schedule

The background email/calendar watch (`heartbeat/run_inbox_watch.py`) fires
every 5 minutes on a timer, but only actually runs a real check — using
your Gmail/Calendar tools and your own judgment — once `interval_minutes`
has elapsed since the last one. That interval is the one thing Dwight
controls directly, and it's just a number in a JSON file you can read and
edit yourself — no server access, no asking Claude Code, no waiting.

## Where it lives

`{DATA_DIR}/inbox_watch_config.json` — read it with your normal file tools
to see the current setting:

```json
{
  "interval_minutes": 20,
  "last_run_at": "2026-09-16T16:00:00+00:00"
}
```

## Changing the interval

When Dwight asks for a different frequency ("check every 10 minutes",
"every hour is fine", "check less often"), just edit `interval_minutes` in
that file to the new number and tell him plainly what it's now set to.
Leave `last_run_at` alone — don't reset it, the next check will happen
whenever it's naturally due under the new interval.

**Minimum useful value is 5** — the timer itself only fires every 5
minutes, so anything below that has no effect (it'll just run at the
5-minute mark regardless). If Dwight asks for something more frequent than
that, tell him plainly that 5 minutes is the floor and why (the timer
itself only fires that often), rather than silently setting a number that
won't actually do anything faster.

## Pausing it

Set `interval_minutes` to something very large (e.g. `999999`) rather than
deleting the file — deleting it just resets to the 20-minute default on
next run, which isn't the same as "off." Tell Dwight it's effectively
paused and how to turn it back on (set it back to a real number).

## Checking current status

Read the file and tell him the current `interval_minutes` and when
`last_run_at` last happened, in plain terms ("checking every 20 minutes,
last real check was 12 minutes ago").
