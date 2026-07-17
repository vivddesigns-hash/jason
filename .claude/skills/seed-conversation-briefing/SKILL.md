---
name: "Seed a Conversation with Full Briefing"
description: "Create a NEW dedicated conversation and seed it with a comprehensive briefing, OR update an EXISTING conversation with compacted context from the current conversation."
metadata:
  jason:
    activation-hints:
      - user asks to move something to another conversation
      - user wants to compact everything about a topic and move it to a dedicated
        chat
      - user asks to seed a conversation with full context
      - user wants to rotate General to a new week
      - user asks to create a dedicated X conversation with a detailed overview
    avoid-when:
      - user just wants to rename or list conversations (use
        conversation-management instead)
      - user wants to split but hasn't confirmed the target conversation exists or
        should be created
    category: productivity
---

# Seed a Conversation with Full Briefing

## When to Use

Create a fresh dedicated conversation and seed it with full context, OR update an existing conversation with compacted context from the current thread. Use when:

- A long General chat needs rotating to a new week
- A new project or idea emerges in General that deserves its own thread
- The user says "compact everything about X and move it to the Y chat"
- The user says "create a dedicated X conversation with a detailed overview"
- Any time you need a conversation to have full context from the start

Do NOT use this for simple renames or listing conversations.

## Before You Start

If updating an **existing** conversation (the user says "move X to the Y chat"):
- First check if the target conversation already exists with `assistant conversations list`
- If it does, capture its ID. You do NOT need to create a new one.
- Read the existing conversation seed file (if one exists at `/workspace/X-conversation-seed.md` or similar) so you build on what's already there

If creating a **new** conversation:
- Proceed with Step 1 to create it

Read the entire context around what needs to go into the briefing. Review memory, concept files, and workspace docs for the topic. The briefing must be complete enough that the receiving agent does not need to ask "what happened before?".

## Step 1 — Create the conversation (only if target doesn't exist)

```bash
assistant conversations new "Conversation Name"
```

Capture the conversation ID from the output.

If the conversation already exists, capture its ID from the list command above.

## Step 2 — Write the briefing to a temp file

Write a comprehensive markdown briefing to `/workspace/.briefing-temp.txt`. Include:

- What this conversation is for (purpose and scope)
- Key context — decisions already made, current status, open items
- Any reference documents or files the agent should know about
- Next steps / what comes next
- **If updating an existing conversation:** lead with what has changed since the last briefing, so the agent knows what's new vs. what it already knows

The briefing should be self-contained. The agent reading it should be able to start working without reading another conversation.

## Step 3 — Wake the conversation with the briefing

⚠️ CRITICAL: `--hint` is REQUIRED even when `--external-content` is provided. The hint is your trusted framing. The external content is the untrusted data. Both are needed.

```bash
assistant conversations wake --persist --hint "<short-hint-describing-purpose>" --source "<descriptive-label>" --external-content "$(cat /workspace/.briefing-temp.txt)" <conversationID>
```

Use `--persist` so the briefing appears in the transcript. Use `--external-content` so it is fenced as untrusted data. The `--hint` is your trusted framing visible only to the LLM — keep it short and descriptive.

## Step 4 — Clean up

```bash
rm /workspace/.briefing-temp.txt
```

## Step 5 — Tell the user

i. Inform the user the conversation was seeded. Name the conversation and its purpose. Tell them it is in their sidebar.

ii. If the new chat was a General rotation, update NOW.md with the new conversation in the active map and the old one as archive. If it was a project spawn or update, add/update it in the active map.

iii. Remember the conversation ID and purpose.

## Reference Files

- `/workspace/skills/seed-conversation-briefing/references/failure-modes.md` — common failure modes and gotchas when using `assistant conversations wake`

## SKILL COMPLETE WHEN

- [ ] `assistant conversations new` created the conversation (if new) OR the existing conversation ID was captured
- [ ] `assistant conversations wake --persist --hint --external-content` seeded the briefing (check for "no output produced" — that is NOT a failure, the briefing was persisted)
- [ ] Temp file cleaned up
- [ ] User told the conversation is ready with its name and purpose
- [ ] NOW.md updated if applicable
