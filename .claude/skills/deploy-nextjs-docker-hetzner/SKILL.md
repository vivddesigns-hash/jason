---
name: "Deploy Next.js Docker to Hetzner"
description: "Build and deploy a Next.js 15 app in Docker to a Hetzner server via SSH. Handles heavy server load, Bun-only projects, Prisma engine binary targets for Alpine, container DNS issues, long builds, and database recovery from deleted volume mounts."
metadata:
  jason:
    activation-hints:
      - deploy to Hetzner
      - deploy Next.js to production
      - push Docker build to remote server
      - deploy via Docker Compose to Hetzner server
    avoid-when:
      - deploying to Coolify (separate build pipeline)
      - local Docker builds (no SSH needed)
      - first-time Docker setup on a fresh Hetzner instance
    category: development
---

# Deploy Next.js Docker to Hetzner

Build a Next.js 15 app (with Prisma + SQLite) as a Docker image and deploy it to a Hetzner server via SSH, using the 500GB HC Volume for persistent data.

## When to Use

Use this when you need to get a Next.js app onto Dwight's Hetzner production server. The server runs 20+ containers at load 15+, uses Docker Compose (no Coolify), and has no Docker CLI on the local Mac — so everything goes through SSH screen sessions.

Do NOT use this for first-time Docker setup on a fresh Hetzner instance, deploying to Coolify, local Docker builds, or apps that don't need persistent volume storage.

## Before You Start

1. The project must compile cleanly: `bun run build` passes locally.
2. SSH access to root@95.217.216.204 works from Dwight's Mac (NOT from the Jason sandbox).
3. The target port is free. Current: 3100=FloatAI, 3110=DebtKiller, 3120=Platform, 3130=Workspace Launcher.
4. The HC Volume is at `/mnt/HC_Volume_104686033`. Docker data volumes bind there.

## Step 1 — Create tarball

```bash
tar --exclude='app/node_modules' --exclude='app/.next' --exclude='app/.git' --exclude='app/tsconfig.tsbuildinfo' --exclude='app/prisma/dev.db' -czf app-deploy.tar.gz app/
```

## Step 2 — Transfer and deploy

The sandbox has no SSH key for Hetzner. Drive deployment through Dwight's Mac via host_bash, or paste the command into his local Codex terminal.

## Step 3 — Extract and build in screen session

```bash
ssh -o ConnectTimeout=10 root@95.217.216.204 "cd /mnt/HC_Volume_104686033/docker && rm -rf app && tar -xzf app.tar.gz && screen -dmS deploy bash -c 'cd app && docker compose build > /tmp/build.log 2>&1 && docker compose up -d >> /tmp/build.log 2>&1 && echo SUCCESS >> /tmp/build.log'"
```

## Step 4 — Monitor build progress

```bash
ssh -o ConnectTimeout=8 root@95.217.216.204 "tail -3 /tmp/wl-build.log"
```

## Failure recovery: deleted volume mount

If `docker compose up -d` fails with `readdirent ... launcher-data/_data: no such file or directory`, the bind-mount directory was deleted (e.g. by `rm -rf` on the project directory). The old container is still running with the database inside it.

To recover:

1. Recreate the data directory:
   `mkdir -p /mnt/HC_Volume_104686033/docker/app-name/data`

2. Rescue the database from the running container. If `docker cp` fails because the old volume mount path is gone, the file is still open in the container process's file descriptors:
   `ls -la /proc/<container-pid>/fd/ | grep deleted`

3. Find the right fd (look for .db files marked (deleted)):
   `docker exec app-name sh -c 'cat /proc/1/fd/29 > /tmp/rescue.db'`
   or directly:
   `cp /proc/<pid>/fd/<number> /mnt/HC_Volume_104686033/docker/app-name/data/app.db`

4. Remove stale container/volume metadata:
   `docker rm app-name 2>/dev/null; docker volume rm app-name_app-data 2>/dev/null`

5. Rebuild and restart:
   `cd /mnt/HC_Volume_104686033/docker/app-name && docker compose build && docker compose up -d`

6. Verify db file size is non-zero and matches expectations.

## Step 5 — Verify health endpoint

```bash
curl -s http://localhost:PORT/api/health
```

## Step 6 — Clean up

```bash
rm -f /workspace/app-deploy.tar.gz
ssh root@95.217.216.204 "rm -f /mnt/HC_Volume_104686033/docker/app.tar.gz /tmp/build.log"
```

## SKILL COMPLETE WHEN

- [ ] Container is running (`docker ps` shows Up status, expected port)
- [ ] Health check returns `{"status":"ok","database":"connected"}`
- [ ] API endpoints respond
- [ ] Data verified intact (if recovery was needed)
- [ ] Tarballs cleaned up locally and on server

## Reference Files

See `/workspace/skills/deploy-nextjs-docker-hetzner/references/failure-modes.md` for the full catalog of deployment errors.
