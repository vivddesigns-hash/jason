# HQ API — Confirmed Working Endpoints (as of Jul 2 2026)

Base: `https://industry-33.emergent.host/api/`
Auth: `X-API-Key: <key>` header
Key: `hq_live_Au...` (51 chars, stored at `dmajor-hq:api_key` in credential vault)

## Confirmed Working

| Method | Endpoint | Returns |
|--------|----------|--------|
| GET | `/api/` | Health check: `{"message":"D-Major HQ online"}` |
| GET | `/api/tasks` | Full task list with status, priority, due_date, project_id |
| POST | `/api/documents` | Create document with title, content, collection, tags |
| GET | `/api/documents` | List all documents with library_id, collection, tags |
| DELETE | `/api/documents/<id>` | Delete a document: `{"deleted":true}` |
| GET | `/api/dashboard` | Executive dashboard: today's stats, action items, calendar |
| GET | `/api/projects` | All projects with name, description, status, color |
| GET | `/api/contacts` | Contact list with name, company, role, tags |
| GET | `/api/notes` | Notes/memos with title and content |

## Not Found (may not exist yet)

| Method | Endpoint | Notes |
|--------|----------|-------|
| GET | `/api/calendar` | Maybe different path, or not built |
| GET | `/api/emails` | Maybe different path, or not built |
| GET | `/api/memory` | Maybe different path, or not built |
| GET | `/api/settings` | Maybe different path, or not built |
| GET | `/api/tasks/summary` | Method Not Allowed (POST might exist) |

## POST /api/documents Payload Structure

```json
{
    "title": "Document Title",
    "collection": "Collection/Folder Name",
    "tags": ["tag1", "tag2"],
    "content": "Full markdown body..."
}
```

Response includes: id, status ("active"), source ("manual"), library_id (null if no collection match), is_public (false), created_at, updated_at.
