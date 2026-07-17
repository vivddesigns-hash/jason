#!/usr/bin/env bash
# Sync Jason's brain (memory + soul) and workspace (state.json) between the
# local Mac install and the cloud instance. Newer-wins per file (rsync -u).
#
#   ./sync.sh pull    cloud -> local   (run when starting local Jason)
#   ./sync.sh push    local -> cloud   (run when stopping local Jason)
#
# Best-effort: never fails hard (so it can't block Start/Stop). Single-user,
# used one-at-a-time, so newer-wins is safe; simultaneous edits to the same file
# on both sides would last-write-win.
set -uo pipefail
cd "$(dirname "$0")"

HOST="root@128.140.119.38"
REMOTE="/opt/myagent"
OPTS="-rtzu --timeout=25 -e ssh"

case "${1:-}" in
  pull)
    rsync $OPTS "$HOST:$REMOTE/memory/"     memory/     2>/dev/null || true
    rsync $OPTS "$HOST:$REMOTE/soul/"       soul/       2>/dev/null || true
    rsync $OPTS "$HOST:$REMOTE/state.json"  ./          2>/dev/null || true
    echo "pulled cloud -> local"
    ;;
  push)
    rsync $OPTS memory/     "$HOST:$REMOTE/memory/"     2>/dev/null || true
    rsync $OPTS soul/       "$HOST:$REMOTE/soul/"       2>/dev/null || true
    rsync $OPTS state.json  "$HOST:$REMOTE/state.json"  2>/dev/null || true
    ssh -o BatchMode=yes -o ConnectTimeout=15 "$HOST" \
      'chown -R jason:jason /opt/myagent/memory /opt/myagent/soul /opt/myagent/state.json 2>/dev/null' 2>/dev/null || true
    echo "pushed local -> cloud"
    ;;
  *)
    echo "usage: sync.sh pull|push"; exit 1 ;;
esac
