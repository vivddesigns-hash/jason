---
name: "Store API Key"
description: "Collect an API key from the user via secure prompt and sync it into both the credential vault and the keys system. Use when the user provides a raw API key (sk-..., gh-..., etc.) and it needs to live in both systems for services like STT."
metadata:
  jason:
    emoji: 🔑
    category: system
---

# Store API Key

Securely collect an API key from the user and store it in both the credential vault (`assistant credentials`) and the keys system (`assistant keys`).

## When to Use

USE THIS SKILL WHEN:
- The user has an API key they want you to store (OpenAI, Anthropic, GitHub, etc.)
- A service (STT, TTS, etc.) needs a key in `assistant keys` but you also want it in the vault
- The user says "I have the key, where should I put it?"
- You need to replace a wrong/mismatched key in either system

DO NOT use this skill when:
- The connection flows through platform-managed OAuth (Google, Linear, GitHub via `ui_show oauth_connect`)
- The service only needs a credential in one system (just `assistant credentials` or just `assistant keys`)

## Required Parameters

- `service` — service namespace (e.g. `openai`, `anthropic`, `github`)
- `field` — field name for the vault (e.g. `api_key`, `auth_token`)
- `label` — display label shown in the secure prompt UI
- `keys_name` — name for the `assistant keys` entry (usually matches `service`)

## Step 1 — Collect via secure prompt (NEVER accept in chat)

Run the credentials prompt command. Set a generous timeout (330s) since the user needs to find and paste their key.

```bash
assistant credentials prompt \
  --service <service> \
  --field <field> \
  --label "<label>" \
  --placeholder "<expected_format>" \
  --usage-description "<why this key is needed>"
```

> CRITICAL: On the `bash` tool, set `timeout_seconds` to at least 330. The default is 120s which cuts off the prompt before the user can respond.

> CRITICAL: Do not ask the user to paste the key in chat. The secure prompt route prevents the secret from appearing in conversation history.

✅ Checkpoint: The prompt opened. Did the user fill in a key? If the prompt was dismissed or timed out, offer to retry or suggest they run `assistant credentials prompt --service <service> --field <field>` themselves.

## Step 2 — Check if keys system also needs the key

Some services read from `assistant keys` (not credentials vault). Run:

```bash
assistant keys list
```

If the service already appears in `assistant keys` and needs updating, or if the target service (e.g. STT) reads from the keys system, you must sync.

If the service only needs the credential vault → done (default).

## Step 3 — Read key from vault and write to keys system

Extract the raw key from the vault and push it into the keys system:

```bash
KEY=$(assistant credentials reveal --service <service> --field <field> 2>/dev/null)
assistant keys set <keys_name> "$KEY"
```

> WARNING: The reveal command prints the raw secret to stdout. When piped through shell substitution it stays within the sandbox, but avoid echoing or logging the value. Validate by checking key length and exit code only.

✅ Checkpoint: Did `assistant keys set` succeed? Confirm with `assistant keys list`.

## Step 4 — Confirm the fix works

If the key is for STT, test with:

```bash
assistant stt transcribe --help
```

Then send the user a test prompt asking them to try it (voice message on desktop or mobile).

## SKILL COMPLETE WHEN

- [ ] `assistant credentials prompt` collected the key (exit 0)
- [ ] `assistant keys set` succeeded if keys system needed it (exit 0)
- [ ] User was told the key is stored and where to find it (service name, label)

## Failure Modes

- **Prompt timeout**: The bash tool's default 120s timeout kills the prompt before the user responds. Always set `timeout_seconds: 330`.
- **Wrong key type in wrong slot**: The `assistant keys` system doesn't validate key format. An Anthropic key (`sk-ant-...`) in the `openai` slot passes the CLI but breaks STT. Verify the user is providing the right service's key.
- **Key rejected at prompt**: `assistant credentials prompt` may silently fail if no connected client is available. Check that a client is connected before prompting. If on web/Telegram with no desktop client, the user may need to run the command themselves on the Mac.
