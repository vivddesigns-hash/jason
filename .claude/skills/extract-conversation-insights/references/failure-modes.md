# Transcript Analysis — Failure Modes & Gotchas

## API Display Limits
- The `chat_history` endpoint may return `.sort(oldest→newest).to_list(200)` which hides all messages past the 200th. Fixed by: returning most recent N (e.g. 500) instead.
- The agent's context loader (`_load_history`) may have the SAME 200-message cap. Both the display layer AND the agent's internal history loader need fixing independently.

## Empty Content in Documents
- When the agent says it created a document but the content comes through empty, it's likely a save failure mid-build. The document exists in the library but has no content. Ask the developer to rebuild in smaller batches.

## Duplicate Agent Responses
- Agent may reply with the same content multiple times. This can indicate the agent hit its reply limit mid-stream and retried.

## Cutoff Date Strategy
- Use the user's earliest report of missing messages as the cutoff. E.g., if they said "my Jul 12 conversations aren't showing", cutoff = current month's 12th day.

## Large Transcripts
- 200+ messages can be thousands of lines. Batch reads at 200-500 lines per file_read call. Do NOT try to print everything via Python stdout — it will be truncated by the bash tool's output limit.

## Credential Injection
- Use `assistant credentials reveal --service <service> --field api_key` to get the API key. Never ask the user for the key or paste it into chat.
- Use `2>/dev/null` to suppress stderr from the reveal command.