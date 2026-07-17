# Seed Conversation Briefing — Failure Modes

## `--hint` is required
`assistant conversations wake` requires `--hint <text>` even when `--external-content` is provided. The hint is the trusted framing visible to the LLM; the external content is the untrusted briefing data.

Error signature:
```
error: required option '--hint <text>' not specified
```

Remedy: always provide both `--hint "short descriptive framing"` and `--external-content "$(...)"`.

## `--external-content` is size-limited
Data passed via `--external-content` appears in process listings (ps) and is bounded by ARG_MAX (~2MB on most systems). Keep briefings under 100KB. For larger context, write to a file and reference it in the briefing.

## The `--persist` flag must be explicit
Without `--persist`, the wake is ephemeral and does not persist to the transcript unless the agent produces output. Always use `--persist` when you want the briefing visible in the conversation history.

## Quiet wake is normal
If the target conversation's agent produces no output (e.g. the briefing was received but the agent has nothing to say), the wake returns "no output produced". This is NOT a failure — the briefing is persisted. Verify by checking the target conversation's transcript.

## Check for existing seed files before writing
Before creating a briefing, check if a previous seed file (`/workspace/*seed*.md`, `/workspace/*briefing*.md`) exists for the target conversation. Build on what's already there rather than starting from scratch.
