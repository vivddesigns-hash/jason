# Deployment Failure Modes

## SSH connection reset during build

**Error:** `kex_exchange_identification: read: Connection reset by peer`

**Cause:** Server load is 15+ on 4 vCPUs with 20 containers. The Docker build consumes all available CPU. SSH daemon cannot accept new connections.

**Fix:** The build runs in a `screen -dmS` session and is unaffected by SSH drops. Retry SSH every 30-60 seconds until the server load drops. The build completes independently.

## Bind-mount directory deleted

**Error:** `readdirent /mnt/HC_Volume_104686033/docker/volumes/app-name_launcher-data/_data: no such file or directory`

**Cause:** `rm -rf` of the project directory also removed the bind-mount source path. `docker compose up -d` fails on volume mount.

**Fix:** Don't `rm -rf` the project directory. Instead extract the tarball alongside it and `mv` the new code in. If already deleted, recover via /proc fd (see SKILL.md Step 4 Failure recovery).

## Middleware not running on static pages

**Error:** Root page returns HTTP 200 instead of 307 redirect for unauthenticated users. `x-nextjs-cache: HIT` header present.

**Cause:** Next.js statically caches pages at build time. Pages without `cookies()` or `headers()` calls are served from cache without running middleware.

**Fix:** Add `export const dynamic = "force-dynamic"` to all static pages (/, /import, /w/[id], etc.) so they render on-demand through middleware.

## Container DNS resolution fails

**Error:** `fetch()` calls from API routes hang — specifically favicon detection or any outbound HTTP from the container.

**Cause:** Hetzner container DNS is broken. The container cannot resolve external hostnames.

**Fix:** Pre-seed data that requires outbound calls. For favicons, use Google's favicon service URL pattern: `https://www.google.com/s2/favicons?domain={hostname}&sz=64`. For any other outbound API calls, handle them at build time or seed them into the database before deploy.

## `rm -rf` includes the .git directory

**Error:** `tar --exclude='.git'` was not used; .git ships to the server ballooning the tarball.

**Fix:** Recreate tarball with `--exclude='.git'`. Always exclude: `node_modules`, `.next`, `.git`, `tsconfig.tsbuildinfo`, `prisma/dev.db`.
