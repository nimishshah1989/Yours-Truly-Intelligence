# /review — Code Review Sub-Agent

## Purpose
Triggers a thorough code review of recently built code. Runs as a focused review pass — does not pollute the main build conversation.

## What to Review

### Security
- [ ] No hardcoded credentials or API keys anywhere
- [ ] All env vars sourced from config.py / pydantic Settings
- [ ] SQL injection protection (supabase-py client handles this, but verify no raw SQL strings)
- [ ] No sensitive data logged (API keys, tokens must never appear in logs)
- [ ] PetPooja credentials not exposed in any API response

### Data Integrity
- [ ] T-1 lag handled correctly in all PetPooja date calculations
- [ ] Inventory pagination (50-record cap) handled with refId loop
- [ ] Upserts used correctly — no duplicate records on re-sync
- [ ] sync_log entry written for every sync job (success or failure)
- [ ] Null/missing fields from API handled gracefully (PetPooja sometimes returns empty strings)

### Code Quality
- [ ] Type hints on all Python functions
- [ ] Pydantic models for all FastAPI request/response schemas
- [ ] Async/await used consistently — no blocking calls inside async functions
- [ ] logging used instead of print() everywhere
- [ ] Error handling: every external API call wrapped in try/except with meaningful error message

### Frontend
- [ ] INR formatting uses Indian number system (₹1,23,456 not ₹123,456)
- [ ] Loading skeleton shown during every data fetch
- [ ] Error state displayed if API call fails
- [ ] No hardcoded API URLs — all from environment variable VITE_API_URL
- [ ] No inline styles — Tailwind classes only

### Docker / Deployment
- [ ] Port 8002 used in docker-compose.yml (never 8000 — conflicts with JIP)
- [ ] .env not committed — only .env.example with placeholder values
- [ ] requirements.txt includes all new packages

## Output Format
Report findings as:
- ✅ PASS — [what was checked]
- ⚠️ WARNING — [issue found, severity: low/medium]
- 🔴 CRITICAL — [must fix before deploy]

End with a summary: total issues, recommended actions in priority order.
