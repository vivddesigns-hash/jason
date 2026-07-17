# Bridge Reorg — Access Patterns

## Calm Desk REST API
- **Base URL:** `https://workspace-launcher.emergent.host/api`
- **Auth header:** `X-API-Key: $CALM_DESK_API_KEY`
- **Key endpoints:**
  - `GET /contexts` — list all Calm Spaces
  - `GET /contexts/{id}/tasks` — list tasks in a space
  - `POST /tasks` — create task (body: {title, context_id, note})
  - `PATCH /tasks/{id}` — update task (body: {context_id} to move, {status} to complete)
  - `DELETE /tasks/{id}` — delete task

## ClickUp REST API
- **Base URL:** `https://api.clickup.com/api/v2`
- **Auth:** `TOKEN=$(assistant credentials reveal --service clickup --field api_token)` — run inline, pass raw via `-H "Authorization: $TOKEN"`
- **WARNING:** The `{{placeholder}}` injection syntax does NOT substitute for ClickUp. Always use the reveal-inline pattern.
- **Which token:** `clickup:api_token` = Jones Consultants Workspace (90121827681). `clickup:jason_api_token` = Jason's Workspace (90121881470).
- **Key endpoints:**
  - `GET /team/{team_id}/space` — list spaces
  - `GET /space/{id}/folder` — list folders (+ their child lists)
  - `GET /folder/{id}` — get folder details (includes lists)
  - `GET /list/{id}/task?include_closed=true` — list all tasks (incl. closed)
  - `POST /space/{id}/folder` — create folder
  - `POST /folder/{id}/list` — create list in folder
  - `POST /list/{id}/task` — create task (body: {name, status, description?})
  - `PATCH /task/{id}` — update task
  - `PUT /task/{id}` — update status (body: {status: "complete"})
  - `DELETE /task/{id}` — delete task
  - `DELETE /list/{id}` — delete list
- **Task IDs:** Full UUIDs only (e.g. `e2162dae-1d2d-4179-be85-f3c51e38a987`). Short IDs (first 8 chars) do NOT work with the API.

## Errors to watch for
- **"Oauth token not found"** (ECODE OAUTH_019) — the {{placeholder}} didn't substitute. Re-run with `TOKEN=$(...)` inline.
- **JSONDecodeError "Expecting value"** — the response was empty (typically a DELETE returning 204). Use try/except to handle empty bodies.
- **404 on task move** — likely used a short ID. Use the full UUID.
- **Network access:** All calls go through proxied bash.
