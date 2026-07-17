---
name: "Extract Insights from Conversation Transcript"
description: "Pull a full conversation transcript from an API endpoint, save it to file, then analyze and extract change requests, decisions, requirements, bug reports, and feature ideas. Use when the user wants a structured summary of a long conversation history, or when conversations appeared to be 'lost' due to display bugs."
metadata:
  jason:
    emoji: 🔍
    activation-hints:
      - analyze a conversation
      - extract insights from chat
      - read the transcript
      - compile the change list
      - what did we discuss in that session
      - pull all messages from the chat
      - figure out what changes are needed from the conversation
    category: productivity
---

## When to Use

Pull a full conversation transcript from an API endpoint, save it to a local file, then analyze it to extract actionable items: change requests, decisions, requirements, bug reports, feature ideas, writing rules, and agent behavior rules. Use when the user asks you to figure out what was discussed, what changes were requested, or what needs to be done based on a long conversation history.

## Setup

You need:
- The API endpoint that serves the conversation messages
- The conversation/session ID
- Authentication credentials (typically an API key from `assistant credentials reveal`)
- A file path for the saved transcript (typically `/workspace/`)

## Step 1 - Fetch the conversation data

```bash
HQ_KEY=$(assistant credentials reveal --service <service-name> --field api_key 2>/dev/null)
curl -s -H "X-API-Key: $HQ_KEY" <endpoint-url>/<session-id> | python3 -c "
import sys, json
data = json.load(sys.stdin)
print(f'Total messages: {len(data)}')
recent = [m for m in data if m.get('created_at','')[:10] >= '<cutoff-date>']
print(f'Messages from cutoff onwards: {len(recent)}')
" 2>&1
```

Replace `<service-name>`, `<endpoint-url>`, `<session-id>`, and `<cutoff-date>`.

⚠️ CRITICAL: Before analyzing, verify the conversation contains the expected message range. If the count looks wrong (e.g. only showing old messages), the API may have a display limit bug — check with the developer.

## Step 2 - Save the full transcript to file

```bash
HQ_KEY=$(assistant credentials reveal --service <service-name> --field api_key 2>/dev/null)
curl -s -H "X-API-Key: $HQ_KEY" <endpoint-url>/<session-id> 2>&1 | python3 -c "
import sys, json
data = json.load(sys.stdin)
with open('/workspace/<filename>', 'w') as f:
    for i, m in enumerate(data):
        role = m.get('role', '?')
        content = m.get('content', '')
        created = m.get('created_at', '?')[:19]
        f.write(f'--- Message {i+1} [{role}] [{created}] ---\n')
        f.write(content)
        f.write('\n\n')
print(f'Saved {len(data)} messages')
" 2>&1
```

## Step 3 - Preview recent messages

Print only messages from the relevant date range, with full user content and truncated assistant content, to understand what the conversation was about:

```bash
HQ_KEY=$(assistant credentials reveal --service <service-name> --field api_key 2>/dev/null)
curl -s -H "X-API-Key: $HQ_KEY" <endpoint-url>/<session-id> 2>&1 | python3 -c "
import sys, json
data = json.load(sys.stdin)
recent = [m for m in data if m.get('created_at','')[:10] >= '<cutoff-date>']
for i, m in enumerate(recent):
    role = m.get('role','?')
    content = m.get('content','')
    created = m.get('created_at','?')[:19]
    if role == 'user':
        print(f'=== USER [{created}] ===')
        print(content)
        print()
    else:
        print(f'--- AGENT [{created}] ---')
        print(content[:300])
        if len(content) > 300:
            print(f'... ({len(content)} chars)')
        print()
" 2>&1
```

> ✓ Checkpoint: Have you seen enough to start the analysis? If the preview is incomplete or truncated, read the saved file with `file_read` at offsets to capture all content.

## Step 4 - Read the full transcript in chunks

Use `file_read` with `offset` and `limit` parameters to read 200-500 lines at a time from the saved transcript file. Focus on user messages — those contain the change requests, corrections, decisions, and preferences.

## Step 5 - Extract and categorize

As you read, organize findings into categories. Common categories from observed traces:

### Writing Rules
Formatting standards, tone guidelines, structure requirements, audience considerations.

### Agent Behavior Rules
How the agent should conduct itself: what to show/not show in chat, tone, when to push vs back off, escalation patterns, memory expectations.

### Platform Features
Capability requests, UI/UX changes, new product ideas, integrations.

### Bug Fixes
Things that are broken: what, when reported, current status (unknown / in progress / fixed / mitigated).

### Corrections & Facts
Mistakes corrected by the user, decisions made, facts established.

## Step 6 - Present the findings

Use a `ui_show` card with `surface_type: "card"` to present an overview with metadata counters, then list each category in plain text with enough detail for action.

Note what's already been fixed or mitigated separately from what's still pending.

## SKILL COMPLETE WHEN

- [ ] The full transcript is saved to `/workspace/<filename>.txt`
- [ ] All user messages have been read and analyzed
- [ ] Findings are organized into categories
- [ ] Change list is presented to the user via card + text
- [ ] Facts worth remembering have been saved via `remember`

## Failure Modes

- **API display limits**: If the API only returns a subset of messages (e.g. oldest 200), the conversation history is incomplete. Flag to the developer to fix the fetch/display limit.
- **Empty content in recent messages**: The API may return messages with empty content fields if the save process failed. Note these as potential partial losses.
- **Truncated output**: Use file_read with offsets to get blocked content; bash pipe truncation can cut off long outputs. Read via file after saving, not from the curl output.
