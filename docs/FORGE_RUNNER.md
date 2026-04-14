# Forge Runner — Operational Guide for YTIP

This is the single source of truth for running forge-runner on YTIP. Read this
before touching anything under `.forge/`, `orchestrator/`, or asking Claude to
"run a chunk".

---

## What forge-runner is

An autonomous loop that picks a chunk from `orchestrator/state.db`, spawns a
fresh Claude Code session against `.forge/CONDUCTOR.md` + the chunk's spec,
runs tests via `.forge/run-tests.sh`, commits via `forge ship`, and updates
`state.db` to DONE. Four post-session checks gate the result.

Source: `~/tools/forge-os/` (installed via `pip install -e .`). Binary:
`~/.local/bin/forge` (top-level CLI) + `~/.local/bin/forge-runner` (inner loop).

---

## One-time setup (already done — reference only)

| What | Where |
|---|---|
| forge-os repo | `~/tools/forge-os/` |
| runner venv | `~/tools/forge-os/runner/.venv` (Python 3.11.15) |
| `forge` wrapper | `~/.local/bin/forge` → calls `~/tools/forge-os/bin/forge` |
| `forge-runner` wrapper | `~/.local/bin/forge-runner` → sources venv, runs `python -m forge_runner` |
| OAuth token | `CLAUDE_CODE_OAUTH_TOKEN` in `~/.zshrc` (routes through Max plan) |
| Per-project config | `.forge/project.yaml`, `.forge/CONDUCTOR.md`, `orchestrator/plan.yaml`, `orchestrator/state.db` |

If any of that is missing on a fresh box: `cd ~/tools/forge-os/runner &&
python3.11 -m venv .venv && source .venv/bin/activate && pip install -e .` and
re-create `~/.local/bin/forge{,-runner}` wrappers.

---

## Daily use — adding and running a chunk

### 1. Write the chunk spec

Create `docs/specs/chunks/<ID>.md`. Spec format:

```markdown
# <ID> — <short title>

## Goal
<one paragraph>

## Scope
<bulleted list of files to create/modify>

## Acceptance criteria
- [ ] <testable statement>
- [ ] Tests still green: `bash .forge/run-tests.sh`
- [ ] Commit subject starts with `<ID>:` or `<ID> `
- [ ] `state.db` shows `<ID>` with `status='DONE'`

## Steps for the inner session
1. <ordered steps>

## Out of scope
<explicit list>

## Dependencies
- Upstream: <list of IDs or "none">
```

Keep it under 80 lines. If it's longer, the chunk is too big — split.

### 2. Seed the chunk into state.db

Two options.

**Option A — use chunkmaster (recommended for multi-chunk slices):**

```
/chunkmaster J --spec docs/specs/chunk-plan-phase-j.md
```

chunkmaster reads the source spec, drafts N chunks, writes per-chunk spec
files, appends to `plan.yaml`, and upserts rows into `state.db`. It does not
run the loop.

**Option B — seed one chunk by hand:**

```bash
python3 - <<'PY'
import sqlite3, datetime
now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=5, minutes=30))).isoformat(timespec="seconds")
con = sqlite3.connect("orchestrator/state.db", isolation_level=None)
con.execute("""INSERT OR REPLACE INTO chunks
    (id, title, spec, deps, depends_on, status, attempts, created_at, updated_at, plan_version)
    VALUES (?, ?, ?, ?, ?, 'PENDING', 0, ?, ?, '1.0')""",
    ("J-1", "Your short title",
     "docs/specs/chunks/J-1.md",
     "[]", "[]", now, now))
print("seeded J-1")
PY
```

**Always write both `deps` and `depends_on`** — forge-os's init schema uses
`deps`, but the runner's state.py reads `depends_on`. Until forge-os fixes
this upstream, write both.

### 3. Dry-run to confirm the picker sees it

```
forge run --dry-run
```

Expected output: `[dry-run] would pick: <ID> — <title>`. If it says
`halt-stalled` or `halt-complete`, one of:
- the chunk ID isn't in state.db (seed it)
- it has unmet deps (check the upstream chunks are `DONE`)
- you're on a non-matching `--filter` regex

### 4. Run one chunk (first real run of a slice — always start with --once)

```
forge run --once --max-turns 150 --timeout 20m
```

`--max-turns` and `--timeout` are CLI-only. The `runner:` section in
`project.yaml` is ignored by `forge-runner` (only `forge-ship.sh` reads
`project.yaml`).

### 5. Run a whole slice

```
forge run --filter 'J-.*' --max-turns 200 --timeout 30m
```

Once one chunk finishes, the picker walks to the next `PENDING` chunk whose
deps are `DONE`, and repeats. Ctrl-C is safe — the loop cleans up.

### 6. Retry a failed chunk

```
forge run --retry J-3 --verbose
```

This resets `J-3` to `PENDING`, archives its failure record, and runs exactly
one iteration. Incompatible with `--once`.

---

## What happens during a chunk run

1. **Picker** — reads `state.db`, finds the first `PENDING` chunk matching
   `--filter` whose deps are all `DONE`. Sorted lexicographically by ID.
2. **Implement stage** — marks chunk `IN_PROGRESS`, snapshots the quality
   baseline (if any), spawns a Claude Code session via
   `claude-agent-sdk.query()` with `.forge/CONDUCTOR.md` appended to the
   system prompt. The session's first user prompt is literally `Implement
   chunk <ID> per the spec.`
3. **Inner session** — reads `CLAUDE.md`, this file, the chunk spec. Plans,
   edits code, runs tests locally, runs `forge ship <ID> "<summary>"`, runs
   `bash .forge/mark-done.sh <ID>`, exits.
4. **Verify stage** — runs four checks:
   - `state.db.status == 'DONE'`
   - latest commit subject starts with `<ID>:` or `<ID> `
   - `.forge/last-run.json` mtime is within the session window
   - `git status --porcelain` is empty (ignoring `.forge/`)
5. **Advance stage** — increments counters, clears `current_chunk`, loops.

If any verify check fails: writes `.forge/logs/<ID>.failure.json`, marks
chunk `FAILED`, exits with code 3. Inspect the log and retry.

---

## Project files — what they do

| File | Role | Edit freely? |
|---|---|---|
| `.forge/project.yaml` | Tells `forge-ship.sh` which test/quality command to run | Yes |
| `.forge/CONDUCTOR.md` | System prompt append for every inner session. YTIP Four Laws + hard stops | Rarely |
| `.forge/run-tests.sh` | Wrapper around pytest (bypasses YAML quote bug) | Yes |
| `.forge/mark-done.sh` | Marks a chunk DONE in state.db. Called by inner sessions after `forge ship` | Never |
| `.forge/logs/` | Per-chunk event logs + failure records. Gitignored | Never (runtime) |
| `orchestrator/plan.yaml` | Human-readable chunk ledger. Not authoritative — `state.db` is | Yes (adds) |
| `orchestrator/state.db` | Runner's authoritative chunk state. Gitignored | Via SQL only |
| `docs/specs/chunks/*.md` | Per-chunk specs — one file per chunk | Yes (new only) |

---

## Commands cheat sheet

```
forge init                              # first-time scaffolding (already done)
forge run --dry-run                     # preview next pick
forge run --once                        # one chunk, exit
forge run --filter 'J-.*' --once        # one chunk matching regex
forge run --filter 'J-.*'               # loop whole slice until stalled
forge run --retry J-3                   # reset + re-run one chunk
forge run --strict-dead-man             # halt on orphan IN_PROGRESS
forge run --verbose                     # runner's own logs → DEBUG
forge status                            # plan summary (counts by status)
forge ship <ID> "<msg>"                 # ONLY legal commit path — runs tests + quality + commit + push
sqlite3 orchestrator/state.db "SELECT id, status FROM chunks;"
```

---

## Failure modes and fixes

| Symptom | Cause | Fix |
|---|---|---|
| `--dry-run` says `halt-stalled` | No PENDING chunks or deps unmet | Seed a chunk or check upstream deps are DONE |
| Inner session hangs, no events for minutes | Stuck in a long Bash call (usually tests) or debugging a forge-os bug | `ps -p <runner_pid>`, inspect `.forge/logs/<ID>.log`, kill if scope-drifting, fix root cause, `forge run --retry` |
| `shipped_needs_sync` in verifier | Commit landed but `state.db` not DONE | Session forgot `bash .forge/mark-done.sh`. Run it manually, then `sqlite3 ... "UPDATE chunks SET status='DONE' ..."` |
| `dirty_working_tree` in verifier | Session left untracked files | Check `.forge/logs/<ID>.log`, add to gitignore or clean up, `forge run --retry` |
| `no_commit_with_prefix` | Commit subject didn't start with `<ID>:` | Amend or re-do — the verifier requires the exact prefix |
| Tests fail in `forge-ship.sh` step 1 | Pre-existing test failures or missing deps | Either fix the tests (preferred) or `--deselect` them in `.forge/run-tests.sh` with a TODO comment |
| `authentication` error | `CLAUDE_CODE_OAUTH_TOKEN` missing or expired | Re-run `claude setup-token`, update `~/.zshrc`, `source ~/.zshrc` |
| Orphan `IN_PROGRESS` row after crash | Runner died mid-chunk | Next `forge run` auto-resets it, or use `--strict-dead-man` to halt and fix manually |

---

## Context: CLAUDE.md's hard stops apply inside inner sessions

`.forge/CONDUCTOR.md` duplicates YTIP's non-negotiables (Decimal not float,
paise internally, schema_v4 rule, no ETL edits, port 8002, no dark theme,
IST dates). Any chunk spec that would violate these MUST be rejected by the
inner session — it writes a failure JSON and exits non-zero. That's by
design: specs are not authoritative over CLAUDE.md.

If you're adding a rule that should apply to every future chunk, edit
`CLAUDE.md` **and** `.forge/CONDUCTOR.md`. They're intentionally duplicated.

---

## Known bugs to fix upstream (track as real issues)

1. `_load_project_yaml.sh` in forge-os can't parse commands with embedded
   quotes. Wrapper pattern (`.forge/run-tests.sh`) works around it.
2. `bin/forge init` creates a schema missing the columns `forge_runner.state`
   writes to. The local state.db has been migrated via `ALTER TABLE`.
   chunkmaster writes to both `deps` and `depends_on` as a workaround.
3. forge-ship.sh and post-chunk.sh do not update `state.db` to DONE — the
   inner session must call `.forge/mark-done.sh` explicitly. CONDUCTOR.md
   tells it to. If the session forgets, the chunk sticks at `IN_PROGRESS`.
4. `runner.timeout` and `runner.max_turns` in `.forge/project.yaml` are read
   by nothing. Pass them as CLI args: `--timeout 20m --max-turns 150`.
