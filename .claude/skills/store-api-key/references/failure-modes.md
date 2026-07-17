# Failure Modes — store-api-key

## Prompt Timeout

`assistant credentials prompt` blocks until the user submits. The bash tool's default is 120s, which is NOT enough. The user needs time to open the secure prompt, find their API key, copy it, and paste it.

**Symptom:** `[ERROR] <tool timeout>` with no output.

**Fix:** Always set `timeout_seconds: 330` (the max recommended for interactive prompts).

## Wrong Key in Wrong Slot

The `assistant keys set openai <key>` command does NOT validate the key format. If the user pastes an Anthropic key (`sk-ant-...`) into the OpenAI slot, the CLI accepts it without complaint.

**Symptom:** STT fails silently or returns garbage.

**Fix:** Before syncing, check the key prefix matches the expected service (OpenAI = `sk-...`, Anthropic = `sk-ant-...`, GitHub = `ghp_...`, etc.).

## No Connected Client

`assistant credentials prompt` requires a connected client to render the secure UI. If running from a headless environment with no desktop/web/Telegram client, the prompt may fail or hang.

**Symptom:** `[ERROR] No connected client available` or similar.

**Fix:** Ask the user to run it directly on their machine: `assistant credentials prompt --service <service> --field <field>`

## Reveal + Set Race

The two-step vault-to-keys sync (`assistant credentials reveal` piped to `assistant keys set`) depends on the vault write persisting before the reveal reads. In practice this is fine — the prompt blocks until stored — but if running in rapid succession for a credential that was ALREADY stored, there's no issue.

## Old Key Still Active

If a prior key was stored in the keys system and the vault gets a new key, both systems must be updated. The vault write alone does NOT update the keys slot.

**Symptom:** Credential vault shows the new key but STT still fails.

**Fix:** Always check and sync BOTH `assistant keys list` and the credential vault. Run the sync step 3 unconditionally.