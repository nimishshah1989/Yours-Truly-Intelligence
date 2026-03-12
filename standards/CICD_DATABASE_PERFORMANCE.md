# CI/CD PROTOCOL
**Standard:** GitHub Actions | Zero-downtime deployments | Mandatory gates before production

---

## Pipeline Philosophy

The pipeline is the last senior engineer on the team. It enforces what humans forget to check. A pipeline that lets bad code through is a broken pipeline.

---

## Branch and Deployment Mapping

```
feature/* → develop     (CI only: lint, type-check, test)
fix/*     → develop     (CI only)
develop   → staging     (Auto-deploy after CI passes)
main      ← PR from develop  (CI + manual approval → production)
hotfix/*  → main        (Emergency path: CI + approval, expedited)
```

---

## Mandatory Pipeline Gates

### Gate 1: Code Quality (< 2 min)
```
□ ESLint — zero errors, zero warnings
□ Prettier — formatting consistent
□ TypeScript — zero type errors
□ Import order — organized correctly
```

### Gate 2: Security (< 3 min)
```
□ npm audit — no HIGH or CRITICAL vulnerabilities
□ Secret scanning — no hardcoded keys (use git-secrets or gitleaks)
□ Dependency licenses — no GPL in commercial projects
```

### Gate 3: Tests (< 10 min)
```
□ All unit tests pass
□ All integration tests pass
□ Coverage thresholds met (80% overall, 95% business logic)
□ No flaky tests (retry once, if still fails — blocked)
```

### Gate 4: Build (< 5 min)
```
□ Production build succeeds
□ Bundle size check — no unexpected large increase (>10% = review required)
□ Docker image builds successfully
```

### Gate 5: Staging Validation (< 15 min)
```
□ E2E tests pass against staging environment
□ Health check endpoint returns 200
□ No new Sentry errors in first 5 minutes
```

### Gate 6: Production (manual approval required)
```
□ Staging validation passed
□ PR reviewed and approved
□ DECISIONS_LOG updated for any architectural changes
□ Rollback plan documented
```

---

## Rollback Protocol

```bash
# 1. Identify last known good image tag (from DECISIONS_LOG or GitHub releases)
LAST_GOOD_SHA="abc123"

# 2. Deploy immediately
./deploy.sh $LAST_GOOD_SHA

# 3. Verify health check
curl https://yourapp.com/api/health

# 4. Create post-incident issue
# Document: what failed, why rollback needed, permanent fix plan
```

---

## PR Requirements

PRs to `main` or `develop` must have:
- [ ] Descriptive title: `[type]: brief description` (feat, fix, chore, docs, security)
- [ ] Description explains WHY (not just what — the diff shows what)
- [ ] Screenshots for UI changes
- [ ] Migration notes if schema changed
- [ ] All CI gates passing
- [ ] No `TODO` comments
- [ ] DECISIONS_LOG entry for architectural changes

---

# DATABASE PROTOCOL
**DB:** Supabase (PostgreSQL) | All schema changes via migrations | No manual edits in production

---

## Migration Standards

### Every Schema Change is a Migration
```bash
# Create migration
supabase migration new add_transactions_table

# File created: supabase/migrations/20250315120000_add_transactions_table.sql
```

### Migration File Rules
- Migrations are append-only — never edit an existing migration
- Every migration is reversible (include rollback in comments if needed)
- Migrations run in CI before tests
- Production migrations run with zero downtime patterns

### Migration Template
```sql
-- Migration: 20250315_add_transactions_table
-- Description: Creates the transactions table for financial tracking
-- Rollback: DROP TABLE IF EXISTS public.transactions;

BEGIN;

-- Create table
CREATE TABLE IF NOT EXISTS public.transactions (
  id          UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  user_id     UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  title       VARCHAR(200) NOT NULL,
  amount      NUMERIC(15, 2) NOT NULL CHECK (amount > 0),
  category_id UUID REFERENCES public.categories(id),
  notes       TEXT,
  created_at  TIMESTAMPTZ DEFAULT NOW() NOT NULL,
  updated_at  TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

-- Indexes
CREATE INDEX idx_transactions_user_id ON public.transactions(user_id);
CREATE INDEX idx_transactions_created_at ON public.transactions(created_at DESC);
CREATE INDEX idx_transactions_user_created ON public.transactions(user_id, created_at DESC);

-- Enable RLS (ALWAYS)
ALTER TABLE public.transactions ENABLE ROW LEVEL SECURITY;

-- RLS Policies
CREATE POLICY "users_select_own_transactions" ON public.transactions
  FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "users_insert_own_transactions" ON public.transactions
  FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "users_update_own_transactions" ON public.transactions
  FOR UPDATE USING (auth.uid() = user_id)
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "users_delete_own_transactions" ON public.transactions
  FOR DELETE USING (auth.uid() = user_id);

-- Auto-update updated_at
CREATE TRIGGER update_transactions_updated_at
  BEFORE UPDATE ON public.transactions
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

COMMIT;
```

---

## Query Performance Standards

### Required for Any Query on Large Tables
```sql
-- Check query plan before shipping
EXPLAIN ANALYZE SELECT * FROM transactions WHERE user_id = 'uuid';

-- Target: seq scan on indexed columns, not full table scans
-- Index scans < 10ms, full scans require justification
```

### N+1 Prevention
```typescript
// ❌ N+1 problem
const users = await getUsers();
for (const user of users) {
  user.transactions = await getTransactions(user.id); // One query per user!
}

// ✅ Single query with join
const { data } = await supabase
  .from('users')
  .select(`
    id, name, email,
    transactions (id, title, amount, created_at)
  `)
  .limit(20);
```

---

# PERFORMANCE STANDARDS
**Target:** Fast, lean, observable

---

## Frontend Performance

| Metric | Target | Critical Threshold |
|--------|--------|-------------------|
| First Contentful Paint | < 1.5s | 3s |
| Largest Contentful Paint | < 2.5s | 4s |
| Time to Interactive | < 3s | 5s |
| Cumulative Layout Shift | < 0.1 | 0.25 |
| JS Bundle (initial) | < 200KB gzipped | 500KB |
| API Response (p95) | < 500ms | 2s |

### Bundle Size Rules
- Monitor with `@next/bundle-analyzer`
- New dependency > 50KB requires Architect approval
- Dynamic imports required for: chart libraries, PDF viewers, rich text editors
- Tree-shaking verified: import named exports, not entire libraries

## Backend Performance

| Metric | Target |
|--------|--------|
| Simple DB query | < 50ms |
| Complex query (joins, aggregation) | < 500ms |
| External API call (with timeout) | < 3s |
| Background job | No hard limit, but monitored |

### Caching Strategy
```typescript
// Static data: cache aggressively
export const revalidate = 3600; // 1 hour (Next.js route segment)

// User-specific data: no caching at edge
export const dynamic = 'force-dynamic';

// React Query stale time
const { data } = useQuery({
  queryKey: ['categories'],
  queryFn: getCategories,
  staleTime: 1000 * 60 * 60, // 1 hour (rarely changes)
});
```
