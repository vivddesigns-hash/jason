---
name: "Push Document to HQ"
description: "Push a markdown or text document to D-Major HQ's document library via the authenticated REST API. Creates a document with title, content, collection (folder), and tags. Documents pushed to HQ become accessible in the HQ web interface and are organized by collection. Use whenever you need to store a research file, spec, guide, notes, or output in HQ as the system of record instead of leaving it in the assistant's workspace."
metadata:
  jason:
    emoji: 📄
    category: integration
---

# Push Document to HQ

Push a markdown/text document to D-Major HQ via the authenticated REST API.

## When to Use

Use this skill when:
- You have a local file that should live in HQ as the system of record instead of the assistant workspace
- The user asks you to store a document, research, spec, or guide in HQ
- You created a file locally (e.g., `.md` research, prompt, guide) and need to file it permanently
- The user has multiple businesses and the document belongs to a specific workspace (Ashlan, Projects, etc.)

## Prerequisites

- HQ API key stored as `dmajor-hq:api_key` in the credential vault (confirmed working: `hq_live_Au...` format)
- HQ API reachable at `https://industry-33.emergent.host`
- Network mode `proxied` enabled on bash commands

## Step 1 - Read the source file

```bash
cat /workspace/<filename>.md
```

## Step 2 - Choose the right collection

Documents are organized by collection (acts as a folder/category):

| Collection | When to use |
|---|---|
| `Projects` | Build specs, prompts, architecture docs, workflow designs |
| `Ashlan Clinic` | Anything clinic-related: research, guides, staff docs |
| `Brand & Strategy` | Brand profiles, marketing briefs, strategy docs |
| `System` | Internal system docs, setup instructions (minimal) |

If none of these fit, create a new collection name that matches the business or project.

## Step 3 - Push the document

Use a Python script to clean the content (strip markdown header noise) and POST via curl:

```bash
python3 << 'PYEOF'
import json, subprocess

HQ_KEY = subprocess.check_output([
    "assistant", "credentials", "reveal",
    "--service", "dmajor-hq", "--field", "api_key"
], text=True).strip()

with open("/workspace/<filename>.md") as fh:
    content = fh.read()

# Strip markdown H1 headers, instruction blocks, and horizontal rules
lines = content.split('\n')
body_lines = []
skip_header = True
for line in lines:
    if skip_header and (line.startswith('#') or line.startswith('**Paste') or line.strip() == '---' or line.strip() == ''):
        continue
    skip_header = False
    body_lines.append(line)
body = '\n'.join(body_lines).strip()

payload = json.dumps({
    "title": "<Title Here>",
    "collection": "Ashlan Clinic",  # Change to appropriate collection
    "tags": ["tag1", "tag2"],
    "content": body
})

result = subprocess.run([
    "curl", "-s", "--max-time", "10", "-X", "POST",
    "-H", f"X-API-Key: {HQ_KEY}",
    "-H", "Content-Type: application/json",
    "https://industry-33.emergent.host/api/documents",
    "-d", payload
], capture_output=True, text=True)

try:
    resp = json.loads(result.stdout)
    print(f"OK: {resp.get('title')} | Collection: {resp.get('collection')} | ID: {resp.get('id')}")
except:
    print(f"FAILED: {result.stdout[:500]}")
    exit(1)
PYEOF
```

⚠️ **CRITICAL:** Replace `<filename>.md`, `<Title Here>`, the collection name, and tags before running. This is not a copy-paste script without edits.

## Step 4 - Verify in HQ

Tell the user the document was created with its collection and ID. They can see it in HQ's document library if they navigate there.

## Step 5 - Clean up the local file (optional)

If the file was a temporary workspace file that shouldn't persist locally:

```bash
rm /workspace/<filename>.md
```

## Collections Reference

Known valid collections from API observation:
- Brand & Strategy
- System
- Projects
- Ashlan Clinic

Collections are case-sensitive. Unknown collection names create new collections automatically.

## SKILL COMPLETE WHEN

- [x] Document POST returned a `201`-like success with `id` field
- [x] User knows where the document was filed
- [x] Local temp file cleaned up (if applicable)
