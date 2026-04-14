#!/usr/bin/env bash
# .forge/mark-done.sh — mark a chunk DONE in orchestrator/state.db.
#
# Called by the inner session AFTER `forge ship <id> "<msg>"` succeeds and
# BEFORE the session exits. The runner's verifier reads state.db and will
# fail the chunk with `shipped_needs_sync` if this step is skipped.
#
# Usage: .forge/mark-done.sh <chunk-id>

set -euo pipefail

CHUNK_ID="${1:?chunk id required, e.g. SMOKE-1}"
DB="orchestrator/state.db"

if [ ! -f "$DB" ]; then
  echo "[mark-done] $DB not found — run this from the repo root" >&2
  exit 1
fi

python3 - "$CHUNK_ID" <<'PY'
import sqlite3, sys, datetime
chunk_id = sys.argv[1]
now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=5, minutes=30))).isoformat(timespec="seconds")
con = sqlite3.connect("orchestrator/state.db", isolation_level=None)
con.execute("BEGIN IMMEDIATE")
cur = con.execute(
    "UPDATE chunks SET status='DONE', finished_at=?, updated_at=?, runner_pid=NULL, failure_reason=NULL WHERE id=?",
    (now, now, chunk_id),
)
if cur.rowcount == 0:
    con.execute("ROLLBACK")
    print(f"[mark-done] ERROR: no row for chunk_id={chunk_id!r}", file=sys.stderr)
    sys.exit(2)
con.execute("COMMIT")
print(f"[mark-done] {chunk_id} → DONE @ {now}")
PY
