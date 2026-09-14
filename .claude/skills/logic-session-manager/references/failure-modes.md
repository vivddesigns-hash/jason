# Logic Session Manager — Failure Modes & Cached Values

## Failure modes

### `find` command returns nothing
- Check that the file was actually saved as a package (.logicx) not a folder (.logic)
- Try searching `~/Music/Logic/` recursively with `-name "*<keyword>*" -o -name "*<keyword>*"`
- The user may have saved it to a different location (Desktop, Documents, Downloads)
- Remember: the found filename will very likely already have a `YYYY-MM-DD_`
  prefix from the local watcher — search patterns using `*<keyword>*`
  (wildcard on both sides) still match, since the original name is preserved
  as a suffix. Don't assume an exact/prefix match will find it.

### Multiple files match the search
- Ask the user which they mean before recording it in the index

### Renaming a file inside a `.logicx` package breaks the project — proven, not theoretical
- **This actually happened**, on 2026-09-14: renaming an audio file inside a
  `.logicx` package's `Media/Audio Files` folder (even with Logic fully
  closed) caused Logic to show "Audio file not found" the next time that
  project was opened — the track was unrecoverable without manually
  relocating the file. Confirmed with a disposable test copy, not assumed.
  Logic's project data references audio by exact filename, independent of
  package-vs-folder save format.
- **This is why this skill never renames anything inside a `.logicx`
  package, and never renames the outer package either** — that job belongs
  entirely to the local watcher (`~/Library/Scripts/autorename-watcher.py`),
  which only renames the *outer* project folder, and only once `lsof`
  confirms nothing has any file inside it open. If you ever find yourself
  about to run `mv` on anything under a `.logicx` path for any reason —
  stop. That's the watcher's job, not this skill's.

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
- **Filename convention (applied by the watcher, not this skill):**
  `YYYY-MM-DD_ParentFolder_OriginalName.logicx`, date = the project's real
  creation date, not the day it was renamed
- **Master session index file:** /workspace/logic-master-session-index.md

## Preconditions
- Need host_bash access (Mac)
- Need ClickUp API token configured in credential vault (service: clickup, field: api_token)
- This skill never renames files — no filesystem-mutation approval needed for that step
