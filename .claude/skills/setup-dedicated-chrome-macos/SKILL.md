---
name: "Setup Dedicated Chrome on macOS"
description: "Launch a separate Chrome instance on macOS with its own profile, remote debugging on port 9222, and no-first-run flags. Creates a Desktop launcher script and connects via CDP inspect mode. Use when the user needs a shared workspace browser that the assistant can control independently from the user's main Chrome, or when computer-use/extension is fighting the user's active browser."
metadata:
  jason:
    emoji: 🌐
    category: system
---

# Setup Dedicated Chrome on macOS

Launch a separate Chrome instance on macOS with its own profile and remote debugging for assistant CDP control.

## When to Use

Use this skill when:
- The user needs a dedicated browser instance the assistant can control without disrupting their main Chrome
- Computer-use is fighting the user's active browser (you click, they lose cursor)
- The user asks for a shared workspace browser or separate Chrome profile
- The assistant needs to work in one Chrome window while the user works in another

## Prerequisites

- Google Chrome installed on macOS (standard `/Applications/Google Chrome.app` path)
- Host bash and host file capabilities on the Mac client
- The assistant CLI `browser` command available

## Procedure

### Step 1 - Launch the dedicated Chrome

Run this via `host_bash` (must target the Mac client, not the sandbox):

```bash
mkdir -p /tmp/jason-chrome-profile
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
  --user-data-dir=/tmp/jason-chrome-profile \
  --remote-debugging-port=9222 \
  --no-first-run \
  --no-default-browser-check &
```

**Important:** Use `background: true` in the host_bash call (set it running, don't wait for it). The command does not exit cleanly because Chrome stays running.

### Step 2 - Verify it's running

Wait ~3 seconds, then check:

```bash
curl -s --max-time 5 http://localhost:9222/json/version
```

Expected response includes `"Browser": "Chrome/..."` and `"webSocketDebuggerUrl": "ws://localhost:9222/..."`. If this fails, the Chrome process may not have started yet — wait 2 more seconds and retry.

### Step 3 - Identify the Mac client ID

```bash
assistant clients list --capability host_bash
```
Note the `target_client_id` of the Mac desktop client.

### Step 4 - Create a Desktop launcher for next restart

Write a double-clickable `.command` file to the user's Desktop:

```bash
DESKTOP_DIR="$(echo ~/Desktop)"
cat > "$DESKTOP_DIR/Launch-Dedicated-Browser.command" << 'SCRIPT'
#!/bin/bash
PROFILE_DIR="/tmp/jason-chrome-profile"
mkdir -p "$PROFILE_DIR"
if curl -s --max-time 2 http://localhost:9222/json/version > /dev/null 2>&1; then
  echo "Dedicated browser is already running."
  exit 0
fi
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
  --user-data-dir="$PROFILE_DIR" \
  --remote-debugging-port=9222 \
  --no-first-run \
  --no-default-browser-check &
sleep 3
echo "Dedicated browser ready."
SCRIPT
chmod +x "$DESKTOP_DIR/Launch-Dedicated-Browser.command"
```

### Step 5 - Connect the assistant to the dedicated Chrome

All future browser commands use:

```bash
assistant browser <command> --browser-mode cdp-inspect --target-client-id <mac-client-id>
```

For example:

```bash
assistant browser navigate --url "https://example.com" --browser-mode cdp-inspect --target-client-id <mac-client-id>
assistant browser snapshot --target-client-id <mac-client-id>
assistant browser extract --target-client-id <mac-client-id>
```

⚠️ **CRITICAL:** The `--browser-mode cdp-inspect` flag is needed only for the first command in a session to select the backend. After that, the session is sticky and subsequent commands only need `--target-client-id`. If commands stop working with "CDP endpoint unreachable" errors, add `--browser-mode cdp-inspect` back to the first command of the next session.

### Step 6 - Tell the user

- The dedicated Chrome is a normal window on their screen — they can move it, minimise it, or put it on a separate monitor
- I control it programmatically — I do NOT need it visible
- They only need to interact with it for manual logins (MFA, OAuth consent screens)
- After a restart, double-click `Launch-Dedicated-Browser.command` on their Desktop
- The profile persists at `/tmp/jason-chrome-profile` (persists across reboots on macOS, resets if /tmp is cleaned)

## Failure Modes

See `references/failure-modes.md` for:
- Port already in use / Chrome already running
- Blocked AppleScript attempts (`do shell script` blocked)
- Fresh profile has no logins (redirects to login pages)
- Target client ID needed (multiple Mac clients)

## SKILL COMPLETE WHEN

- [x] `host_bash` launched Chrome with `--remote-debugging-port=9222`
- [x] `curl http://localhost:9222/json/version` confirms the browser is listening
- [x] `assistant browser navigate` with `cdp-inspect` succeeds
- [x] Desktop launcher script written and executable
- [x] User knows about the new window and the launcher
