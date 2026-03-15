---
name: review-react
version: 2.0.0

description: |
  Review React and TypeScript code for quality, patterns, architectural alignment, design system
  compliance, and shared component reusability. Evaluates type safety, component architecture,
  state management, accessibility, performance, design token usage, and layer placement (shared vs feature).
  Use when reviewing React components, TypeScript interfaces, hooks, Next.js pages, validating
  frontend implementations against established patterns, or checking that components correctly use
  design system tokens and are placed in the right layer. Also use when auditing for duplicated
  shared components, magic numbers in styling, or visual drift from the design system.
  Relevant for React 18+, Next.js App Router, TypeScript, TanStack Query, Zustand, accessibility audits.

chains:
  invoked-by:
    - skill: implement/react
      context: "Post-implementation quality gate"
    - skill: refactor/react
      context: "After refactoring validation"
  invokes:
    - skill: implement/react
      when: "Critical or major findings detected requiring fixes"
    - skill: review/types
      when: "Complex type issues need dedicated analysis"
---

# React Review

> Validate React implementations for type safety, architectural alignment, accessibility, **design system compliance**, **reusability**, and production readiness through systematic code analysis.

## Quick Reference

| Aspect | Details |
|--------|---------|
| **Dimension** | React & TypeScript Quality |
| **Scope** | Components, hooks, state management, accessibility, patterns, **design token usage**, **layer placement** |
| **Invoked By** | `implement/react`, `refactor/react`, `/review` command |
| **Invokes** | `implement/react` (on failure), `review/types` (complex type issues) |
| **Verdict Options** | `PASS` · `PASS_WITH_SUGGESTIONS` · `NEEDS_WORK` · `FAIL` |

---

## Review Objective

Ensure React implementations follow established patterns, maintain type safety, respect the Server/Client component boundary, manage state correctly, meet accessibility standards, **use design system tokens consistently**, and **place components in the correct layer for reusability**.

### This Review Answers

1. Does the code follow TypeScript strict mode with explicit prop interfaces?
2. Is state classified and located correctly (server vs client vs URL vs form)?
3. Are components properly separated into Server and Client boundaries?
4. Does the implementation meet accessibility requirements?
5. **Do all visual values (colors, spacing, typography, motion) reference design system tokens?**
6. **Is each component in the correct layer — shared for domain-agnostic, feature for domain-coupled?**
7. **Are existing shared components reused rather than duplicated?**

### Out of Scope

- Aesthetic design judgment (whether teal is the right brand color, whether the layout looks nice)
- Business logic correctness (covered by `review/functionality`)

> **Note:** Design system *compliance* (whether code uses established tokens and shared components) is **in scope**. The line is: "Are you using the design system correctly?" is our concern. "Is the design system itself well-designed?" is not.

---

## Core Workflow

```
┌─────────────────────────────────────────────────────────────┐
│                    REVIEW WORKFLOW                          │
├─────────────────────────────────────────────────────────────┤
│  1. SCOPE    →  Identify .tsx, .ts files to review          │
│  2. CONTEXT  →  Load principles, implement/react patterns   │
│  3. ANALYZE  →  Apply evaluation criteria systematically    │
│  4. CLASSIFY →  Assign severity to each finding             │
│  5. VERDICT  →  Determine pass/fail based on findings       │
│  6. REPORT   →  Output structured review results            │
│  7. CHAIN    →  Invoke implement/react if fixes needed      │
└─────────────────────────────────────────────────────────────┘
```

### Step 1: Scope Definition

Identify review targets:

```bash
# React components and hooks
**/*.tsx
**/*.ts (excluding *.test.ts, *.spec.ts)

# Exclude
node_modules/**, dist/**, .next/**, build/**
```

### Step 2: Context Loading

Before analysis, internalize:

- **Principles:** `rules/principles.md` → Type Safety, Modularity, Composition over Inheritance
- **Conventions:** `rules/react.md` → React-specific conventions
- **Patterns:** `skills/implement/react/refs/*.md` → State, hooks, patterns, accessibility
- **Design System:** The project's design tokens (colors, typography, spacing, motion, shadows, radii) and shared component inventory

### Step 3: Systematic Analysis

For each artifact, evaluate against criteria in order of severity:

| Priority | Criterion Category | Weight |
|----------|-------------------|--------|
| P0 | Type Safety Violations | Blocker |
| P1 | State Management Errors | Critical |
| P2 | Component Architecture Issues | Major |
| P3 | Accessibility Gaps | Major |
| P4 | Design System & Reusability Violations | Major |
| P5 | Performance Anti-patterns | Minor |

### Step 4: Severity Classification

| Severity | Definition | Action Required |
|----------|------------|-----------------|
| **BLOCKER** | `any` types, broken type contracts, runtime crashes | Must fix before merge |
| **CRITICAL** | Wrong state location, missing error states, 'use client' at wrong level, duplicated shared component | Must fix, may defer |
| **MAJOR** | Accessibility violations, nested components, stale closures, magic numbers in styling, wrong layer placement | Should fix |
| **MINOR** | Naming issues, missing cleanup functions, suboptimal patterns, inconsistent token usage | Consider fixing |
| **SUGGESTION** | Alternative approaches, optimization opportunities, potential shared component promotion | Optional improvement |
| **COMMENDATION** | Excellent patterns, clean implementations, good design system usage | Positive reinforcement |

### Step 5: Verdict Determination

```
Findings Analysis
       │
       ├─► Any BLOCKER? ──────────────► FAIL
       │
       ├─► Any CRITICAL? ─────────────► NEEDS_WORK
       │
       ├─► Multiple MAJOR? ───────────► NEEDS_WORK
       │
       ├─► Few MAJOR or MINOR only? ──► PASS_WITH_SUGGESTIONS
       │
       └─► SUGGESTION/COMMENDATION ───► PASS
```

---

## Evaluation Criteria

### TS: Type Safety

| ID | Criterion | Severity | Check |
|----|-----------|----------|-------|
| TS.1 | No `any` type usage | BLOCKER | `grep -r ":\s*any" --include="*.tsx" --include="*.ts"` |
| TS.2 | Explicit prop interfaces defined | CRITICAL | All components have `interface *Props` |
| TS.3 | Native element extension uses `ComponentPropsWithoutRef` | MAJOR | Check components wrapping HTML elements |
| TS.4 | Discriminated unions for variant props | MAJOR | Multi-mode components use `type` or `variant` field |
| TS.5 | No `// @ts-ignore` or `// @ts-expect-error` without justification | MAJOR | Search for suppression comments |
| TS.6 | `npx tsc --noEmit` passes | BLOCKER | Zero type errors |

### SM: State Management

| ID | Criterion | Severity | Check |
|----|-----------|----------|-------|
| SM.1 | Server data uses TanStack Query, not useState/Zustand | CRITICAL | API data not in local state |
| SM.2 | Query key factories for cache management | MAJOR | Consistent key structure exists |
| SM.3 | No derived state in useEffect | CRITICAL | Computed values during render |
| SM.4 | Zustand uses granular selectors | MAJOR | No full-store subscriptions |
| SM.5 | Form state uses React Hook Form + Zod | MINOR | Complex forms validated properly |
| SM.6 | URL state for filters/pagination | MINOR | searchParams used appropriately |

### CA: Component Architecture

| ID | Criterion | Severity | Check |
|----|-----------|----------|-------|
| CA.1 | No nested component definitions | CRITICAL | Components defined at module level |
| CA.2 | `'use client'` only at leaf components | CRITICAL | Directive pushed to minimum scope |
| CA.3 | Server Components for data, Client for interactivity | MAJOR | Proper separation |
| CA.4 | Compound components for implicit parent-child state | MAJOR | Context-based composition |
| CA.5 | Single responsibility per component | MAJOR | No god components |
| CA.6 | Props don't exceed 7 without composition | MINOR | Use slots/children for complex interfaces |

### AX: Accessibility

| ID | Criterion | Severity | Check |
|----|-----------|----------|-------|
| AX.1 | Interactive elements use `<button>`, `<a>`, `<input>` | MAJOR | No `<div onClick>` or `<span onClick>` |
| AX.2 | Form inputs have associated `<label>` | MAJOR | `htmlFor` or wrapper pattern |
| AX.3 | Images have `alt` text | MAJOR | Decorative images use `alt=""` |
| AX.4 | Focus visible on interactive elements | MAJOR | `:focus-visible` styles exist |
| AX.5 | Modals trap focus and handle Escape | CRITICAL | Focus management implemented |
| AX.6 | Color not sole information carrier | MINOR | Icons, text, patterns supplement color |

### DS: Design System Compliance

Every visual value should trace to a design system token. Hardcoded values cause visual drift — different features start looking like different products. This section catches those inconsistencies.

| ID | Criterion | Severity | Check |
|----|-----------|----------|-------|
| DS.1 | Colors use semantic tokens, not raw values | MAJOR | No hardcoded hex, rgb, oklch, or Tailwind color scales (`bg-zinc-950`) — use semantic tokens (`bg-background`, `text-primary`) |
| DS.2 | Spacing uses scale tokens, not arbitrary values | MAJOR | No `p-[13px]` or `gap-[7px]` — use scale values (`p-3`, `gap-2`) |
| DS.3 | Typography uses type scale, not ad-hoc sizes | MAJOR | No `text-[15px]` or `font-[450]` — use presets (`text-sm`, `font-medium`) |
| DS.4 | Motion uses token presets, not hardcoded values | MINOR | No inline `duration-300 ease-in-out` — use motion tokens |
| DS.5 | Shadows use elevation tokens | MINOR | No inline `shadow-[0_2px_4px_...]` — use scale (`shadow-sm`, `shadow-md`) |
| DS.6 | Border radius uses scale tokens | MINOR | No `rounded-[7px]` — use scale (`rounded-md`, `rounded-lg`) |
| DS.7 | Icons from project's icon set | MINOR | No mixed icon libraries — consistent icon source |
| DS.8 | Dark mode works without feature-specific overrides | MAJOR | Colors respond to theme correctly via CSS variables |

### RE: Reusability & Layer Placement

The shared layer is the product's reusable vocabulary. When domain-agnostic components stay trapped inside features, other features end up reinventing them — leading to duplication, divergence, and wasted effort. This section ensures components are in the right place.

| ID | Criterion | Severity | Check |
|----|-----------|----------|-------|
| RE.1 | No duplication of existing shared components | CRITICAL | Feature doesn't recreate Card, Badge, Spinner, EmptyState, etc. that already exist in shared |
| RE.2 | Domain-agnostic components are in the shared layer | MAJOR | Layout, display, input, and feedback components that have no feature-specific data coupling belong in shared |
| RE.3 | Feature components don't leak into shared | MAJOR | Shared layer has no imports from feature directories |
| RE.4 | Shared components use generic props, not domain types | MAJOR | Shared components accept primitives or generic types, not feature-specific interfaces |
| RE.5 | New shared components are exported through barrel file | MINOR | Other features can discover and import them |
| RE.6 | Components named by function, not domain | MINOR | `StatusBadge` not `VulnerabilityBadge`, `MetricCard` not `ScanMetricCard` |
| RE.7 | Existing shared components extended, not forked | MAJOR | If a shared component almost fits, add a variant to it — don't create a parallel version |

### PF: Performance & Patterns

| ID | Criterion | Severity | Check |
|----|-----------|----------|-------|
| PF.1 | Effects return cleanup functions for subscriptions | MAJOR | Intervals, listeners cleaned up |
| PF.2 | No stale closures in intervals/callbacks | MAJOR | Functional updates used |
| PF.3 | Lists > 100 items use virtual scrolling | MINOR | TanStack Virtual for large lists |
| PF.4 | Loading, error, empty states for async data | CRITICAL | All three states handled |
| PF.5 | No direct state mutation | BLOCKER | Always use setter functions |
| PF.6 | exhaustive-deps ESLint warnings addressed | MAJOR | No suppressed dependency warnings |

---

## Patterns & Anti-Patterns

### Indicators of Quality

```tsx
// Explicit props interface with discriminated union
interface ButtonProps extends ComponentPropsWithoutRef<'button'> {
  variant: 'primary' | 'secondary';
  isLoading?: boolean;
}

// Query key factory
export const userKeys = {
  all: ['users'] as const,
  detail: (id: string) => [...userKeys.all, 'detail', id] as const,
};

// Proper cleanup in effects
useEffect(() => {
  const id = setInterval(() => setCount(c => c + 1), 1000);
  return () => clearInterval(id);
}, []);

// Server/Client split
// page.tsx (Server Component - no directive)
export default async function Page() {
  const data = await fetchData();
  return <ClientWidget initialData={data} />;
}

// widget.tsx
'use client';
export function ClientWidget({ initialData }: Props) {
  const [state, setState] = useState(initialData);
  return <button onClick={() => setState(/*...*/)}>Action</button>;
}

// Design system token usage — all visual values from the system
<Card className="p-4 shadow-sm">                        {/* spacing + elevation tokens */}
  <span className="text-sm text-muted-foreground">      {/* type scale + semantic color */}
    {title}
  </span>
  <div className="mt-2 text-2xl font-semibold">         {/* spacing + type scale */}
    {value}
  </div>
</Card>

// Reusing shared components — import, don't recreate
import { EmptyState } from '@/shared/components/empty-state';
import { Spinner } from '@/shared/components/spinner';
```

### Red Flags

```tsx
// ❌ any type
function Component(props: any) { ... }

// ❌ Nested component definition
function Parent() {
  function Child() { return <div>Bad</div>; } // Recreated every render!
  return <Child />;
}

// ❌ Derived state in useEffect
const [items, setItems] = useState([]);
const [filtered, setFiltered] = useState([]);
useEffect(() => setFiltered(items.filter(...)), [items]); // Don't store derived!

// ❌ Server data in local state
const [users, setUsers] = useState([]);
useEffect(() => {
  fetch('/api/users').then(r => r.json()).then(setUsers);
}, []); // Should use TanStack Query

// ❌ div as button
<div onClick={handleClick}>Click me</div>

// ❌ 'use client' at page level
'use client'; // Too high! Push to leaf components
export default function Page() { ... }

// ❌ Stale closure
useEffect(() => {
  setInterval(() => setCount(count + 1), 1000); // count is stale!
}, []);

// ❌ Magic numbers instead of design tokens
<div className="p-[13px] text-[15px] text-[#3a7bc8]">   // DS.1, DS.2, DS.3 violations

// ❌ Hardcoded color scale instead of semantic token
<div className="bg-zinc-950 text-zinc-100">              // DS.1 — use bg-background, text-foreground

// ❌ Duplicating a shared component inside a feature
// features/dashboard/components/spinner.tsx
function Spinner() { return <div className="animate-spin..." />; }  // RE.1 — shared Spinner already exists

// ❌ Domain-specific naming for a generic component
function VulnerabilityBadge({ status }: { status: string }) { ... }  // RE.6 — should be StatusBadge

// ❌ Forking a shared component instead of extending it
// features/settings/components/compact-card.tsx
function CompactCard({ children }) { ... }  // RE.7 — add density variant to shared Card instead
```

---

## Finding Output Format

Structure each finding as:

```markdown
### [BLOCKER] Usage of `any` type in UserCard props

**Location:** `src/components/UserCard.tsx:15`
**Criterion:** TS.1 - No `any` type usage

**Issue:**
Component props typed as `any`, losing all type safety benefits.

**Evidence:**
\```tsx
function UserCard(props: any) {
  return <div>{props.name}</div>;
}
\```

**Suggestion:**
Define explicit interface:
\```tsx
interface UserCardProps {
  name: string;
  email: string;
  avatar?: string;
}
function UserCard({ name, email, avatar }: UserCardProps) { ... }
\```

**Rationale:**
`any` defeats TypeScript's purpose, allows runtime errors, and makes refactoring dangerous.
```

---

## Review Summary Format

```markdown
# React Review Summary

## Verdict: NEEDS_WORK

| Metric | Count |
|--------|-------|
| Files Reviewed | 12 |
| Blockers | 0 |
| Critical | 2 |
| Major | 5 |
| Minor | 3 |
| Suggestions | 2 |
| Commendations | 1 |

## Key Findings

1. **[CRITICAL] SM.1** - Server data stored in useState instead of TanStack Query in `UserList.tsx`
2. **[CRITICAL] RE.1** - Duplicated Spinner component in `features/dashboard/` — shared version exists
3. **[MAJOR] DS.1** - Hardcoded hex colors in `MetricCard.tsx` instead of semantic tokens
4. **[MAJOR] AX.1** - Interactive div elements in `NavigationMenu.tsx`
5. **[MAJOR] RE.2** - Domain-agnostic FilterBar stuck in feature directory — should be shared

## Recommended Actions

1. Migrate `UserList.tsx` to use `useQuery` with proper query keys
2. Delete duplicated Spinner, import from shared
3. Replace `#3a7bc8` with `text-primary` semantic token
4. Replace `<div onClick>` with `<button>` elements in navigation
5. Promote FilterBar to shared layer with generic props

## Design System & Reusability Summary

| Check | Status |
|-------|--------|
| Token compliance | 2 violations (DS.1, DS.2) |
| Shared component reuse | 1 duplication (RE.1) |
| Layer placement | 1 misplaced component (RE.2) |
| Component naming | Clean |

## Skill Chain Decision

Invoking `implement/react` to address 2 CRITICAL findings before merge.
```

---

## Skill Chaining

### Chain Triggers

| Verdict | Chain Action | Target Skill |
|---------|--------------|--------------|
| `FAIL` | Mandatory implement | `implement/react` |
| `NEEDS_WORK` | Targeted fixes | `implement/react` |
| `PASS_WITH_SUGGESTIONS` | Optional improvements | None (suggestions only) |
| `PASS` | Continue pipeline | `test/unit` or `review/performance` |

### Handoff Protocol

When chaining to implement:

```markdown
**Chain Target:** `implement/react`
**Priority Findings:** TS.1, SM.1, RE.1, DS.1 (BLOCKER and CRITICAL)
**Context:** Review identified 2 critical issues requiring remediation

**Constraint:** Preserve existing component interfaces and test coverage
```

### Re-Review Loop

After implement completes, re-invoke this review with:

- Scope limited to modified files
- Focus on previously-failed criteria
- Maximum 3 iterations before escalation

---

## Integration Points

### Upstream Integration

This skill is invoked by:

| Source | Trigger | Context Provided |
|--------|---------|------------------|
| `implement/react` | Post-implementation | Changed files list |
| `/review` command | Explicit invocation | User-specified scope |
| `refactor/react` | Post-refactor validation | Modified components |

### Downstream Integration

This skill invokes:

| Target | Condition | Handoff |
|--------|-----------|---------|
| `implement/react` | Verdict ≠ PASS | Findings + priority order |
| `review/types` | Complex TypeScript issues | Type-specific findings |
| `test/unit` | Verdict = PASS | Component paths for coverage |

---

## Automated Checks

Run these commands during analysis:

```bash
# Type checking
npx tsc --noEmit

# Lint for React-specific issues
npx eslint --ext .tsx,.ts src/ --format stylish

# Search for any types
grep -rn ":\s*any" --include="*.tsx" --include="*.ts" src/

# Search for nested component definitions
grep -rn "function.*{$" --include="*.tsx" src/ -A 5 | grep "function"

# Search for div onClick anti-pattern
grep -rn "<div.*onClick" --include="*.tsx" src/

# Search for 'use client' placement
grep -rn "'use client'" --include="*.tsx" src/

# Search for hardcoded colors (design system violations)
grep -rn "bg-\(zinc\|slate\|gray\|neutral\|stone\)-" --include="*.tsx" src/
grep -rn "text-\(zinc\|slate\|gray\|neutral\|stone\)-" --include="*.tsx" src/
grep -rn "#[0-9a-fA-F]\{3,8\}" --include="*.tsx" src/

# Search for arbitrary Tailwind values (magic numbers)
grep -rn "\-\[.*px\]" --include="*.tsx" src/
```

---

## Examples

### Example 1: State Management Violation

**Input:** Review `src/components/UserList.tsx`

```tsx
'use client';
import { useState, useEffect } from 'react';

export function UserList() {
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch('/api/users')
      .then(r => r.json())
      .then(data => {
        setUsers(data);
        setLoading(false);
      });
  }, []);

  if (loading) return <div>Loading...</div>;
  return <ul>{users.map(u => <li key={u.id}>{u.name}</li>)}</ul>;
}
```

**Analysis:**

- SM.1 violated: Server data in useState
- TS.2 violated: No explicit props interface (implicit any for users)
- PF.4 partial: Loading state exists but no error state

**Verdict:** `NEEDS_WORK` → Chain to `implement/react`

### Example 2: Design System & Reusability Violations

**Input:** Review `src/features/dashboard/components/metric-display.tsx`

```tsx
function MetricDisplay({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-[8px] p-[14px] bg-[#1a2332] shadow-[0_1px_3px_rgba(0,0,0,0.3)]">
      <span className="text-[13px] text-[#8899aa]">{label}</span>
      <div className="mt-[6px] text-[28px] font-[600]">{value}</div>
    </div>
  );
}
```

**Analysis:**

- DS.1 violated: Hardcoded colors (`#1a2332`, `#8899aa`) instead of semantic tokens
- DS.2 violated: Arbitrary spacing (`p-[14px]`, `mt-[6px]`) instead of scale tokens
- DS.3 violated: Ad-hoc font size (`text-[13px]`, `text-[28px]`) instead of type scale
- DS.5 violated: Inline shadow instead of elevation token
- DS.6 violated: Arbitrary radius (`rounded-[8px]`) instead of scale token
- RE.2 flagged: This component is domain-agnostic — could be a shared `MetricCard`

**Suggestion:**
```tsx
import { Card } from '@/shared/components/card';

function MetricCard({ label, value, className }: MetricCardProps) {
  return (
    <Card className={cn('p-4', className)}>
      <span className="text-sm text-muted-foreground">{label}</span>
      <div className="mt-1 text-2xl font-semibold">{value}</div>
    </Card>
  );
}
```

**Rationale:** Every magic number creates visual drift. When 10 features each pick their own spacing and colors, the product looks inconsistent. Design tokens exist to prevent this — use them.

### Example 3: Accessibility Violation

**Input:** Review `src/components/ActionCard.tsx`

```tsx
export function ActionCard({ onClick, label }: { onClick: () => void; label: string }) {
  return (
    <div
      className="card hover:bg-gray-100 cursor-pointer"
      onClick={onClick}
    >
      {label}
    </div>
  );
}
```

**Analysis:**

- AX.1 violated: Using `<div onClick>` instead of `<button>`
- DS.1 flagged: `bg-gray-100` is a raw Tailwind color scale, not a semantic token

**Verdict:** `PASS_WITH_SUGGESTIONS` (if isolated) or `NEEDS_WORK` (if pattern is widespread)

---

## Deep References

Load on-demand for complex reviews:

| Reference | When to Load | Path |
|-----------|--------------|------|
| TypeScript patterns | Complex generic or conditional types | `refs/typescript.md` |
| State decision tree | Ambiguous state location decisions | `refs/state.md` |
| Component patterns | Compound component or polymorphic reviews | `refs/patterns.md` |
| Accessibility guide | ARIA implementation questions | `refs/accessibility.md` |
| Next.js patterns | App Router specific issues | `refs/nextjs.md` |

---

## Quality Gates

Before finalizing review output:

- [ ] All .tsx/.ts files in scope were analyzed
- [ ] Each finding has location + criterion + severity
- [ ] Verdict aligns with severity distribution
- [ ] Actionable suggestions provided for non-PASS verdicts
- [ ] `npx tsc --noEmit` was executed
- [ ] Chain decision is explicit and justified
- [ ] Output follows structured format
- [ ] **Design system token compliance checked (DS.1–DS.8)**
- [ ] **Reusability and layer placement checked (RE.1–RE.7)**
- [ ] **Review summary includes Design System & Reusability section**
