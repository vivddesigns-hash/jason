---
name: "Bridge Reorg — Audit + Re-sync Tasks Across Both Sides"
description: "Audit Calm Desk and ClickUp for misplaced tasks, drift, and orphans, then move/delete/recreate to sync them. Use when tasks are in the wrong space, items appear on only one side, or the Bridge needs a cleanliness pass."
metadata:
  jason:
    emoji: 🔄
    activation-hints:
      - needs to reorganise all calm spaces
      - audit the bridge
      - re-sync clickup and calm desk
      - bridge cleanup
      - tasks are in the wrong space
    category: productivity
---

## When to Use

Run this when tasks are in the wrong Calm Space or ClickUp folder, when items exist on only one side of the Bridge, or when the user says "reorganise all of my calm spaces" or "update the bridge" with a cleanup intent. Do NOT use for adding a single new project — that's `bridge-onboarding`.

## Overview

1. Survey both sides (Calm Desk + ClickUp) independently
2. Build a combined picture and flag drift
3. Execute moves, creates, and deletes to align
4. Verify the result

## Step 1 — Survey Calm Desk

```bash
curl -s -H "X-API-Key: $CALM_DESK_API_KEY" \
  https://workspace-launcher.emergent.host/api/contexts
```

For each context (Calm Space), fetch its tasks:

```bash
curl -s -H "X-API-Key: $CALM_DESK_API_KEY" \
  https://workspace-launcher.emergent.host/api/contexts/{id}/tasks
```

Save the full output per space, including task IDs and `note` fields.

## Step 2 — Survey ClickUp

```bash
TOKEN=$(assistant credentials reveal --service clickup --field api_token)
```

Fetch the team ID first:
```bash
curl -s -H "Authorization: $TOKEN" https://api.clickup.com/api/v2/team
```

Then map spaces → folders → lists → tasks:
```bash
curl -s -H "Authorization: $TOKEN" https://api.clickup.com/api/v2/team/{team_id}/space
curl -s -H "Authorization: $TOKEN" https://api.clickup.com/api/v2/space/{space_id}/folder
curl -s -H "Authorization: $TOKEN" https://api.clickup.com/api/v2/list/{list_id}/task?include_closed=true
```

Include closed tasks — they may hold items that should be opened or moved.

## Step 3 — Identify drift

Compare the two surveys. Look for:
- **Misplaced:** task in a Calm Space / ClickUp folder that doesn't match its content (e.g. "Go Deeper session with Dwight" filed under "Reggae Revolution" when it belongs in "KFM Build")
- **Orphans:** task on one side with no equivalent on the other
- **Duplicates:** same task created twice (often from earlier test runs)
- **Template junk:** ClickUp onboarding lists ("Get Started with ClickUp", "Project 1", "Project 2") that have no real tasks

Build a list of actions: CREATE, MOVE (create in target + delete source), DELETE.

⚠️ **Point-of-action warning:** Before deleting anything, confirm it has no real content. A list with "Task 1", "Task 2", "Task 3" names is template junk. A list with meaningful names ("Launch Autopilot") is not.

## Step 4 — Execute on Calm Desk

**Move a task** (PATCH context_id alone may not re-parent — use create + delete):
```bash
# Create in target space
curl -s -X POST -H "X-API-Key: $CALM_DESK_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"title":"...","context_id":"{target_context_id}","note":"..."}' \
  https://workspace-launcher.emergent.host/api/tasks

# Delete from source
curl -s -X DELETE -H "X-API-Key: $CALM_DESK_API_KEY" \
  https://workspace-launcher.emergent.host/api/tasks/{old_id}
```

**Delete a duplicate:**
```bash
curl -s -X DELETE -H "X-API-Key: $CALM_DESK_API_KEY" \
  https://workspace-launcher.emergent.host/api/tasks/{id}
```

## Step 5 — Execute on ClickUp

**Move a task** (ClickUp also wants create + delete):
```bash
# Fetch original for description
curl -s -H "Authorization: $TOKEN" \
  https://api.clickup.com/api/v2/task/{old_id}

# Create in target list
curl -s -X POST -H "Authorization: $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"...","description":"...","status":"to do"}' \
  https://api.clickup.com/api/v2/list/{target_list_id}/task

# Delete from source
curl -s -X DELETE -H "Authorization: $TOKEN" \
  https://api.clickup.com/api/v2/task/{old_id}
```

**Delete a template junk list:**
```bash
curl -s -X DELETE -H "Authorization: $TOKEN" \
  https://api.clickup.com/api/v2/list/{list_id}
```

⚠️ **No undo on list delete.** Confirm it has no real tasks first.

**Close obsolete tasks** (status = "complete") rather than deleting them:
```bash
curl -s -X PUT -H "Authorization: $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"status":"complete"}' \
  https://api.clickup.com/api/v2/task/{id}
```

**Rename a folder** to "retired" instead of deleting it:
```bash
curl -s -X PUT -H "Authorization: $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"Old Folder Name (retired)"}' \
  https://api.clickup.com/api/v2/folder/{folder_id}
```

## Step 6 — Add missing Calm Space tasks to ClickUp

When adding project tasks that exist in Calm Desk but not in ClickUp, create them in the right folder/list:

```bash
curl -s -X POST -H "Authorization: $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"Task name","status":"to do"}' \
  https://api.clickup.com/api/v2/list/{target_list_id}/task
```

## SKILL COMPLETE WHEN

- [ ] All misplaced items moved to correct space/folder on BOTH sides
- [ ] All duplicates deleted
- [ ] Template junk lists removed from ClickUp
- [ ] Obsolete tasks closed (not deleted)
- [ ] User shown a summary of changes, or the progress card shows all steps completed and verified
