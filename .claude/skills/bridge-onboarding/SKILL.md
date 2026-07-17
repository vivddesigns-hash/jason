---
name: "The Bridge — Onboard a Project to ClickUp + Calm Desk"
description: "Onboard a new project to both ClickUp and Calm Desk simultaneously (The Bridge). Creates ClickUp folder + list + tasks under the right space, and Calm Desk Calm Space + tasks in parallel. Use whenever Dwight says 'onboard to the bridge', 'update the bridge', or asks to set up a new project in both systems."
metadata:
  jason:
    emoji: 🌉
    activation-hints:
      - user says 'onboard' or 'update the bridge' or 'set up the bridge'
      - new project needs ClickUp folder + Calm Desk Calm Space
      - need to create both PM track and workspace track for a new
        business/client/project
      - Dwight asks to put something in ClickUp and Calm Desk
    avoid-when:
      - only need ClickUp — use clickup-api directly
      - only need Calm Desk — use calm-desk-api directly
      - migrating existing tasks from ClickUp to Calm Desk — use
        import-clickup-to-calmdesk skill instead
    category: productivity
---

# The Bridge — Onboard a Project to ClickUp + Calm Desk

💡 **Anchoring fact:** "The Bridge" = ClickUp (PM track) + Calm Desk (workspace track). Written into Dwight's SOUL.md as the permanent naming convention (Jul 11, 2026). Every new project that lands in both systems is "onboarded to The Bridge."

## When to Use

USE THIS SKILL WHEN:
- Dwight says "onboard X to the bridge" or "update the bridge"
- A new project, business, or client needs setup in BOTH ClickUp and Calm Desk
- You need to create a ClickUp folder, list, tasks AND a Calm Space with tasks in parallel
- Dwight says "add it to ClickUp and Calm Desk" in any form

Do NOT use this skill when:
- Only one system is needed (ClickUp-only or Calm Desk-only — handle directly)
- You're importing/migrating existing ClickUp tasks into Calm Desk (use `import-clickup-to-calmdesk` skill instead)
- The project already exists in both systems and just needs an update (handle directly)

## What Gets Created

**ClickUp track (PM):**
- Folder under the correct Space (Product Builds / Music / Business Clients / Business Ops / Personal & Community)
- List inside the folder (typically "Action Plan" for first setup, or whatever is appropriate)
- Tasks with custom fields: Build Phase, Stakeholder, Business Area (if option exists)

**Calm Desk track (workspace):**
- Calm Space with a relevant icon/emoji
- Tasks inside that Calm Space

## Prerequisites

- The **ClickUp space** must already exist. The 5-space layout is: Product Builds (90127970165), Music (90128237371), Business Clients (90128237372), Business Ops (90128237373), Personal & Community (90128237374).
- You need the **ClickUp Jason API token** (`clickup:jason_api_token` in vault, retrieved via `assistant credentials reveal --service clickup --field jason_api_token`)
- You need the **Calm Desk API key** (`$CALM_DESK_API_KEY`)
- Both networks must use `network_mode: proxied`

## Steps

### Step 1 — Gather the info

Before starting, confirm with Dwight (or know from context):

- **Business/project name** (e.g. "Done Deal Maintenance")
- **Which ClickUp space** it belongs to (usually Business Clients for client businesses)
- **Calm Desk icon** — pick a fitting emoji
- **Task list** — what are the initial action items? If unknown, create a simple placeholder list Dwight can flesh out later

### Step 2 — Create the ClickUp folder

```bash
jason_TOKEN=$(assistant credentials reveal --service clickup --field jason_api_token 2>&1)

FOLDER=$(curl -s -X POST "https://api.clickup.com/api/v2/space/{SPACE_ID}/folder" \
  -H "Authorization: $jason_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "{PROJECT_NAME}"}')
```

Extract the folder ID. Then create a list inside it:

```bash
LIST=$(curl -s -X POST "https://api.clickup.com/api/v2/folder/{FOLDER_ID}/list" \
  -H "Authorization: $jason_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "Action Plan", "content": "{optional description}"}')
```

### Step 3 — Create ClickUp tasks

Create each task with custom fields. First fetch the list's custom fields to get dropdown option IDs:

```bash
curl -s -H "Authorization: $jason_TOKEN" "https://api.clickup.com/api/v2/list/{LIST_ID}/field"
```

Known custom field IDs (stable as of Jul 8):
- Build Phase: `5a74b47c-3d58-41cd-8bac-f87e70e3e4ca` (options: Discovery/Planning/Build/Testing/Launch/Maintenance)
- Stakeholder: `5f373181-f2e0-4caa-a572-a70f591954c5` (options: Dwight/Shelita/Glenn/Jason)
- Business Area: `c5ce32f4-790e-4121-aa7e-af732de4d4e5` — requires a predefined option to exist. If the project doesn't have one, flag it to Dwight.
- Blocked By: `9dc562f7-b483-433e-818f-ac91b325f526` (text field)

Create each task:

```bash
curl -s -X POST "https://api.clickup.com/api/v2/list/{LIST_ID}/task" \
  -H "Authorization: $jason_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "{TASK_NAME}", "content": "{DESCRIPTION}", "custom_fields": [...]}'
```

> ⚠️ Business Area dropdown: If the project's Business Area option doesn't exist yet, you cannot add it via API. Skip the Business Area custom field on the tasks and tell Dwight to add the option in the ClickUp UI.

### Step 4 — Create the Calm Desk Calm Space

```bash
CONTEXT=$(curl -s -X POST "https://workspace-launcher.emergent.host/api/contexts" \
  -H "X-API-Key: $CALM_DESK_KEY" \
  -H "Content-Type: application/json" \
  -d '{"name": "{PROJECT_NAME}", "icon": "{EMOJI}"}')
```

Extract the context ID from the response.

### Step 5 — Create Calm Desk tasks

⚠️ CRITICAL: The correct endpoint is `POST /api/tasks` with `context_id` in the body, NOT `POST /api/contexts/{id}/tasks` which returns 405.

```bash
curl -s -X POST "https://workspace-launcher.emergent.host/api/tasks" \
  -H "X-API-Key: $CALM_DESK_KEY" \
  -H "Content-Type: application/json" \
  -d '{"title": "{TASK_TITLE}", "context_id": "{CONTEXT_ID}"}'
```

Create all tasks in parallel where possible using separate curl calls in the same bash command.

### Step 6 — Verify

Check both systems have the right count:

```bash
# ClickUp
curl -s -H "Authorization: $jason_TOKEN" \
  "https://api.clickup.com/api/v2/list/{LIST_ID}/task" | python3 -c "import json,sys; print(len(json.load(sys.stdin).get('tasks',[])))"

# Calm Desk
curl -s -H "X-API-Key: $CALM_DESK_KEY" \
  "https://workspace-launcher.emergent.host/api/contexts/{CONTEXT_ID}/tasks" | python3 -c "import json,sys; data=json.load(sys.stdin); tasks=data if isinstance(data,list) else data.get('tasks',[]); print(len(tasks))"
```

### Step 7 — Report

Tell Dwight what was created:
- ClickUp: which space, folder name, list name, task count
- Calm Desk: Calm Space name, icon, task count
- Any flags (e.g. missing Business Area option, ClickUp task limit approached)

## Failure Modes & Gotchas

### Calm Desk task creation returns empty list
If tasks were created but the context shows 0 tasks when you verify:
- You likely used `POST /api/contexts/{id}/tasks` which returns 405 Method Not Allowed
- Use `POST /api/tasks` with `context_id` in the body instead

### ClickUp custom statuses can't be set
The public ClickUp API only returns/completes for statuses. Custom statuses added in the UI can't be set via API. That's fine — tasks default to "to do."

### Business Area dropdown missing option
Custom field dropdown options can't be added via API. If the project name isn't in the dropdown, the tasks will have a blank Business Area. Flag this clearly to Dwight so he can add it in the ClickUp UI.

### Calm Desk task field name
Use `title` for the task name field. Not `name`. Not `text`. Not `content`. The API accepts `title`.

## SKILL COMPLETE WHEN

- [ ] ClickUp folder + list created under the correct space
- [ ] Tasks created in ClickUp (verify count)
- [ ] Calm Desk Calm Space created with icon
- [ ] Tasks created in Calm Desk (verify count)
- [ ] Dwight informed of what was created and any flags
