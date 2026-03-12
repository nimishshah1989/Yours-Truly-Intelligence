# /architect — System Design Before Code

## Purpose
Forces a full architecture review BEFORE any code is written. Run this at the start of every new feature or module.

## What to Do When This Command Is Invoked

1. **Read CLAUDE.md fully** before responding — understand the full system context

2. **Produce this output in order:**

### A. Feature Summary (2-3 sentences)
What this feature does and why it exists in the context of the YoursTruly platform.

### B. Files to Create / Modify
List every file that will be created or changed. For each file: path, purpose, and what existing files it depends on.

### C. Database Changes
If new tables or columns are needed, write the exact SQL `CREATE TABLE` or `ALTER TABLE` statements. Follow the schema conventions in CLAUDE.md exactly.

### D. API Endpoints
For every new FastAPI route:
```
METHOD /api/path
Request body: {field: type}
Response: {field: type}
Purpose: one line description
```

### E. Data Flow
Step-by-step numbered list: where data comes from → how it moves → where it ends up.

### F. Dependencies
Any new Python packages (add to requirements.txt) or npm packages needed.

### G. Risks & Edge Cases
What could go wrong? What edge cases must be handled? (e.g. PetPooja T-1 lag, empty inventory response, Tally XML malformed)

### H. Build Order
Numbered sequence of tasks in the order they should be built. Each task should be completable in a single Claude Code session.

---

## Rules
- Do NOT write any code in the architect step
- If anything in the request is ambiguous, ask one clarifying question before proceeding
- If the request conflicts with CLAUDE.md conventions, flag it explicitly and propose a compliant alternative
- Architecture must be approved before `/build` is invoked
