---
name: "Code Review — Agent-Built Products"
description: "Download source files from a GitHub repo (private or public), read all frontend components and backend code, and compile a full structured code review with severity-classified findings. Use when a product built by an AI agent needs a code-level audit before it goes to beta testers or customers."
metadata:
  jason:
    emoji: 🔍
    activation-hints:
      - review the code for
      - do a code review of
      - code-level audit of
      - inspect the source code of
      - check the code quality of
    avoid-when:
      - The user wants a UI-only inspection via browser automation or
        computer-use. This skill is for reading source code from a GitHub repo,
        not for visual QA.
    category: development
---

# Code Review — Agent-Built Products

## When to Use

Use when a product built by an AI agent needs a code-level audit before releasing to beta testers or customers. This skill catches root-cause bugs, multi-tenant security holes, missing error handling, hardcoded values, and UX regressions that UI-only inspection misses.

Do not use this for visual QA or browser-based inspection — that is a separate skill. This is source-code only.

## Prerequisites

- GitHub OAuth connected in Jason (for private repo access)
- The GitHub repo URL (owner/repo format)

## Procedure

### Step 1 — Get the repo source

First, decide whether to download a tarball or fetch individual files.

**If the repo is small** (< 50 files) → fetch individual files via the GitHub Contents API:
```
GET https://api.github.com/repos/{owner}/{repo}/contents/{path}
Authorization: Bearer <token>
```
Each response contains `"content"` (base64-encoded). Decode and save.

**If the repo has many files** → download the tarball:
```
curl -L -H "Authorization: Bearer <token>" \
  https://api.github.com/repos/{owner}/{repo}/tarball/HEAD \
  -o /workspace/{repo}-source.tar.gz
```

**Known failure mode:** Large tarballs can have corrupted filenames from UTF-8 encoding issues. If extraction produces garbled filenames, fall back to fetching individual source files via the Contents API.

### Step 2 — Map the file structure

List the extracted directory tree to understand the architecture:

```bash
find /workspace/{repo}-dir -type f | grep -E '\.(py|js|jsx|ts|tsx|css|html)$' | head -60
```

Identify the key layers:
- Frontend entry point (App.js/jsx, main.tsx)
- API client / network layer
- Backend server entry point (server.py, app.js, main.py)
- Component files
- Config files (tailwind, postcss, environment)

### Step 3 — Read the critical files

Read files in this priority order, in parallel where independent:

**Frontend:**
1. App.js/jsx — routing, app shell, error boundaries
2. Main component(s) — Desk.jsx, Dashboard.jsx, etc.
3. Auth/SignIn components
4. API client library
5. Individual page/view components (one by one)
6. CSS / design token files (tailwind.config, index.css, App.css)

**Backend:**
1. Server entry point — focus on:
   - Middleware (auth guards, CORS)
   - `require_user` / authentication helpers
   - Every route handler — check EACH one for `Depends(require_user)`
   - Ownership validation on data-access routes
2. Data models / schemas (Pydantic models)
3. Admin endpoints
4. Billing / payment routes
5. Any webhook handlers

**Desktop (if Electron):**
1. main.js — contextIsolation, nodeIntegration, preload path
2. preload.js — what IPCs are exposed to renderer

### Step 4 — Build the classification system

Read the Minimum Expectations checklist (`/workspace/agent-build-minimum-expectations.md`) for reference on what to check. Classify every finding into:

| Severity | Criteria | Examples |
|---|---|---|
| **BLOCKER** | Security hole, crash, or data loss. Cannot ship. | Missing auth on endpoint, missing import causing crash, no error boundary, SSRF vector |
| **MAJOR** | Bad UX, data integrity issue, or significant functional gap | Wrong keyboard behavior, missing CRUD operations, hardcoded values, wrong app name |
| **MINOR** | Polish, edge cases, defense-in-depth | No rate limiting, missing validation, cosmetic inconsistencies |

### Step 5 — Write the report

Save the report to `/workspace/data/{repo-name}-code-review-{date}.md`. Structure it:

```markdown
# {Product Name} — Code Review ({date})

**Repo:** {owner}/{repo}
**Scope:** {web, desktop, or both}
**Reviewer:** Jason

---

## Executive Summary

Brief high-level assessment. What's the overall state? What's the most important thing to fix?

---

## BLOCKERS (N)

### B1. Title
**Severity: CRITICAL|HIGH**
**File:** path/to/file.py line NNN

Description. Impact. Fix recommendation.

---

## MAJORS (N)

### M1. Title
**Files:** path/to/file.jsx line NNN

Description. Fix recommendation.

---

## MINORS (N)

### m1. Title

---

## POSITIVE FINDINGS

### p1. Title

What's genuinely good about this codebase.

---

## FIX PRIORITY TABLE

| # | Severity | Issue | Effort |
|---|---|---|---|
| B1 | CRITICAL | ... | Medium |
```

### Step 6 — Create a fix prompt

Create a paste-ready fix prompt for the building agent (e.g. Emergent) at `/workspace/{repo-name}-fix-prompt.md`. Include exact file names, line numbers, code snippets showing the current state, and the corrected code. Group by severity.

### Step 7 — Offer the fix prompt

Show the fix prompt as a copy block so the user can paste it to the building agent.

## SKILL COMPLETE WHEN

- [ ] All source files downloaded or fetched
- [ ] Every route handler checked for auth + ownership
- [ ] Frontend component tree traced for crash points
- [ ] Report saved to `/workspace/data/{repo}-code-review-{date}.md`
- [ ] Fix prompt saved at `/workspace/{repo}-fix-prompt.md`
- [ ] User offered the fix prompt as a copy block
