# AGENT COLLABORATION PROTOCOL
**How agents communicate, hand off, escalate, and review each other's work**

---

## Core Principle

Agents are not siloed workers. They are a team. Backend's output is Frontend's input. Security reviews everyone's output. QA validates the whole thing. ARCHITECT sees the full picture.

---

## Communication Format

Every agent output uses this header:

```
[AGENT_NAME] | Task: [what is being done] | Consuming: [other agent's output if applicable]
─────────────────────────────────────────────────────────────────────────────────────
[actual output]
─────────────────────────────────────────────────────────────────────────────────────
[AGENT_NAME] ✅ Complete | Handoff to: [next agent] | Blockers: [none / list]
```

---

## Standard Handoff Sequences

### New Feature Build
```
[ARCHITECT] → Defines data model, API contract, and component spec
    ↓
[BACKEND] → Implements API route, tests, service
    ↓
[SECURITY] → Reviews API route (auth, validation, RLS)
    ↓
[FRONTEND] → Builds component against confirmed API contract
    ↓
[QA] → Integration tests, coverage check
    ↓
[DEVOPS] → Deployment pipeline validation
    ↓
[ARCHITECT] → Final review and sign-off
```

### Bug Fix
```
[QA] → Reproduce bug, write failing test
    ↓
[BACKEND or FRONTEND] → Fix, make test pass
    ↓
[SECURITY] → Check if bug was security-related
    ↓
[QA] → Confirm fix, regression check
```

### Database Schema Change
```
[ARCHITECT] → Approves schema change
    ↓
[BACKEND] → Writes migration with RLS
    ↓
[SECURITY] → Validates RLS policies
    ↓
[DEVOPS] → Migration plan for production
    ↓
[QA] → Migration tested against seed data
```

---

## Escalation Protocol

Use this exact format to escalate:

```
[AGENT_NAME] ⚠️ ESCALATING TO ARCHITECT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Issue:          [concise description of the problem]
Discovered:     [where/what revealed this issue]  
Impact:         [what this blocks or breaks]
Option A:       [first approach — pros/cons]
Option B:       [second approach — pros/cons]
Recommendation: [which option this agent prefers and why]
Needs by:       [urgency — blocking / before next deploy / non-urgent]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## Conflict Resolution

When agents disagree (e.g., Security wants to add overhead that Frontend says hurts UX):

1. Both agents state their position with reasoning
2. Architect makes the final call
3. Decision is logged in `DECISIONS_LOG.md` with full context
4. No agent overrides another without Architect involvement

---

# CODE REVIEW CHECKLIST
**Every PR must pass this before merge**

## Architecture
- [ ] Change is consistent with existing architecture
- [ ] No new patterns introduced without Architect approval
- [ ] New dependencies approved
- [ ] Module boundaries respected (no circular dependencies)

## Code Quality
- [ ] Files under 400 lines
- [ ] Functions under 40 lines
- [ ] No magic numbers or strings
- [ ] Naming is clear and consistent
- [ ] No commented-out code
- [ ] No TODO comments
- [ ] Error handling is complete
- [ ] No `any` types
- [ ] No `console.log`

## Security (run against SECURITY.md checklist)
- [ ] No hardcoded secrets
- [ ] Auth checked on all protected routes
- [ ] Input validated server-side
- [ ] User identity from session, not request body
- [ ] RLS in place for any new tables

## Testing
- [ ] Unit tests for new service/utility code
- [ ] API tests for new routes
- [ ] Component tests for new UI
- [ ] Coverage thresholds maintained
- [ ] Edge cases tested

## Performance
- [ ] No N+1 queries
- [ ] No unbounded loops
- [ ] External API calls have timeouts
- [ ] New components lazy-loaded if heavy

## Documentation
- [ ] JSDoc on public functions
- [ ] OpenAPI spec updated for API changes
- [ ] DECISIONS_LOG updated if architectural decision made
- [ ] README updated if setup steps changed

---

# INCIDENT RESPONSE PROTOCOL
**For production issues, security breaches, and deployment failures**

---

## Severity Classification

| Level | Description | Response Time | Who Responds |
|-------|-------------|---------------|--------------|
| P0 | Data breach, complete outage, financial data exposed | Immediate | All hands |
| P1 | Major feature broken, significant users affected | < 1 hour | Senior engineers |
| P2 | Minor feature broken, workaround exists | < 4 hours | Next available |
| P3 | Cosmetic issues, edge cases | Next deploy | Scheduled |

---

## P0/P1 Response Playbook

### Step 1: Assess (< 5 minutes)
```
What is broken:
Who is affected:
When did it start:
Is data at risk: yes / no
Can we rollback: yes / no
```

### Step 2: Communicate
- Notify Nimish immediately for P0
- Set status page / communication if user-visible

### Step 3: Contain
- If security breach: rotate all potentially compromised secrets immediately
- If data exposure: disable affected endpoint immediately
- If deployment broke prod: rollback immediately (don't debug in production)

### Step 4: Fix
- Fix in branch, not directly in main
- Write test that would have caught this
- Full CI pipeline before re-deploying

### Step 5: Post-Mortem (within 48 hours)
```markdown
## Incident: [title]
**Date:** 
**Duration:**
**Impact:**

### Timeline
- HH:MM — Event/action taken
- HH:MM — ...

### Root Cause
[What caused this]

### What Went Well
[What helped us recover faster]

### What Went Wrong
[What made it worse]

### Action Items
| Action | Owner | Due Date |
|--------|-------|---------|
| Add monitoring for X | DevOps | Date |
| Add test for scenario Y | QA | Date |
```

---

# SELF-IMPROVEMENT PROTOCOL
**How Claude learns and improves based on Nimish's feedback**

---

## Session Learning Capture

At the end of every session, Claude appends to `project/LEARNINGS.md`:

```markdown
## Session: [Date] — [Brief description of work done]

### Decisions Made
- [Decision]: [Reasoning]

### Corrections Applied
- Nimish corrected: [what was wrong]
- Correct approach: [what was right]
- Rule extracted: [permanent rule going forward]

### Patterns Observed
- [Pattern Nimish prefers that isn't yet in a standard file]

### Proposed Rule Additions
These corrections happened in this session and should be added as permanent rules:
1. [File to update]: [specific rule to add]
```

---

## Rule Extraction Protocol

When Nimish corrects something:

1. Apply the correction immediately
2. Identify if it's a preference, a standard, or a rule
3. Propose adding it to the relevant `.md` file:

```
[ARCHITECT] I've applied your correction. This appears to be a pattern 
preference worth making permanent.

Proposed addition to [agents/FRONTEND.md]:
"Always use [specific approach] instead of [approach that was corrected]"

Shall I add this? If yes, I'll update the file and it applies to all future sessions.
```

---

## Pattern Recognition

If the same correction happens twice, Claude must:
1. Flag it explicitly: "This is the second time I've made this error."
2. Add it as a rule without waiting for approval
3. Note it in `LEARNINGS.md` under "Repeat Corrections (now permanent rules)"

---

## TECH_STACK Template

```markdown
# Project: [Name]
**Last Updated:** [Date]

## Stack
- **Framework:** Next.js 14 App Router / FastAPI
- **Database:** Supabase (PostgreSQL)
- **Auth:** Supabase Auth
- **Hosting:** AWS EC2 (prod) / Railway (staging) / Vercel (frontend)
- **CI/CD:** GitHub Actions
- **Monitoring:** Sentry + UptimeRobot
- **Email:** [provider]
- **Payments:** [if applicable]

## Key Decisions
- [Why this stack was chosen]
- [Any non-standard choices and why]

## Environment Variables Required
- `DATABASE_URL`
- `SUPABASE_URL`
- `SUPABASE_ANON_KEY`
- `SUPABASE_SERVICE_ROLE_KEY`
- [add others]

## Deployment
- Production: [URL]
- Staging: [URL]
- Branch strategy: feature/* → develop → main

## Key Contacts / Integrations
- Supabase project: [project name/ID]
- GitHub repo: [URL]
- Sentry project: [URL]
```

---

## DECISIONS_LOG Template

```markdown
# Architecture Decisions Log
**Project:** [Name]
**Format:** Append-only. Never delete or edit past decisions.

---

## ADR-001: [Title]
**Date:** YYYY-MM-DD
**Status:** Accepted
**Context:** [Why this decision was needed]
**Decision:** [What was chosen]
**Consequences:** [What changes as a result]

---
```
