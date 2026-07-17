# Logic Session Manager — Failure Modes & Cached Values

## Failure modes

### `find` command returns nothing
- Check that the file was actually saved as a package (.logicx) not a folder (.logic)
- Try searching `~/Music/Logic/` recursively with `-name "*<keyword>*" -o -name "*<keyword>*"`
- The user may have saved it to a different location (Desktop, Documents, Downloads)

### `mv` fails with "Permission denied"
- The file may still be open in Logic Pro. Have the user close the session first.

### Multiple files match the search
- Ask the user which they mean before renaming

### ClickUp API returns `Status not found` (ECODE CRTSK_001 or ITEM_114)
- The space only has default "to do" and "complete" statuses. Free-tier and new spaces lack custom statuses like "in progress".
- **Fix:** Create the task without a status field (defaults to "to do"), or set `status: "to do"`, then note the actual status in the description.
- If on paid plan, first ensure "in progress" status exists in the space via the ClickUp UI or Space status API (POST `/space/{space_id}/status`).

### ClickUp API returns `null` for task ID (Task 01 first attempt)
- The failure is "Status not found" as above — retry without the status field.

### ClickUp API returns 404 on adding status to space
- POSTing to `/api/v2/space/{id}/status` returned 404. Status management may need UI or a different API endpoint on some accounts.

## Cached Values
- **Base URL:** https://api.clickup.com/api/v2
- **Auth:** `Authorization: $TOKEN` (raw token, no "Bearer " prefix)
- **Service name:** clickup
- **Credential retrieval:** `assistant credentials reveal --service clickup --field api_token`
- **Mac path for Logic sessions:** ~/Music/Logic/
- **LitaMarie folder:** ~/Music/Logic/LitaMarie Music/
- **Naming convention:** `Artist - Collection - Track# - Song Title.logicx`
- **Master session index file:** /workspace/logic-master-session-index.md

## Preconditions
- Need host_bash access (Mac)
- Need ClickUp API token configured in credential vault (service: clickup, field: api_token)
- User must approve the rename before executing (filesystem mutation)
