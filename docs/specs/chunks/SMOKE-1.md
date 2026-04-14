# SMOKE-1 — Forge runner end-to-end smoke test

## Goal

Verify that forge-runner can pick a chunk, spawn an inner session, commit via
`forge ship`, and mark state.db DONE — without touching any production code.

## Scope

Create a single new file at `docs/FORGE_RUNNER_SMOKE.md` with exactly this
content:

```
# Forge runner smoke test

This file was created by forge-runner's inner session to verify the
end-to-end pipeline (pick → implement → ship → mark-done → verify).

If you're reading this, the runner works.
```

Do not modify any other file. Do not touch `backend/`, `frontend/`, `schema/`,
or any existing doc. Do not run migrations. Do not install dependencies.

## Acceptance criteria

- [ ] `docs/FORGE_RUNNER_SMOKE.md` exists with the exact content above.
- [ ] `pytest backend/tests -q -m 'not integration'` still passes (no regression).
- [ ] Commit subject starts with `SMOKE-1:` or `SMOKE-1 `.
- [ ] `state.db` shows `SMOKE-1` with `status='DONE'`.
- [ ] Working tree is clean at session end (except `.forge/` runner paths).

## Steps for the inner session

1. Read `CLAUDE.md` and this spec. Nothing else is needed.
2. Use the Write tool to create `docs/FORGE_RUNNER_SMOKE.md` with the content above.
3. Run `cd backend && pytest tests/ -q -m 'not integration'` — it should pass.
   If it fails for unrelated reasons, note the failure in the commit message
   but proceed (the chunk's own acceptance is the new file, not pre-existing test state).
4. Run `forge ship SMOKE-1 "forge runner end-to-end smoke test"`.
5. Run `bash .forge/mark-done.sh SMOKE-1`.
6. Exit 0.

## Out of scope

- Adding tests for the new file.
- Updating CLAUDE.md, MEMORY.md, or the wiki.
- Anything in `backend/` or `frontend/`.
