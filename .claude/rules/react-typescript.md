---
paths:
  - 'web/src/**/*.tsx'
  - 'web/src/**/*.ts'
---

# React + TypeScript Standards

Conventions for all React components, hooks, and TypeScript modules in the web application.

## Type Safety

1. Use TypeScript strict mode — no `any` types; use `unknown` with type guards when truly unknown
2. Define explicit `interface XxxProps` for every component
3. Extend native elements with `ComponentPropsWithoutRef<'element'>` or `ComponentProps<'element'>`
4. Use discriminated unions (`variant` field) for multi-mode components
5. No `// @ts-ignore` or `// @ts-expect-error` without justification comment

## Component Architecture

6. Define components at module level — never nest component definitions inside other components
7. One component per file; name file after the component (kebab-case)
8. Push `'use client'` to the smallest leaf component that needs interactivity
9. Keep Server Components for data fetching, Client Components for state/events
10. Max 7 props before using composition (children slots, compound components)
11. Accept `className` on every component, merge via `cn()` from `@/shared/lib/utils`

## State Management

12. Server data → TanStack Query (never `useState` + `useEffect` + `fetch`)
13. UI-only state (open/closed, hover) → `useState` colocated in component
14. Cross-component shared state → Zustand with granular selector hooks
15. Filters, pagination, sort → URL searchParams
16. Complex forms → React Hook Form + Zod schema
17. Never store derived state — compute during render
18. Create query key factories for cache management

## Styling (Tailwind + shadcn/ui)

19. Use semantic CSS tokens (`bg-primary`, `text-muted-foreground`) — never raw color scales (`bg-zinc-950`)
20. Never construct Tailwind classes dynamically (`` `bg-${color}-500` ``); use complete literal strings
21. Use CVA (`cva()` + `VariantProps`) for component variant styling
22. Never modify files in `shared/ui/` — wrap shadcn/ui base components for app-specific behavior
23. No `@apply` in component styles — use composition

## Accessibility

24. Interactive elements use `<button>`, `<a>`, `<input>` — never `<div onClick>`
25. Form inputs must have associated `<label>` elements
26. Images require `alt` text (`alt=""` if decorative)
27. Modals must trap focus and handle Escape key
28. Color must not be the sole information carrier

## Async Data

29. Handle all three states for async data: loading, error, empty
30. Use error boundaries at route level minimum
31. Return cleanup functions from effects with subscriptions/intervals
32. Use functional state updates in intervals to avoid stale closures

## Patterns

```tsx
// Component with cn(), explicit props, semantic tokens
interface MetricCardProps {
  title: string;
  value: number;
  trend: 'up' | 'down' | 'stable';
  className?: string;
}

export function MetricCard({ title, value, trend, className }: MetricCardProps) {
  return (
    <div className={cn("rounded-lg border bg-card p-4 text-card-foreground", className)}>
      <p className="text-sm text-muted-foreground">{title}</p>
      <p className="text-2xl font-semibold">{value}</p>
    </div>
  );
}
```

## Anti-Patterns

```tsx
// Server data in local state
const [users, setUsers] = useState([]);
useEffect(() => { fetch('/api/users').then(r => r.json()).then(setUsers) }, []);
// Fix: use useQuery({ queryKey: userKeys.all, queryFn: fetchUsers })

// Nested component
function Parent() {
  function Child() { return <div />; } // recreated every render
  return <Child />;
}

// Dynamic Tailwind class
const bg = `bg-${color}-500`; // won't be included in build
// Fix: use complete literals via cn() or CVA variants
```
