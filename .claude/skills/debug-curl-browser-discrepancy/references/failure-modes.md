# Failure Modes: Curl Works / Browser Fails

## The setup trap
When a service runs on a plain IP:port (no HTTPS), curl passes everything but the browser rejects `Secure` cookies silently. Always check `secure` on the cookie configuration first when login works in curl but fails in the browser.

## The curl-as-truth trap
Verifying login via “curl returns 303 and the cookie file has the entry” is necessary but insufficient. Curl does not enforce Secure, SameSite=None without Secure, or domain mismatches. A saved cookie in curl’s file does not mean a real browser stored it.

## The action-ID trap
Next.js Server Action field names (`$ACTION_ID_xxx`) change with every build. Curl tests that hardcode an action ID break after a redeploy. Always extract it dynamically, and always verify the field name used when the browser submits.

## The form-field-name trap
The login form field name must match what the server expects. A server action expects `formData.get("password")`; if the HTML has `name="api_key"` but the server reads `name="password"`, the server gets an empty string. Check both the HTML names and the server’s expected names.

## The gap-order trap
Check cookie Secure FIRST. It’s the most common cause, the fastest to verify, and if you check CORS or action IDs first you’ll waste time on the wrong problem. Order: Secure flag → action ID → field name → Content-Type → CORS.

## The rebuild blind spot
After fixing the cookie in the source code, the running container still serves the old build. Curl may show the old behavior if it hits a stale container. Always verify the container was actually restarted or replaced before declaring a fix done.
