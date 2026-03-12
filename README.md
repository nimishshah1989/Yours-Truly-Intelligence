# Claude Engineering OS
### By Nimish Jhaveri | Version 2.0

> Drop this folder into any project. Instantly have a senior engineering team operating at MAANG standards.

---

## What This Is

A portable intelligence layer for every Claude-assisted development project. Contains agent definitions, coding standards, security protocols, and a self-improvement system — all in markdown files that Claude reads at the start of every session.

---

## How to Use

### Step 1: Copy this folder into your project root
```
your-project/
  claude-engineering-os/    ← This folder
  src/
  package.json
  ...
```

### Step 2: At the start of every Claude session, say:
```
"Read claude-engineering-os/CLAUDE.md and initialize the engineering team for this session."
```

### Step 3: Fill in the project context files
```
claude-engineering-os/project/TECH_STACK_TEMPLATE.md → Rename to TECH_STACK.md and fill in
claude-engineering-os/project/DECISIONS_LOG.md → Starts empty, Claude fills as you build
claude-engineering-os/project/LEARNINGS.md → Starts empty, Claude fills as it learns
```

### Step 4: Work normally — Claude will now operate as a coordinated team
Every response will indicate which agent is active and why.

---

## File Map

```
CLAUDE.md                              ← START HERE — master orchestration

agents/
  ARCHITECT.md                         ← CTO/Orchestrator (always active)
  BACKEND.md                           ← API, DB, server logic
  FRONTEND.md                          ← React, Next.js, components
  FULLSTACK.md                         ← Integration, data flow
  DEVOPS.md                            ← CI/CD, Docker, infra
  QA.md                                ← Testing, coverage, review
  SECURITY.md                          ← Security audit (always active)
  UI_UX_AND_MOBILE.md                  ← Design, iOS/React Native

standards/
  CODING_STANDARDS.md                  ← MAANG-grade coding rules
  API_DOCUMENTATION.md                 ← OpenAPI spec requirements
  CICD_DATABASE_PERFORMANCE.md        ← Pipeline, migrations, performance

protocols/
  PROTOCOLS.md                         ← Collaboration, review, incidents, self-improvement

project/
  TECH_STACK_TEMPLATE.md               ← Fill this in per project
  DECISIONS_LOG.md                     ← Append-only architecture log
  LEARNINGS.md                         ← Claude's self-improvement log
```

---

## Key Features

| Feature | How It Works |
|---------|-------------|
| **Multi-agent team** | ARCHITECT orchestrates; agents announce themselves and hand off explicitly |
| **Security-first** | SECURITY agent reviews every session; blocks deploy if issues found |
| **MAANG standards** | Coding standards enforce file limits, typing, error handling, no magic numbers |
| **Self-improving** | Claude logs corrections to LEARNINGS.md; repeat corrections become permanent rules |
| **Portable** | Drop into any project; context files make it project-specific |

---

## MCP Connections to Add to Claude

These MCPs amplify the engineering team's capabilities:

### Tier 1 — Essential (add now)
| MCP | Purpose |
|-----|---------|
| **GitHub** | Code push, PR creation, branch management, CI status |
| **Supabase** | Direct DB operations, RLS management, migration running |
| **Linear** | Task/ticket creation and tracking by agents |
| **Vercel** | Deployment management, environment variables |

### Tier 2 — High Value
| MCP | Purpose |
|-----|---------|
| **Sentry** | Agents see real production errors |
| **Figma** | Design-to-code workflow (already available as deferred tool) |
| **PostHog** | Agents see analytics and user behavior |
| **AWS** | EC2/Docker management for JIP stack |

### Tier 3 — Advanced
| MCP | Purpose |
|-----|---------|
| **Browserbase/Playwright** | Agents can actually test the UI |
| **Linear** | Project management integration |
| **Slack** | Already connected — agents can post status updates |

---

## Customization

This OS is designed to evolve with you. To customize:

1. **Add project-specific rules** to `TECH_STACK.md` under "Key Architecture Decisions"
2. **Add permanent preferences** to the relevant agent file directly
3. **Add new agents** by creating a new file in `/agents/` with the same format
4. **Modify standards** — everything is editable, nothing is sacred

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 2.0 | 2025-03 | Complete rebuild — all agents, all standards, self-improvement protocol |
