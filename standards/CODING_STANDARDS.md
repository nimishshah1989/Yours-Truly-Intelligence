# CODING STANDARDS — MAANG GRADE
**Applies to:** All agents, all languages, all projects

---

## The Prime Directive

> Code is read 10x more than it is written. Optimize for the reader.

Every line you write will be read by a future engineer (likely yourself in 3 months). Write for clarity, not cleverness.

---

## 1. Modularity and File Size

### Hard Limits
- **400 lines max per file.** If approaching this limit, split the file.
- **One responsibility per module.** A file that does two things is two files.
- **Functions: 40 lines max.** If longer, extract helper functions.
- **Nesting: 3 levels max.** Deeply nested code is unreadable code.

### Module Structure
```
/features/[feature-name]/
  index.ts              ← Public API (exports only what's needed outside)
  [feature].service.ts  ← Business logic
  [feature].api.ts      ← API calls
  [feature].types.ts    ← TypeScript types
  [feature].utils.ts    ← Pure utility functions
  [feature].constants.ts ← Feature-specific constants
  __tests__/
    [feature].service.test.ts
    [feature].api.test.ts
```

### Barrel Exports (index.ts)
```typescript
// features/transactions/index.ts
// Only export what external modules need
export type { Transaction, TransactionFilter } from './transactions.types';
export { TransactionService } from './transaction.service';
// Internal helpers are NOT exported
```

---

## 2. Naming Conventions

### Universal Rules
```typescript
// Variables and functions: camelCase
const transactionAmount = 1000;
function calculateTotal(items: Item[]): number { ... }

// Types, interfaces, classes: PascalCase
interface TransactionFilter { ... }
type PaymentStatus = 'pending' | 'complete' | 'failed';
class TransactionService { ... }

// Constants (truly constant values): SCREAMING_SNAKE_CASE
const MAX_TRANSACTION_AMOUNT = 1_000_000;
const API_VERSION = 'v1';

// Booleans: prefix with is/has/can/should
const isLoading = true;
const hasPermission = false;
const canDelete = user.role === 'admin';

// Event handlers: prefix with handle/on
const handleSubmit = () => { ... };
const onClose = () => { ... };

// Custom hooks: prefix with use
function useTransactions() { ... }
function useDebounce<T>(value: T, delay: number) { ... }
```

### Explicit Over Abbreviated
```typescript
// ❌ Bad — requires mental decoding
const usr = getUsr(id);
const amt = calcAmt(txns);
function proc(d: any) { ... }

// ✅ Good — self-documenting
const user = getUser(id);
const totalAmount = calculateTotalAmount(transactions);
function processTransaction(transaction: Transaction) { ... }
```

### File Naming
```
components/TransactionCard.tsx    ← PascalCase for components
hooks/useTransactions.ts          ← camelCase with 'use' prefix
services/transactionService.ts    ← camelCase with role suffix
utils/formatCurrency.ts           ← camelCase, describes what it does
types/transaction.types.ts        ← camelCase with .types suffix
```

---

## 3. No Magic Numbers or Strings

```typescript
// ❌ Bad — what is 86400? why 10?
if (tokenAge > 86400) { ... }
const items = data.slice(0, 10);

// ✅ Good — intent is clear
const ONE_DAY_IN_SECONDS = 86400;
const DEFAULT_PAGE_SIZE = 10;

if (tokenAge > ONE_DAY_IN_SECONDS) { ... }
const items = data.slice(0, DEFAULT_PAGE_SIZE);
```

```typescript
// constants/index.ts — Central constants file
export const LIMITS = {
  MAX_TRANSACTION_AMOUNT: 1_000_000,
  MIN_PASSWORD_LENGTH: 8,
  MAX_FILE_SIZE_BYTES: 10 * 1024 * 1024, // 10MB — comment explains calculation
  DEFAULT_PAGE_SIZE: 20,
  MAX_PAGE_SIZE: 100,
} as const;

export const ROUTES = {
  HOME: '/',
  LOGIN: '/login',
  DASHBOARD: '/dashboard',
  TRANSACTIONS: '/dashboard/transactions',
} as const;
```

---

## 4. Error Handling — Exhaustive

### Every Async Operation Has Error Handling
```typescript
// ❌ Bad — fire and forget
async function createTransaction(data: TransactionCreate) {
  const result = await db.insert(data); // What if this throws?
  return result;
}

// ✅ Good — explicit error handling
async function createTransaction(data: TransactionCreate): Promise<Transaction> {
  try {
    const { data: transaction, error } = await supabase
      .from('transactions')
      .insert(data)
      .select()
      .single();
    
    if (error) {
      throw new DatabaseError(`Failed to create transaction: ${error.message}`);
    }
    
    if (!transaction) {
      throw new DatabaseError('Transaction created but no data returned');
    }
    
    return transaction;
  } catch (error) {
    if (error instanceof DatabaseError) throw error;
    throw new DatabaseError(`Unexpected error creating transaction`, { cause: error });
  }
}
```

### Result Type Pattern (for complex operations)
```typescript
type Result<T, E = Error> =
  | { success: true; data: T }
  | { success: false; error: E };

async function safeParse(input: unknown): Promise<Result<ParsedData>> {
  const parsed = schema.safeParse(input);
  if (!parsed.success) {
    return { success: false, error: new ValidationError(parsed.error.message) };
  }
  return { success: true, data: parsed.data };
}
```

---

## 5. Loop Safety — No Unbounded Operations

### Every Loop Has an Exit Condition
```typescript
// ❌ Dangerous — can run forever
while (true) {
  const result = await fetchNextPage();
  if (result.done) break; // What if 'done' is never true due to a bug?
}

// ✅ Safe — explicit limit
const MAX_ITERATIONS = 1000;
let iterations = 0;

while (iterations < MAX_ITERATIONS) {
  iterations++;
  const result = await fetchNextPage();
  if (result.done) break;
}

if (iterations >= MAX_ITERATIONS) {
  console.error('Loop exceeded max iterations — possible infinite loop');
  throw new Error('Operation exceeded maximum iterations');
}
```

### Recursive Functions Have Depth Limits
```typescript
function processTree(node: TreeNode, depth = 0, maxDepth = 50): ProcessedNode {
  if (depth > maxDepth) {
    throw new Error(`Tree depth exceeded maximum (${maxDepth})`);
  }
  
  return {
    value: process(node.value),
    children: node.children?.map(child => processTree(child, depth + 1, maxDepth)),
  };
}
```

### Async Loops Are Not Concurrent Unless Intended
```typescript
// ❌ This runs ALL promises concurrently — could overwhelm DB
const results = await Promise.all(ids.map(id => fetchById(id)));

// ✅ For large sets, batch with concurrency limit
import PLimit from 'p-limit';
const limit = PLimit(5); // Max 5 concurrent
const results = await Promise.all(
  ids.map(id => limit(() => fetchById(id)))
);
```

---

## 6. TypeScript — Strict Mode Always

### tsconfig.json Requirements
```json
{
  "compilerOptions": {
    "strict": true,              
    "noUncheckedIndexedAccess": true, 
    "noImplicitReturns": true,   
    "noFallthroughCasesInSwitch": true,
    "exactOptionalPropertyTypes": true
  }
}
```

### Type Patterns
```typescript
// Use discriminated unions for state
type RequestState<T> =
  | { status: 'idle' }
  | { status: 'loading' }
  | { status: 'success'; data: T }
  | { status: 'error'; error: Error };

// Use branded types for IDs to prevent mixing them up
type UserId = string & { readonly brand: unique symbol };
type TransactionId = string & { readonly brand: unique symbol };

function getTransaction(id: TransactionId) { ... }
// getTransaction(userId) ← TypeScript error! 

// Exhaustive switch statements
function getStatusLabel(status: PaymentStatus): string {
  switch (status) {
    case 'pending': return 'Pending';
    case 'complete': return 'Complete';
    case 'failed': return 'Failed';
    default:
      const _exhaustive: never = status; // TypeScript error if case missed
      return _exhaustive;
  }
}
```

---

## 7. Comments and Documentation

### When to Comment
```typescript
// ✅ Comment WHY, not WHAT (the code says what)
// Using sliding window rate limit instead of fixed window to prevent 
// burst traffic at window boundaries (thundering herd problem)
const ratelimit = new Ratelimit({
  limiter: Ratelimit.slidingWindow(10, '1 m'),
});

// ✅ Comment non-obvious business logic
// Indian financial regulations require transactions above ₹2L to be flagged
const HIGH_VALUE_THRESHOLD = 200_000;

// ✅ JSDoc for public APIs
/**
 * Calculates the absolute return for a portfolio position.
 * @param entryPrice - Price at position entry (in INR)
 * @param currentPrice - Current market price (in INR)
 * @param quantity - Number of units held
 * @returns Object with absolute and percentage return
 */
function calculateReturn(entryPrice: number, currentPrice: number, quantity: number) {
  ...
}

// ❌ Don't comment the obvious
const total = price * quantity; // multiply price by quantity
```

### No TODO in Production
```typescript
// ❌ Not allowed in code that merges to main
// TODO: fix this later
// HACK: this is a workaround

// ✅ Create a tracked issue instead
// See: [LINEAR-123] Refactor to use proper pagination
```

---

## 8. Import Organization

```typescript
// 1. Node built-ins
import { readFile } from 'fs/promises';

// 2. External packages
import { NextRequest, NextResponse } from 'next/server';
import { z } from 'zod';

// 3. Internal absolute imports
import { TransactionService } from '@/services/transactionService';
import type { Transaction } from '@/types/models';

// 4. Relative imports
import { formatCurrency } from '../utils/format';

// Empty line between each group
```

---

## 9. Code Review Standards

### A PR is not ready to merge unless:
- [ ] All tests pass
- [ ] No TypeScript errors
- [ ] No linting errors
- [ ] No hardcoded values
- [ ] Error handling is complete
- [ ] Loading and empty states handled
- [ ] No TODO comments
- [ ] Naming is clear and descriptive
- [ ] File sizes within limits
- [ ] Security checklist passed
- [ ] Self-reviewed (read your own diff before requesting review)

---

## 10. Forbidden Patterns

```typescript
// ❌ Never: any type
const data: any = ...

// ❌ Never: non-null assertion without verification
const user = getUser()!;  // What if getUser() returns null?

// ❌ Never: catch and ignore
try { ... } catch (e) {}  // Silently swallowing errors

// ❌ Never: floating promises
fetchData(); // No await, no .catch() — fire and forget

// ❌ Never: direct DOM manipulation in React
document.getElementById('element').style.display = 'none';

// ❌ Never: console.log in production code
console.log('debug', data); // Use proper logging

// ❌ Never: synchronous file I/O in server handlers
const data = fs.readFileSync(...); // Blocks the event loop

// ❌ Never: eval() or new Function()
eval(userInput); // Remote code execution vulnerability

// ❌ Never: disable TypeScript
// @ts-ignore
// @ts-nocheck
```
