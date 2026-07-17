---
name: "Debug HTTP Service — Curl Works but Browser Fails"
description: "Diagnose and fix a web service that responds correctly to curl but fails when accessed from a real browser. Covers the common gaps: cookie Secure flags, form-action IDs, missing Content-Type headers, CORS, and user-agent filtering. Use whenever curl returns 200 but a browser shows a white page, login rejection, or broken JS."
metadata:
  jason:
    emoji: 🔍
    activation-hints:
      - works in curl but not in the browser
      - browser shows blank page but curl works
      - login works with curl but fails in the browser
      - CORS error when accessing from browser
    category: development
---

# Debug HTTP Service — Curl Works but Browser Fails

## When to Use

Diagnose a web service that works locally or via curl but fails when accessed from a real browser. The classic pattern: curl returns 200 and correct data, but the browser shows a white page, an “Invalid” error, or a silent redirect back to login.

This skill covers the gaps between curl and a real browser that are most often the cause.

## Step 1 — Check the browser’s actual response

Ask the user what they see. A meaningful description beats guessing: “blank white page” vs “Login page again” vs “JSON in the address bar”.

If you have a browser tool available, navigate and extract: the page source, the console errors observed in the network tab, and whether cookies are being set (look at the Set-Cookie response headers in the Network tab vs the browser’s cookie store).

## Step 2 — Reproduce via curl, then curl with browser-fidelity

Start with a minimal curl to confirm the service is reachable:

```bash
curl -s http://target:port/path
```

Then add the check that curl obscures — the cookie jar:

```bash
# Full login flow with cookie jar
curl -s -c /tmp/cookies.txt -X POST http://target:port/login \
  -F '$ACTION_ID_...=' \
  -F 'field=value'

# Check if a cookie was actually stored
grep SESSION_COOKIE_NAME /tmp/cookies.txt

# Hit the protected route with that cookie
curl -s -b /tmp/cookies.txt http://target:port/protected
```

If curl passes both steps, the gap is in the browser’s stricter enforcement of HTTP spec — proceed to Step 3.

## Step 3 — Check the four common curl/browser gaps

### 3a. Cookie Secure flag

**Most common cause.** The server sends `Set-Cookie: session=...; Secure; HttpOnly`. When the service is served over plain HTTP (no TLS), the browser silently drops the cookie. Curl does NOT enforce the Secure attribute.

**Fix:** Change `secure: true` to `secure: false` in the cookie configuration. Add a comment that HTTPS will re-enable it.

```typescript
// Before (broken over plain HTTP)
cookieStore.set("session", value, { httpOnly: true, secure: process.env.NODE_ENV === "production" });

// After (works over HTTP)
cookieStore.set("session", value, { httpOnly: true, secure: false });
```

You can verify via curl:
```bash
# Check what the server sends
grep workspace_launcher /tmp/cookies2.txt | awk '{print $4}'
# Prints "FALSE" if Secure flag is off, "TRUE" if it's on
```

### 3b. Server action / form field names

Next.js Server Actions generate an `$ACTION_ID_xxx` hidden field that changes every build. Submitting raw curl with the wrong (or missing) action ID causes the browser to redirect back to the login page.

**Fix in curl:** Always extract the action ID dynamically:
```bash
ACTION=$(curl -s http://target/login | \
  grep -o 'name="\$ACTION_ID[^"]*"' | head -1 | \
  sed 's/name="//;s/"//')
```

### 3c. Content-Type header

Curl defaults to `application/x-www-form-urlencoded`. A browser sends `multipart/form-data` for form posts with file fields. If the server is strict about Content-Type parsing, curl (in one mode) may work while the browser doesn’t, or vice versa.

**Fix:** Match the browser’s exact Content-Type. Use `-F` for multipart (matches form submissions) or `-d` for URL-encoded.

### 3d. CORS / User-Agent

If the resource is fetched via JS from a different origin, the server may reject cross-origin requests that curl doesn’t include. If the server gatekeeps on User-Agent (unusual but real), the browser’s User-Agent differs from curl’s.

**Fix:** Add headers that match the browser:
```bash
curl -H "Origin: http://app-domain.com" -H "User-Agent: Mozilla/5.0 ..." ...
# Or with full browser-CORS preflight
curl -X OPTIONS -H "Origin: ..." -H "Access-Control-Request-Method: POST" ...
```

## Step 4 — Fix, rebuild, and verify the user path

Apply the fix. If the service is in a Docker container, rebuild and redeploy.

After deployment, verify the EXACT path the user will walk, not a proxy for it:

1. Open the login page in a browser (not curl)
2. Submit the form
3. Check the URL after submission (should be the dashboard, not back at login?error=1)
4. Verify protected routes render correctly

Do NOT stop at “curl returns 200”. That was the trap that started this debugging.

## SKILL COMPLETE WHEN

- [ ] The specific gap (Secure flag, action ID, Content-Type, or CORS) is identified
- [ ] Fix is applied and the build passes
- [ ] Fixed service is deployed
- [ ] User confirms the browser path works end-to-end

## Reference Files

### references/failure-modes.md

**The setup trap:** When a service runs on a plain IP:port (no HTTPS), curl passes everything but the browser rejects `Secure` cookies silently. Always check `secure` on the cookie configuration first when login works in curl but fails in the browser.

**The curl-as-truth trap:** Verifying login via “curl returns 303 and the cookie file has the entry” is necessary but insufficient. Curl does not enforce Secure, SameSite=None without Secure, or domain mismatches. A saved cookie in curl’s file does not mean a real browser stored it.

**The action-ID trap:** Next.js Server Action field names (`$ACTION_ID_xxx`) change with every build. Curl tests that hardcode an action ID break after a redeploy. Always extract it dynamically, and always verify the field name used when the browser submits.

**The form-field-name trap:** The login form form field name must match what the server expects. A server action expects `formData.get("password")`; if the HTML has `name="api_key"` but the server reads `name="password"`, the server gets an empty string. Check both the HTML names and the server’s expected names.
