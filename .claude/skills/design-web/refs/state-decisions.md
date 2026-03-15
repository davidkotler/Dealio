# State Management Decision Reference

> Deep dive into state classification and management strategy selection.

---

## The State Classification Framework

### Step 1: Identify the Source

| Source | Classification |
|--------|---------------|
| API/Database | **Server State** |
| User interaction only | **Client State** |
| URL/Route | **URL State** |
| Form input | **Form State** |

### Step 2: Determine Scope

| Scope | Location Strategy |
|-------|-------------------|
| Single component | Local (useState) |
| Parent + children | Lifted state |
| Sibling components | Common ancestor or context |
| Distant components | Global store or context |
| Entire app | Global store |

### Step 3: Select Tool

```
                    ┌─────────────────────────────┐
                    │      Is it from an API?      │
                    └─────────────────────────────┘
                               │
              ┌────────────────┴────────────────┐
              ▼                                 ▼
            [YES]                             [NO]
              │                                 │
              ▼                                 ▼
    ┌─────────────────┐              ┌─────────────────┐
    │  TanStack Query │              │  Is it in URL?  │
    │  or SWR         │              └─────────────────┘
    └─────────────────┘                       │
                                 ┌────────────┴───────────┐
                                 ▼                        ▼
                               [YES]                    [NO]
                                 │                        │
                                 ▼                        ▼
                       ┌─────────────────┐    ┌─────────────────┐
                       │  URL Params     │    │   Form data?    │
                       │  searchParams   │    └─────────────────┘
                       └─────────────────┘              │
                                              ┌────────┴────────┐
                                              ▼                 ▼
                                            [YES]             [NO]
                                              │                 │
                                              ▼                 ▼
                                    ┌─────────────┐   ┌─────────────────┐
                                    │ React Hook  │   │  How many       │
                                    │ Form + Zod  │   │  consumers?     │
                                    └─────────────┘   └─────────────────┘
                                                              │
                                                   ┌──────────┴──────────┐
                                                   ▼                     ▼
                                              [1-2 close]           [3+ distant]
                                                   │                     │
                                                   ▼                     ▼
                                           ┌────────────┐        ┌────────────┐
                                           │  useState  │        │  Context   │
                                           │  + lift    │        │  or        │
                                           └────────────┘        │  Zustand   │
                                                                 └────────────┘
```

---

## Server State Patterns

### Query Key Factory

**Why:** Consistent cache keys enable reliable invalidation, prefetching, and cache reads.

```typescript
// Pattern: Hierarchical key factory
export const userKeys = {
  all: ['users'] as const,
  lists: () => [...userKeys.all, 'list'] as const,
  list: (filters: UserFilters) => [...userKeys.lists(), filters] as const,
  details: () => [...userKeys.all, 'detail'] as const,
  detail: (id: string) => [...userKeys.details(), id] as const,
};

// Enables:
queryClient.invalidateQueries({ queryKey: userKeys.all });       // All user queries
queryClient.invalidateQueries({ queryKey: userKeys.lists() });   // All list queries
queryClient.invalidateQueries({ queryKey: userKeys.detail(id) }); // Specific user
```

### Stale Time Strategy

| Data Type | Stale Time | Rationale |
|-----------|------------|-----------|
| User profile | 5-15 min | Changes rarely |
| Dashboard metrics | 30s-2min | Should feel "live" |
| Static config | 30+ min | Almost never changes |
| Real-time data | 0 | Always refetch |
| Search results | 1 min | Balance freshness + perf |

### Optimistic Update Design

**Design checklist:**




- [ ] Capture previous state before mutation
- [ ] Apply optimistic update immediately
- [ ] Handle rollback on error
- [ ] Invalidate after settlement (success or error)

```typescript
// Design artifact: Mutation plan
interface MutationPlan {
  queryKeyToUpdate: QueryKey;
  optimisticTransform: (old: Data, newValue: Partial<Data>) => Data;
  rollbackStrategy: 'restore-previous' | 'invalidate-all';
  invalidateOnSettled: QueryKey[];
}
```

---

## Client State Patterns

### When useState vs useReducer

| Scenario | Choice |
|----------|--------|
| Single primitive value | useState |
| Multiple related values | useState (object) or useReducer |
| Complex transitions | useReducer |
| Next state depends on previous | useReducer |
| State machine behavior | useReducer |


### Zustand Store Design



**Design checklist:**

- [ ] Store defined outside components
- [ ] Actions included in store (not separate)
- [ ] Selectors for each consumed slice
- [ ] Middleware decided (devtools, persist)

```typescript
// Design artifact: Store shape
interface AuthStore {
  // State
  user: User | null;
  token: string | null;

  // Derived (computed in selectors, not stored)
  // isAuthenticated: boolean  ❌ Don't store derived

  // Actions
  login: (credentials: Credentials) => Promise<void>;
  logout: () => void;
}

// Selectors (design these!)
const useUser = () => useAuthStore(s => s.user);
const useIsAuthenticated = () => useAuthStore(s => s.user !== null);
```

### Context vs Zustand

| Criteria | Context | Zustand |
|----------|---------|---------|
| Re-renders | All consumers on any change | Only when selected slice changes |
| DevTools | No | Yes |
| Persistence | Manual | Built-in middleware |
| Server components | Works | Requires client boundary |
| Complexity | Low | Medium |

**Decision:** Use Context for low-frequency updates (theme, auth status). Use Zustand for high-frequency updates (UI state, filters).

---

## URL State Patterns

### What belongs in URL

| State Type | URL? | Rationale |
|------------|------|-----------|
| Filters/sort | ✅ | Shareable, bookmarkable |
| Pagination | ✅ | Shareable, browser back works |
| Selected tab | ✅ | Direct link to tab |
| Modal open | ❌ | Not shareable, clutters URL |
| Form values | ❌ | Transient, sensitive |
| Expanded rows | ❌ | UI state, not shareable |

### URL + React Query Integration

```typescript
// Design: URL params drive query
interface ListPageDesign {
  urlParams: {
    page: number;
    sort: 'name' | 'date';
    filter?: string;
  };

  queryKey: ['items', 'list', { page, sort, filter }];

  // When URL changes → query key changes → refetch
  // When data arrives → render
  // No local state storing URL values!
}
```

---

## Form State Patterns

### Form Complexity Matrix

| Form Type | Strategy |
|-----------|----------|
| Single field | Controlled useState |
| 2-3 fields, no validation | Uncontrolled with refs |
| Multiple fields + validation | React Hook Form |
| Complex conditional logic | React Hook Form + custom hooks |
| Wizard/multi-step | React Hook Form + form state machine |

### Validation Strategy Design

```typescript
// Design artifact: Validation plan
interface FormValidationPlan {
  schema: ZodSchema;  // Source of truth

  timing: {
    validateOnBlur: ['email', 'username'];  // Async checks
    validateOnChange: ['password'];          // Real-time feedback
    validateOnSubmit: ['all'];               // Final validation
  };

  asyncValidations: {
    username: 'Check availability via API';
    email: 'Check if already registered';
  };
}
```

---

## Anti-Patterns to Catch in Design

### 1. Server Data in Client Store

```typescript
// ❌ Design flaw
interface AppStore {
  users: User[];           // Server data in Zustand!
  loadUsers: () => void;
}

// ✅ Correct design
// users: TanStack Query
// AppStore: only client state (preferences, UI state)
```

### 2. Derived State Stored

```typescript
// ❌ Design flaw
interface State {
  items: Item[];
  filteredItems: Item[];  // Derived!
  total: number;          // Derived!
}

// ✅ Correct design
interface State {
  items: Item[];
  filter: string;
}
// filteredItems = useMemo derived
// total = items.length
```

### 3. State Location Too High

```typescript
// ❌ Design flaw: modal state in App
interface AppState {
  isModalOpen: boolean;    // Only used by one component!
}

// ✅ Correct design: state colocated
// Modal component owns its open/closed state
// Or: parent that needs to control it
```

### 4. Missing Loading/Error States

```typescript
// ❌ Design flaw: only happy path
interface ComponentProps {
  data: User[];
}

// ✅ Complete design
interface ComponentProps {
  data: User[] | null;
  isLoading: boolean;
  error: Error | null;
  onRetry: () => void;
}
```

---

## State Design Template

Use this template for each piece of identified state:

```markdown
## State: [Name]

**Classification:** Server | Client | URL | Form

**Source:** [Where does this data come from?]

**Consumers:** [Which components need this?]

**Update triggers:** [What causes this to change?]

**
Location:** [useState in X | Context | Zustand | TanStack Query | URL]

**Cache strategy (if server):**
- Stale time: [duration]
- Invalidation triggers: [list]
- Optimistic updates: yes/no

**Derived values:** [List any computed values]
```
