# Bridge Reorg — Failure Modes (from Jul 11 trace)

## 1. {{placeholder}} substitution does NOT work for ClickUp
`curl -H "Authorization: {{clickup:api_token}}"` returns `{"err":"Oauth token not found"}`.
Fix: `TOKEN=$(assistant credentials reveal --service clickup --field api_token)` then `-H "Authorization: $TOKEN"`.

## 2. Task IDs are full UUIDs
ClickUp returns short IDs in list views but the API requires the full UUID. Fetch the full ID via `GET /list/{id}/task` first.

## 3. DELETE returns empty body (204 No Content)
Python's `json.loads()` on an empty string raises `JSONDecodeError`. Catch this: try/except, return {} on empty.

## 4. Moving a task requires create + delete (no direct move)
Neither Calm Desk nor ClickUp has a PATCH-to-move endpoint that reliably re-parents. Pattern: `POST /list/{target}/task` with the same name/description → `DELETE /task/{old_id}`. Link preservation is manual.

## 5. Calm Desk tasks may lack descriptions after move
Creating a new task via POST /tasks only carries `title` and `context_id`. Check the original task's `note` field before deleting it and include it in the new body.

## 6. Rate limits
ClickUp has no documented rate limit issues at <100 calls/min. Calm Desk/Workspace Launcher is emergent.host — may have lower tolerance; batch deletes into chunks of 5-10.

## 7. ClickUp list delete is permanent (no undo)
Before deleting a list (e.g. template junk like "Get Started with ClickUp"), confirm it contains no real tasks.

## 8. Proxied bash can timeout on large fetches
`GET /list/{id}/task?include_closed=true` on lists with 12+ tasks takes <5s, but serialized requests across 15 spaces can hit the 120s default timeout. Set `timeout_seconds: 300` for multi-space surveys.
