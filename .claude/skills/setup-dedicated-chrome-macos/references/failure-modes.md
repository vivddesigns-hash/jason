# Failure Modes — Dedicated Chrome on macOS

## Port 9222 Already in Use

If you get `curl: (7) Failed to connect` when checking, wait 2-3 seconds and retry — Chrome may still be starting.

If the port is genuinely taken by another process, change the port number. Pick an uncommon port (e.g. 9223) and use it consistently in all commands.

## Blocked AppleScript Approach

AppleScript with `do shell script` is blocked by Jason's security model ("BLOCKED: AppleScript contains blocked pattern: do shell script"). Always use `host_bash` instead for the Chrome launch command.

## Fresh Profile Redirects

A fresh Chrome profile (`/tmp/jason-chrome-profile`) has no saved sessions, cookies, or login state. When the assistant navigates to a site that requires authentication, it will redirect to a login/signup page. The user needs to log in once in the dedicated Chrome window for each service. After that, sessions persist in the profile.

## Multiple Mac Clients

If multiple macOS clients appear in `assistant clients list --capability host_bash`, the wrong one may be targeted. Verify by checking the client ID against the one that accepted the Chrome launch. The pattern is: the Mac that received the launch command is the one to target for CDP.

## Extension Mode Interference

The `assistant browser` CLI defaults to `extension` mode (Chrome extension or macOS desktop proxy). If the dedicated Chrome is running with `cdp-inspect`, commands must explicitly use `--browser-mode cdp-inspect` on the first call of each session, or they'll default back to extension mode and fail (or worse, connect to the user's main Chrome window).

## Launcher Script Fails with Permission Denied

If double-clicking the `.command` file opens it in a text editor instead of running it, the file may not have execute permissions. The `chmod +x` in the skill handles this. If the issue recurs, run:

```bash
chmod +x ~/Desktop/Launch-Dedicated-Browser.command
```
