---
name: "Import ClickUp Tasks to Calm Desk"
description: "Pull tasks from ClickUp (across spaces, folders, and lists), map them to Calm Desk workspace contexts via the REST API, filter out onboarding junk, and create them as tasks with status mapping (active/parked). Use whenever tasks need to be migrated or synced from ClickUp into Calm Desk."
metadata:
  jason:
    emoji: 📥
    activation-hints:
      - import tasks from clickup into calm desk
      - sync clickup tasks to calm desk
      - migrate my tasks into calm desk
      - get all my clickup tasks into calm desk
      - bring my clickup tasks over
    avoid-when:
      - user wants to delete or reorganize existing Calm Desk tasks without a
        ClickUp source
      - user wants to build a task in Calm Desk from scratch
    category: productivity
---

# Import ClickUp Tasks to Calm Desk

Import tasks from ClickUp into Calm Desk via REST API, mapping each task to the right context by its space/folder.

## When to Use

- User asks to import their ClickUp tasks into Calm Desk
- User wants to sync or migrate their task system
- User says "make sure all my tasks are inside Calm Desk"
- User wants a full task inventory moved into workspace-specific contexts

## Setup

Two API connections needed:

### 1. ClickUp API
```
# Get team ID and spaces
curl -s "https://api.clickup.com/api/v2/team" -H "Authorization: $CLICKUP_TOKEN"

# Get spaces within a team
curl -s "https://api.clickup.com/api/v2/team/{team_id}/space" -H "Authorization: $CLICKUP_TOKEN"
```

### 2. Calm Desk API
```
API="https://workspace-launcher.preview.emergentagent.com/api"
KEY="$CALM_DESK_KEY"

# Verify access
curl -s "$API/contexts" -H "X-API-Key: $KEY"
```

## Procedure

### Step 1 — Pull all ClickUp tasks

Loop through each space, folder, and list. The ClickUp API structure:
- `/team/{id}/space` → spaces
- `/space/{id}/folder` → folders (or folderless lists at `/space/{id}/list`)
- `/folder/{id}/list` → lists
- `/list/{id}/task?archived=false&subtasks=true` → tasks

For each task, capture: `space`, `folder`, `list`, `id`, `name`, `status`, `tags`.

Save all tasks to a JSON file (`/tmp/clickup_tasks.json`).

### Step 2 — Get Calm Desk contexts
```
curl -s "$API/contexts" -H "X-API-Key: $KEY"
```
Build a `ctx_by_name` map from the response.

### Step 3 — Map ClickUp spaces/folders to Calm Desk contexts

```python
def map_task_to_context(task):
    space = task["space"]
    folder = task["folder"]
    list_name = task["list"]
    name = task["name"]
    
    # Skip ClickUp onboarding tasks
    if "Get Started with ClickUp" in list_name:
        return None
    # Skip generic placeholder tasks
    if name in ["Task 1", "Task 2", "Task 3", "\u200eTask 1", "\u200eTask 2"]:
        return None
    
    # Product Builds space — map by folder name
    if space == "Product Builds":
        if folder == "KFM Build": return "KFM Build"
        elif folder == "HQ Platform": return "HQ Platform"
        elif folder == "Workspace Launcher": return "General Admin"
        # other folders map to General Admin or specific contexts
        return "General Admin"
    
    # Music space — map by folder name
    if space == "Music":
        if "LitaMarie" in folder: return "LitaMarie Music"
        elif "D-Major" in folder: return "Dwight D-Major Jones"
        return "LitaMarie Music"
    
    # Business Clients = Ashlan Clinic
    if space == "Business Clients": return "Ashlan Clinic"
    
    # Business Ops — Infrastructure to HQ Platform, rest to General Admin
    if space == "Business Ops":
        if folder == "Infrastructure": return "HQ Platform"
        return "General Admin"
    
    # Personal & Community — map by folder
    if space == "Personal & Community":
        if folder == "Football": return "Kairo Jones Football"
        elif folder == "BCCF / Faith": return "BCCF"
        elif folder == "Personal Brand": return "Dwight Jones UK"
        elif folder == "VIVD Media": return "VIVD Media"
        return "General Admin"
    
    return "General Admin"
```

⚠️ **This mapping is workspace-specific.** Adjust it to match Dwight's actual contexts in Calm Desk. Get the context list first, then build the mapping.

### Step 4 — Create tasks in Calm Desk

For each non-skipped task:
1. POST to `$API/tasks` with `{"context_id": ctx_id, "title": task_name}`
2. If task status is "blocked" in ClickUp, PATCH to park it: `{"status": "parked"}`
3. Count created vs skipped vs failed

### Step 5 — Verify
```
curl -s "$API/contexts" -H "X-API-Key: $KEY" | python3 -c "
import json, subprocess, sys
contexts = json.load(sys.stdin)
for c in contexts:
    tasks = subprocess.run(['curl', '-s', f'{API}/contexts/{c[\"id\"]}/tasks', ...], capture_output=True, text=True)
    print(f'{c[\"name\"]}: {len(json.loads(tasks.stdout))} tasks')
"
```

## Status mapping

| ClickUp Status | Calm Desk Status |
|---|---|
| `to do` | `active` |
| `in progress` | `active` |
| `blocked` | `parked` |
| `completed` / `done` | `done` |

## Known failure modes
- **Calm Desk API key expires or changes** (happened Jul 9 during Emergent Google Sign-in work). Check with `curl -s "$API/contexts" -H "X-API-Key: $KEY"` before importing. If 401, key needs refreshing.
- **ClickUp API token scoping** — the Jason token has access to more teams than Dwight's personal token. Use `jason_api_token` field for full access.
- **ClickUp pagination** — ClickUp defaults to max 100 tasks per request. The task fetch may truncate if a list has >100. Monitor for `truncated: true` in response.

## SKILL COMPLETE WHEN

- [ ] All ClickUp tasks pulled, filtered, and saved to JSON
- [ ] Each task created in its mapped Calm Desk context
- [ ] Blocked tasks parked in Calm Desk
- [ ] Summary reported (created, skipped, failed, per-context counts)
- [ ] Verification confirms task counts match expectations
