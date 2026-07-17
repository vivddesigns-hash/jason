# HQ Agent Email Sending — Failure Modes

## Symptom: Agent keeps recreating pending actions
**What happens:** You send an instruction via /api/agent asking to confirm the send. The agent returns a *new* pending action with a different action_id instead of confirming the previous one.

**Root cause:** The /api/agent NL endpoint processes instructions conversationally and keeps creating fresh pending actions. It does NOT directly execute pending actions from prior sessions.

**Fix:** Do NOT try to confirm via the NL /api/agent endpoint. Instead, use the separate confirmation endpoint:
```
POST /api/agent/confirm
Body: {"action_id": "<id>", "approved": true}
```

## Symptom: /api/agent returns "Field required"
**What happens:** The endpoint rejects with a Field required error for `body`.`message`.

**Root cause:** The /api/agent endpoint accepts `{"message": "..."}` not `{"instruction": "..."}`.

**Fix:** Use `message` as the key in the JSON body.

## Symptom: /api/emails endpoint not found
**What happens:** Any request to /api/emails returns 404.

**Root cause:** HQ has no direct email API endpoint. All email operations route through the agent.

**Fix:** Use the agent instruction pattern — instruct via /api/agent with `{"message": "..."}`.

## Precondition: API key
- Stored in Jason credential vault as `dmajor-hq:api_key` (51 chars).
- Must be retrieved at the start of each use.

## Precondition: Endpoints
- /api/agent accepts `{"message": string}` for instruction.
- /api/agent/confirm accepts `{"action_id": string, "approved": true}` to confirm a pending action.
- Production URL: https://industry-33.emergent.host