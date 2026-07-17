#!/usr/bin/env bash
# Usage:
#   ./run.sh            # start the web chat
#   ./run.sh heartbeat  # run the daily heartbeat once
#   ./run.sh persona    # print the assembled system prompt (debug)
set -euo pipefail
cd "$(dirname "$0")"

# load .env if present
if [ -f .env ]; then set -a; . ./.env; set +a; fi

# prefer a local venv if it exists
if [ -d .venv ]; then . .venv/bin/activate; fi

case "${1:-web}" in
  heartbeat)   exec python -m heartbeat.run_heartbeat ;;
  consolidate) exec python -m agent.consolidate ;;
  persona)     exec python -m agent.persona ;;
  web)       exec uvicorn web.server:app --host "${HOST:-127.0.0.1}" --port "${PORT:-8787}" ;;
  *) echo "unknown command: $1"; exit 1 ;;
esac
