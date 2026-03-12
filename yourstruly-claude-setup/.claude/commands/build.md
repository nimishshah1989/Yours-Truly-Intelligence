# /build — Phased Module Builder

## Purpose
Builds a specific module or feature following the architecture defined in `/architect`. Always builds incrementally — one logical unit at a time.

## Rules Before Building
- Architecture must have been defined (via `/architect`) before building
- Read CLAUDE.md before writing a single line of code
- Build backend before frontend
- Write the database schema/migration before writing any Python code that touches the DB
- Test each function mentally before moving to the next

## Build Sequence (always follow this order)

### Step 1 — Database First
Write and execute `schema.sql` changes. Confirm tables exist in Supabase before writing any Python.

### Step 2 — Backend Core
Build in this order:
1. Pydantic models / schemas
2. Database helper functions
3. Business logic (analytics, ETL, intelligence functions)
4. FastAPI route handlers
5. Register router in `main.py`

### Step 3 — Test Backend
Before building frontend, verify the API endpoint works:
```bash
curl -X GET http://localhost:8002/api/[endpoint] \
  -H "Content-Type: application/json"
```
Show the actual response. If it fails, fix it before proceeding.

### Step 4 — Frontend
1. API call function in `lib/api.js`
2. React component(s)
3. Wire into the appropriate page
4. Loading state + error state

### Step 5 — Integration Check
Confirm the full flow works end-to-end: DB → Python → API → React → renders correctly.

## Code Quality Checklist (apply to every file)
- [ ] Type hints on all Python functions
- [ ] Pydantic model for every API request/response
- [ ] Async/await used correctly (no blocking calls in async functions)
- [ ] `logging` used instead of `print()`
- [ ] No hardcoded credentials — all from config.py / env vars
- [ ] INR formatting using Indian number system in frontend
- [ ] Loading and error states in every React component
- [ ] Port 8002 used in docker-compose, never 8000

## After Every Build Session
Summarise:
- What was built
- What was tested and confirmed working
- What still needs to be done (update Phase status in CLAUDE.md)
- Any issues encountered and how they were resolved
