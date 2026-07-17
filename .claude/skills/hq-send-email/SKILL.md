---
name: "HQ Agent Email Sending"
description: "Send an email from a specific business account (like support@ashlanclinic.com) through the D-Major HQ platform's agent endpoint. Routes through HQ's own Gmail integration when the address isn't connected to Jason directly. Handles the HQ agent's two-phase approval gate: send instruction via /api/agent, then confirm via /api/agent/confirm."
metadata:
  jason:
    emoji: 📧
    activation-hints:
      - user asks to send an email from a business address not connected to Jason
      - needs to send from support@ashlanclinic.com or similar HQ-managed account
      - HQ agent is holding an action pending approval and I need to confirm it
      - user says 'get HQ to send it' or 'route through HQ'
    avoid-when:
      - the email can be sent directly from dwightjonesuk@gmail.com via the Gmail
        skill — use Gmail directly instead, not HQ routing
      - the task is to read/search emails, not send — use messaging or Gmail skills
      - the email has large attachments over ~5MB — must use HQ document upload
        pattern instead
    category: integrations
---

# HQ Agent Email Sending

Send an email through the D-Major HQ agent platform, typically when the target sending address (e.g. support@ashlanclinic.com) is connected to HQ's own Gmail integration but NOT connected as a Google OAuth account on Jason.

## When to Use

USE THIS SKILL WHEN:
- The user says "get HQ to send it" or "route through HQ"
- The sending address is a business email (support@ashlanclinic.com, info@ashlanclinic.com, etc.) not directly connected to Jason
- An HQ agent action is pending approval and needs confirmation

DO NOT use this skill when:
- The email can be sent directly from dwightjonesuk@gmail.com via the Gmail skill
- You only need to read/search emails, not send
- The email has large attachments (>5MB) — use the HQ document upload + agent instruction pattern instead

## Prerequisites

- HQ API key (`dmajor-hq:api_key`) in the Jason credential vault
- Production URL: https://industry-33.emergent.host
- The target sending email address must be connected to HQ's Gmail integration

## Step 1 — Retrieve the API key

```bash
HQ_KEY=$(assistant credentials reveal --service dmajor-hq --field api_key 2>/dev/null | head -1)
if [ -z "$HQ_KEY" ]; then
  echo "ERROR: Could not retrieve HQ API key"
  exit 1
fi
```

> Checkpoint: The key must be 51 characters. If retrieval fails, check the credential vault with `assistant credentials list --search dmajor-hq`.

## Step 2 — Create the task via the agent endpoint

Send an instruction to the /api/agent endpoint with the full email details:

```bash
curl -s -X POST "https://industry-33.emergent.host/api/agent" \
  -H "X-API-Key: $HQ_KEY" \
  -H "Content-Type: application/json" \
  -d '{
  "message": "Send an email from [FROM_ADDRESS] to [TO_ADDRESS] with subject \"[SUBJECT]\". Body: [FULL_EMAIL_BODY]"
}'
```

⚠️ CRITICAL: Use `{"message": ...}` not `{"instruction": ...}`. The endpoint rejects with a Field required error if the key is wrong.

## Step 3 — Check if the agent holds for approval

The response will include an `actions` array. Each action has:
- `id`: the action_id
- `type`: e.g. "send_email"
- `status`: "pending" if it needs confirmation, "done" if already completed
- `needs_confirmation`: true/false

If `status: "done"` and `needs_confirmation: false` → the email was sent. Report success.

If `needs_confirmation: true` → proceed to Step 4.

> Checkpoint: Extract the `id` from the pending send_email action before proceeding.

## Step 4 — Confirm the action

⚠️ CRITICAL: Do NOT try to confirm via the NL /api/agent endpoint. It will create a fresh pending action instead of confirming the previous one. Use the separate confirmation endpoint.

```bash
curl -s -X POST "https://industry-33.emergent.host/api/agent/confirm" \
  -H "X-API-Key: $HQ_KEY" \
  -H "Content-Type: application/json" \
  -d '{
  "action_id": "<ACTION_ID_FROM_STEP_3>",
  "approved": true
}'
```

## Step 5 — Verify and report

When the confirmation returns `{"status": "done", "result": "Sent email to ..."}`, the email was sent. Report to the user:

> Email sent from [FROM_ADDRESS] to [TO_ADDRESS] with status: done.

## SKILL COMPLETE WHEN

- [ ] API key retrieved successfully
- [ ] /api/agent instruction sent and response received
- [ ] Action confirmed via /api/agent/confirm (if needed)
- [ ] User told the outcome
