---
name: "Autorename Watcher Control"
description: "Pause, stop, resume, or check the status of the local auto-naming watcher on Dwight's Mac — the background service that automatically renames files and folders he saves across Desktop, Documents, Downloads, Music, Movies, and Pictures. Use immediately whenever Dwight says to stop, pause, or turn off the renaming, reports something looks wrong with a file/folder name, or asks what the watcher has renamed recently."
metadata:
  jason:
    emoji: 🛑
    activation-hints:
      - user asks to stop/pause/turn off the auto-renaming or the watcher
      - user says a file or folder was renamed unexpectedly or something
        looks wrong with file names
      - user asks if the watcher is running, paused, or what it's done recently
      - user asks to resume/turn the watcher back on
    avoid-when:
      - user is asking to rename ONE specific file themselves (not about the
        watcher's automatic behavior)
      - user is asking about Logic session organization specifically (see
        the logic-session-manager skill instead)
    category: productivity
---

# Autorename Watcher Control

Controls the background service that automatically renames files and
folders on Dwight's Mac to `YYYY-MM-DD_ParentFolder_OriginalName` the
moment they're saved, across `~/Desktop`, `~/Documents`, `~/Downloads`,
`~/Music`, `~/Movies`, `~/Pictures`. Built and tested 2026-09-14.

**If Dwight sounds worried or says something looks wrong: pause first, ask
questions after.** The pause action below is instant, harmless, and fully
reversible — there's no cost to pausing on a false alarm, but real cost to
leaving it running while something's actually wrong. Don't debate whether
it's necessary; just do it, then investigate.

**"Pause first" means run Step 1's `touch` command. It does not mean
alarm first.** Those are different things. Pausing is cheap and silent —
do it immediately, without announcing it as an emergency. What you tell
Dwight afterward must be based on **current, live-checked state**, never
on the rename log alone. The log in Step 3 is a historical record — most
of it already happened, was already investigated, and is already resolved.
Reading old log lines and reporting them as something happening *now* is
the single most likely way to falsely alarm Dwight over nothing. Before
you tell him anything is currently wrong, urgent, or needs his attention:
verify it against the real filesystem right now (`ls`, `find`, `launchctl
list`) — not against what the log says happened at some point today.

## Step 0 — Just checking status? Don't take action, and don't guess why.

If Dwight is only asking whether it's paused/running (not asking you to
change anything), run exactly this and nothing else:

```bash
ls -la ~/.autorename-paused 2>&1
launchctl list | grep autorename
```

Report only what these two commands actually show: paused or not, loaded
or not. **Do not explain *why* it's in that state unless you actually know
— read the pause file's own content if it exists (`cat
~/.autorename-paused`), and if that still doesn't explain it, say plainly
"I don't know why," don't invent a plausible-sounding reason.** A status
check is not an invitation to narrate a backstory. Stop after reporting
the fact.

## Step 1 — Pause it (the fast, safe, default action)

```bash
touch ~/.autorename-paused
```

This alone stops every future rename immediately — the watcher checks for
this file before doing anything, every time. It does **not** undo anything
already renamed, and does not require killing any process. This is the
right first move any time Dwight is worried, even before you know what's
wrong.

Confirm it worked:
```bash
ls -la ~/.autorename-paused
```
(If the file exists, renaming is stopped.)

## Step 2 — Fully stop it (only if pausing isn't enough)

Pausing (Step 1) is normally sufficient — nothing runs. Only do this if you
need the background processes themselves gone (e.g. before editing the
watcher's own script files):

```bash
launchctl unload ~/Library/LaunchAgents/com.dwightjones.autorename.plist
launchctl unload ~/Library/LaunchAgents/com.dwightjones.autorename-sweep.plist
pkill -9 -f "autorename-watcher" 2>/dev/null
pkill -9 -f "fswatch" 2>/dev/null
```

Confirm nothing is running:
```bash
launchctl list | grep autorename
ps aux | grep -i "fswatch\|autorename" | grep -v grep
```
(Both should return nothing.)

## Step 3 — Check what it's renamed recently

```bash
tail -30 ~/Documents/Documents/JASON/auto-rename-log.txt
```

Each line is `timestamp  old_path  ->  new_path`. **This is a history log,
not a live status report — every line already happened, some of it hours
ago, and may already be reviewed, approved, or fixed.** Seeing entries in
here is not itself evidence that anything is currently wrong. Concretely:

- **Do not tell Dwight something is "currently" renamed, broken, or needs
  attention based on a log line alone.** Check whether the *old_path*
  still exists and the *new_path* doesn't, or vice versa — that's what
  tells you the actual current state, not the log entry itself.
  ```bash
  ls -d "<old_path>" 2>&1
  ls -d "<new_path>" 2>&1
  ```
- **Do not extrapolate scale you haven't checked** ("hundreds of files")
  — count what's actually there right now if scale matters:
  ```bash
  find <folder> -maxdepth 1 -iname "202*-*-*_*" | wc -l
  ```
- If several old log lines describe a large structural change (e.g. a
  parent folder itself renamed) and you're not sure whether it's still in
  that state, check the parent folder directly before saying anything to
  Dwight — don't reason from the log entries alone.

If, after checking current state, something genuinely looks wrong right
now — say so plainly, with what you actually checked to confirm it. If
current state looks normal, say that, even if the log shows a lot of
historical activity. This is the exact, literal undo list if something
*does* need reverting — reverse a line with `mv "<new_path>" "<old_path>"`,
most-recent-first if several are related (so nested renames unwind
correctly) — but only after confirming, from current state, that a revert
is actually needed.

## Step 4 — Resume it

Only do this once Dwight explicitly confirms he wants it running again —
don't resume on your own judgment after a pause triggered by a concern.

```bash
rm ~/.autorename-paused
```

If you also fully stopped it in Step 2, reload both agents too:
```bash
launchctl load ~/Library/LaunchAgents/com.dwightjones.autorename.plist
launchctl load ~/Library/LaunchAgents/com.dwightjones.autorename-sweep.plist
```

## What it will and won't do (for explaining to Dwight if asked)

- Renames files AND folders, including existing ones already sitting in
  the watched folders — not just new activity going forward.
- Never touches anything *inside* a `.logicx`/`.band` project package —
  only the outer project folder name, and only once nothing has it open
  (checked via `lsof`).
- Never moves anything to a different folder — rename only, same location.
- Does not touch external drives (`/Volumes/...`) — only the 6 folders
  under `~/`.
- The date in the new name is the file's real creation date, not the day
  it happens to get renamed.

## SKILL COMPLETE WHEN
- [ ] The requested action (pause / stop / resume / status check) was executed
- [ ] Confirmed via the check command, not assumed
- [ ] Dwight told plainly what state it's in now
