# Learnings Log
**Project:** [PROJECT NAME]
**Purpose:** Running log of corrections, preferences, and patterns Nimish has taught the team.
**Rule:** Claude appends to this file at the end of every session where a correction or preference was noted.

---

## How This File Works

When Nimish corrects Claude mid-session, or expresses a strong preference:
1. Claude applies the correction immediately
2. Claude logs it here at session end
3. If the same correction happens twice → it becomes a permanent rule in the relevant agent file
4. Rules extracted from this file are noted in `RULE ADDED:` entries

---

## Session Log

<!-- Claude appends sessions below this line in the format shown -->

### Template Entry (delete this when first real entry is added)
```
## Session: YYYY-MM-DD — [Brief description of work]

### Corrections Applied
- Nimish corrected: [what Claude got wrong]
- Correct approach: [what the right approach was]
- Rule extracted: [the standing rule going forward]

### Preferences Noted
- [Preference that isn't yet codified as a rule]

### Proposed Rule Additions
1. [agents/FRONTEND.md]: Add rule — "[rule text]"
2. [standards/CODING_STANDARDS.md]: Add to forbidden patterns — "[pattern]"

### Status
[ ] Proposed rules reviewed by Nimish
[x] Rules added to relevant files
```
