# Project: [PROJECT NAME]
**Last Updated:** [DATE]
**Status:** Active

---

## Stack

| Layer | Technology | Version |
|-------|-----------|---------|
| Frontend Framework | Next.js App Router | 14.x |
| UI Library | React | 18.x |
| Styling | Tailwind CSS | 3.x |
| Backend | FastAPI / Next.js API Routes | - |
| Database | Supabase (PostgreSQL) | - |
| Auth | Supabase Auth | - |
| State Management | TanStack Query + Zustand | - |
| Forms | react-hook-form + Zod | - |
| Testing | Vitest + Playwright | - |
| Containerization | Docker + Docker Compose | - |
| CI/CD | GitHub Actions | - |
| Hosting (Production) | AWS EC2 Mumbai | - |
| Hosting (Frontend) | Vercel | - |
| Error Tracking | Sentry | - |
| Uptime Monitoring | UptimeRobot | - |

---

## Environment Variables

```bash
# Supabase
SUPABASE_URL=
SUPABASE_ANON_KEY=          # Public — okay to be in frontend
SUPABASE_SERVICE_ROLE_KEY=  # Server-side only, never public

# App
NEXTAUTH_SECRET=
NEXT_PUBLIC_APP_URL=        # e.g. https://yourapp.com
APP_VERSION=                # Set by CI/CD from git SHA

# External Services (add as needed)
OPENAI_API_KEY=             # Server-side only
ANTHROPIC_API_KEY=          # Server-side only
STRIPE_SECRET_KEY=          # Server-side only
STRIPE_PUBLISHABLE_KEY=     # NEXT_PUBLIC_ okay
UPSTASH_REDIS_REST_URL=
UPSTASH_REDIS_REST_TOKEN=
SENTRY_DSN=                 # NEXT_PUBLIC_ okay for frontend errors
```

---

## Key Architecture Decisions

- [Decision 1 and brief reasoning]
- [Decision 2 and brief reasoning]

---

## Deployment

| Environment | URL | Branch | Auto-deploy |
|-------------|-----|--------|-------------|
| Production | https://[domain] | main | No (manual approval) |
| Staging | https://staging.[domain] | develop | Yes |
| Local | http://localhost:3000 | - | - |

---

## External Integrations

| Service | Purpose | Dashboard |
|---------|---------|-----------|
| Supabase | Database + Auth | [URL] |
| GitHub | Code + CI/CD | [URL] |
| Sentry | Error tracking | [URL] |

---

## Domain and Feature Map

```
[List the main features/modules of this project]
Feature 1: [description]
Feature 2: [description]
```
