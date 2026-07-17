---
name: "Hub Splitter — Split Overgrown Concept Index"
description: "Split an overgrown memory concept hub/index page by spinning related links into a new sub-hub, reducing the main hub's link count and keeping the structure navigable. Use when a concept hub has too many links to fit cleanly in context."
metadata:
  jason:
    emoji: 📂
    activation-hints:
      - hub has too many links
      - concept index is over capacity
      - main hub needs a sub-hub
      - too many articles in one hub page
    avoid-when:
      - the hub has fewer than ~30 links and no clear grouping for extraction
      - the user asked you to move a single link, not restructure the whole hub
    category: system
---

## When to Use

A concept hub page has grown past ~30-35 linked articles. The navigation is crowded, context injection is wasting space on low-priority links, and there's a clear natural grouping (daily work sessions, secondary references, utility articles) that can be extracted into a sub-hub. Use this when you need to make a hub leaner without losing information.

## Steps

### Step 1 — Read the hub and identify what to extract

Read the hub file at `/workspace/memory/concepts/<hub-name>.md`. Look for a natural grouping of links — things that share a common theme (e.g. all daily work-session articles, all secondary/reference articles, all utility utilities). The grouping should be coherent enough to make sense as its own page.

If the hub's `main:` frontmatter key matches its `slug:`, the links list is straight from the frontmatter `links:` field.

### Step 2 — Create the sub-hub page

Write a new concept file at `/workspace/memory/concepts/<sub-hub-name>.md` with:

```yaml
---
title: <Sub Hub Title — Descriptive>
slug: <sub-hub-name>
tags: [reference, hub, <grouping-tag>]
kind: index
main: <sub-hub-name>
links:
  - <copied links from main hub>
---
# <Sub Hub Title — Descriptive>

Short description of what this sub-hub collects and how it relates to the main hub.
```

### Step 3 — Edit the main hub

Use `file_edit` on the main hub file to:
1. **Remove** the extracted links from the frontmatter `links:` list
2. **Add** the sub-hub as a new link at the end: `- "<sub-hub-name> — <brief description> (sub-hub)"`

⚠️ CRITICAL: When editing YAML frontmatter links lists, match the EXACT whitespace. YAML list items start with `  - "..."` (two leading spaces, hyphen, space). If your replacement doesn't match carefully, the YAML breaks. When in doubt, use `file_read` to check the actual whitespace before editing.

### Step 4 — Verify the result

Read both files back and confirm:
- [ ] Main hub's `links:` count is reduced by the number extracted (target ~30-35)
- [ ] Sub-hub's `links:` contains all extracted entries
- [ ] Main hub has a `"<sub-hub-name> — description (sub-hub)"` entry at the end
- [ ] Sub-hub has a body that explains what it contains

## SKILL COMPLETE WHEN

- [ ] `file_write` created the new sub-hub file
- [ ] `file_edit` updated the main hub's frontmatter
- [ ] Both files confirmed readable with valid YAML

## Failure modes

- **YAML indentation mismatch:** If the edit produces invalid YAML, the file may load incorrectly. Verify by reading the file back after editing.
- **Link overlap:** If a link was already present in the sub-hub before extraction, the main hub may have lost it. Check that each extracted link was only in one place.
- **Sub-hub not discoverable:** The main hub MUST have the sub-hub link added. Without it, the sub-hub is an orphan.
