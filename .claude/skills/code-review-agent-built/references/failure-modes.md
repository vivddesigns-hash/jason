# Failure Modes — Code Review

## GitHub API Tarball Downloads
- Large repo tarballs downloaded via `GET /repos/{owner}/{repo}/tarball` can have corrupted filenames when they contain special characters or UTF-8. Preferred approach: fetch individual files via `GET /repos/{owner}/{repo}/contents/{path}`.
- GitHub's contents API returns JSON with `"content"` as base64-encoded file data. Decode with `base64.b64decode()` before analysis.
- Private repos require an authenticated `Authorization: Bearer <token>` header. Connect GitHub OAuth in Jason settings first.

## Very Large Files
- Content appends to README on each mode-switch. After several inspections, the README can grow past 100KB from accumulated inspection notes.
- server.py files for full-stack apps can exceed 2000 lines. Read in manageable chunks (200-300 lines at a time) to avoid hitting tool limits.

## Missing Imports
- A blank white page / component crash is often caused by a missing or incorrect `import` statement. Check the import block of the crash-causing component first.

## Missing Auth on Backend Endpoints
- The most common multi-tenant security gap: endpoints that do data CRUD (create/read/update/delete) but are missing a `require_user` dependency or ownership check. Check every endpoint for its security dependency, not just the ones that look sensitive.