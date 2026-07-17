---
name: "Logic Session Manager"
description: "Find Logic Pro session files on the Mac, rename them to the naming convention, update the master session index at /workspace/logic-master-session-index.md, and create cross-reference tasks in ClickUp. Use when Dwight saves a new Logic session, asks to organize his Logic files, or needs session files tracked in the master index."
metadata:
  jason:
    emoji: 🎵
    activation-hints:
      - user saves a new Logic Pro session
      - user wants to organize Logic session files
      - user asks about tracking their music sessions
      - user mentions a new song or recording in Logic
    avoid-when:
      - user asks about DAWs other than Logic Pro
      - user is asking about mixing or mastering advice (not session file
        management)
      - user just wants to find a file path without naming or indexing it
    category: productivity
---

# Logic Session Manager

Organize Logic Pro session files: find them on the Mac, rename to the naming convention, update the master session index at /workspace/logic-master-session-index.md, and create cross-reference tasks in ClickUp.

## When to Use

Use when Dwight saves a new Logic session on his Mac, asks to organize Logic files, or needs new song sessions tracked in the master session index. Also use when he says "I saved a new song" or mentions a Logic session file.

## Step 1 — Confirm intent and collect session details

Ask the user:
- What song did you save?
- What collection/album/project is it for?
- What track number is it in that collection?

If the user just says "I saved a Logic session" without specifics → ask for the song name first (default).

If the user already told you the details in conversation → skip the questions and proceed.

> ✓ Checkpoint: confirm you have the song name, collection, and optional track number before searching.

## Step 2 — Find the session file on the Mac

Use `host_bash` to search the user's Mac for the new Logic file:

```bash
find /Users -maxdepth 5 -name "*<song-name>.logicx" 2>/dev/null; find /Users -maxdepth 5 -name "*<song-name>.logic" 2>/dev/null
```

The most likely locations are:
- `~/Music/Logic/` (root Logic folder)
- `~/Music/Logic/<Artist Name>/` (artist subfolder)
- `~/Desktop/` (if they saved quickly)

If the find returns nothing → try keywords from the date or session:
```bash
find ~/Music/Logic -maxdepth 4 -iname "*<keyword>*" 2>/dev/null
```

If still nothing → ask the user where they saved it.

## Step 3 — Propose the rename

Show the user the current filename and propose the renamed version following the convention:

`Artist - Collection - TrackNumber - Song Title.logicx`

**Get explicit approval before renaming.** This modifies a file on the user's system.

> ✓ Checkpoint: User must confirm they want the rename before executing.

## Step 4 — Rename the file

```bash
mv "<current-path/current-name.logicx>" "<current-path/Artist - Collection - Track# - Song Title.logicx>"
```

Confirm the rename by running `ls -la "<current-path/>"`.

## Step 5 — Update the master session index

Read the current file at `/workspace/logic-master-session-index.md`.

If the collection already exists → add the new song to the table.

If the collection is new → add a new section with the table template, using the reference format at `references/session-index-template.md`.

If the song is the wrong track number compared to what's in the index → offer to re-sequence existing entries.

Lines to update:
- Add or update the row for this song
- Set Last Updated to today's date
- Set Status based on what the user tells you (default: In Progress)
- Add any other notes the user volunteers

## Step 6 — Cross-reference in ClickUp

Determine which ClickUp space and folder this belongs to:

| Artist | ClickUp Space | Folder |
|--------|--------------|--------|
| LitaMarie | Music | LitaMarie / ACE Funding |
| Other artist | Music | (artist folder) |

If the collection list doesn't exist in ClickUp yet → create a new list under the folder.

If the list exists → find the track task and update its status to "to do" or update the description with the new session path.

⚠️ **Common error:** New ClickUp spaces on Free/Unlimited tier only have "to do" and "complete" statuses. If you set `status: "in progress"` the API returns `"Status not found"`. **Fix:** Create the task without a status field (it defaults to "to do"), then note the actual status in the description field instead.

ClickUp API commands (use `network_mode: proxied`):

```bash
TOKEN=$(assistant credentials reveal --service clickup --field api_token)
# Create a task on a specific list:
curl -s -X POST "https://api.clickup.com/api/v2/list/<LIST_ID>/task" \
  -H "Authorization: $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "Track 0X: Song Title", "description": "Description here. Path: ~/path/to/file.logicx", "priority": 3}'

# Update a task:
curl -s -X PUT "https://api.clickup.com/api/v2/task/<TASK_ID>" \
  -H "Authorization: $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"description": "Updated description "}'

# Add a comment to a task:
curl -s -X POST "https://api.clickup.com/api/v2/task/<TASK_ID>/comment" \
  -H "Authorization: $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"comment_text": "Comment here", "notify": false}'
```

## Step 7 — Report the outcome

Tell the user what was done:
- Where the file was found
- What it was renamed to
- What the master index now shows
- What ClickUp task was created or updated

## SKILL COMPLETE WHEN

- [ ] `host_bash` rename command executed (with user approval)
- [ ] Master session index at /workspace/logic-master-session-index.md updated with new entry
- [ ] ClickUp task created or updated with session details
- [ ] User informed of the outcome
