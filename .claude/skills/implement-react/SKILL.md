---
name: implement-react
version: 2.0.0
description: |
  Implement production-ready React components with TypeScript, proper state management, accessibility,
  shared component reusability, and design system token adherence. Use when building React components,
  implementing UI features, writing hooks, creating Next.js pages, or placing components in the correct
  layer (shared vs feature). Also use when promoting a feature component to the shared layer, extending
  an existing shared component with new variants, or adding new design system tokens.
  Relevant for React 18+/19, Next.js App Router, TypeScript, TanStack Query, Zustand, component implementation.
  Also covers shadcn/ui components, Tailwind CSS styling, CVA variants, theming, and Radix UI primitives.
---

# React Implementation

> Transform design artifacts into production-ready, type-safe, **design-system-aligned** React components — placing each one in the right layer.

## Quick Reference

| Aspect | Details |
|--------|---------|
| **Invokes** | `test/unit`, `review/react`, `implement/pydantic` (for API types) |
| **Invoked By** | `design/web`, `implement/python` (full-stack features) |
| **Inputs** | Component tree, state map, props interfaces, **reusability assessment**, **design system impact** from design phase |
| **Outputs** | Type-safe components, hooks, tests, accessible markup — **placed in correct layer with design token compliance** |

---

## Core Workflow

1. **Receive**: Accept design artifacts (component tree, state map, interfaces, reusability assessment, design system impact)
2. **Audit**: Check the project's existing shared components, hooks, and design tokens — know what already exists before writing anything
3. **Scaffold**: Create file structure matching component hierarchy, placing files in the correct layer (shared vs feature)
4. **Type**: Define TypeScript interfaces for all props and state
5. **Implement**: Build components bottom-up (leaves first), reusing existing shared components wherever possible
6. **Style**: Use design system tokens for every visual property — colors, spacing, typography, motion, shadows, radii
7. **Wire**: Connect state management (Query/Zustand/useState)
8. **Promote**: If the design calls for new shared components or design system tokens, implement them in the shared layer
9. **Validate**: Verify types compile, accessibility present, design token compliance
10. **Chain**: Hand off to `test/unit` for test coverage

---

## Must Do

### Code Quality
- Use **TypeScript strict mode** with explicit prop interfaces
- Separate **Server Components** (data) from **Client Components** (interactivity)
- Use **TanStack Query** for server state, **useState/Zustand** for client state
- Apply **semantic HTML** before ARIA attributes
- Include **loading, error, empty states** for all async data
- Use **`ComponentPropsWithoutRef<'element'>`** when extending native elements
- Create **query key factories** for cache management
- Return **cleanup functions** from effects with subscriptions

### Styling & Design System
- Use **`cn()` to merge className** on every component that accepts it
- Use **semantic CSS tokens** (`bg-primary`, `text-muted-foreground`) — never raw color scales
- Define **CVA variants** with semantic names for component styling
- **Wrap shadcn/ui base components** for app-specific behavior — don't modify `ui/` files
- Reference **spacing tokens** for all padding, margin, and gap values — no magic pixel numbers
- Use **typography presets** from the design system — no ad-hoc font sizes or weights
- Use **motion tokens** (duration, easing) for all transitions and animations — no hardcoded `0.3s ease`
- Use **shadow/elevation tokens** for depth — no inline box-shadow values

### Reusability & Layer Placement
- **Check the shared layer first** before creating any new component — if something similar exists, use or extend it
- Place **domain-agnostic components** (layout, display, input, feedback) in the shared layer
- Place **domain-coupled components** (tied to a specific feature's data model) in the feature layer
- Design feature-local components with **clean props interfaces** so promotion to shared is easy later
- Name components by **what they do**, not what domain they serve — `StatusBadge` not `VulnerabilityBadge`
- When extending a shared component, **add the variant to the existing component** — don't fork it into a parallel component
- Export new shared components through the **barrel file** so other features can discover them

## Never Do

### Code Quality
- Use `any` type — use `unknown` with type guards if truly unknown
- Store **server data in Zustand/Redux** — use TanStack Query
- Create **nested component definitions** inside other components
- Use **`useEffect` for derived state** — compute during render
- Place `'use client'` at **high levels** — push to leaf components
- Use **`<div onClick>`** for interactive elements — use `<button>`
- **Mutate state directly** — always use setter functions
- **Ignore exhaustive-deps** ESLint warnings

### Styling & Design System
- **Construct Tailwind classes dynamically** (`` `bg-${color}-500` ``) — use complete literal strings
- **Hardcode colors** (`bg-zinc-950`) instead of semantic tokens (`bg-background`)
- **Modify `components/ui/`** for app-specific logic — create wrappers
- **Use `@apply`** in component styles — use composition instead
- **Use magic pixel values** (`p-[13px]`) when a spacing scale token exists (`p-3`)
- **Hardcode font sizes** (`text-[15px]`) when the type scale covers it (`text-sm`)
- **Hardcode transitions** (`transition-all duration-300`) when motion tokens are defined

### Reusability
- **Duplicate a shared component** inside a feature because it's "easier" — import it
- **Create a parallel component** (`MyFeatureButton`) when the shared `Button` can be extended with a variant
- **Hardcode domain-specific text, icons, or labels** in a component that could be generic — accept them as props
- **Put reusable, domain-agnostic logic** in a feature directory — it belongs in the shared layer

---

## When → Then

| When | Then |
|------|------|
| Props extend native element | `interface Props extends ComponentPropsWithoutRef<'button'>` |
| Component has multiple variants | Use **discriminated union** with `variant` field |
| Parent-child share implicit state | Use **compound components** with Context |
| Data from API/server | **TanStack Query** with query key factory |
| UI-only state (modal, hover) | **useState** colocated in component |
| State shared across distant components | **Zustand** with selector hooks |
| Form with validation | **React Hook Form + Zod** schema |
| Filter/pagination in URL | **searchParams** + React Query |
| List > 100 items | **Virtual scrolling** (TanStack Virtual) |
| Component renders as different elements | **Polymorphic** with `as` prop or **`asChild`** (shadcn/ui) |
| Needs interactivity (state/effects/events) | **Client Component** (`'use client'`) |
| Direct data access, secrets | **Server Component** (default) |
| Building UI with shadcn/ui components | Compose from base `ui/` components, wrap for app logic |
| Component needs visual variants | **CVA** with `cva()` and `VariantProps` |
| Styling a reusable component | Accept `className`, merge via **`cn()`** |
| Need conditional Tailwind classes | Use **`cn()`** with objects/ternaries, never dynamic strings |
| Adding a new design system color | CSS variable pair (`:root` + `.dark`) + `@theme inline` |
| Component is domain-agnostic | Place in **shared layer** — not inside a feature directory |
| Shared component almost fits | **Extend with a new variant** — don't create a parallel component |
| Feature component needed by a second feature | **Promote** it to the shared layer, update both imports |
| New visual value needed (color, spacing step) | **Add a design token** — never use an ad-hoc magic number |
| Implementing from design artifacts | Honor the **reusability assessment** and **design system impact** sections |

---

## Component Patterns

### Compound Component

```tsx
const TabsContext = createContext<TabsContextValue | null>(null);

function useTabsContext() {
  const ctx = useContext(TabsContext);
  if (!ctx) throw new Error('Must be used within Tabs');
  return ctx;
}

function Tabs({ children, defaultValue }: TabsProps) {
  const [active, setActive] = useState(defaultValue);
  return (
    <TabsContext.Provider value={{ active, setActive }}>
      {children}
    </TabsContext.Provider>
  );
}

Tabs.Tab = Tab;
Tabs.Panel = TabPanel;
```

### Discriminated Union Props

```tsx
type ButtonProps =
  | { variant: 'button'; onClick: () => void; href?: never }
  | { variant: 'link'; href: string; onClick?: never };

function Button(props: ButtonProps) {
  if (props.variant === 'link') {
    return <a href={props.href}>{props.children}</a>;
  }
  return <button onClick={props.onClick}>{props.children}</button>;
}
```

### Server/Client Split

```tsx
// page.tsx (Server Component)
export default async function Page() {
  return (
    <Suspense fallback={<Skeleton />}>
      <DataSection />        {/* Server - fetches data */}
    </Suspense>
    <InteractiveWidget />    {/* Client - handles events */}
  );
}

// widget.tsx (Client Component)
'use client';
export function InteractiveWidget() {
  const [open, setOpen] = useState(false);
  return <button onClick={() => setOpen(true)}>Open</button>;
}
```

### Shared Component (Designed for Reuse)

A shared component accepts generic props, uses design system tokens for all visual properties, and avoids domain-specific assumptions. This makes it usable across any feature without modification.

```tsx
// shared/components/metric-card.tsx — domain-agnostic, reusable
interface MetricCardProps {
  title: string;
  value: string | number;
  trend?: 'up' | 'down' | 'stable';
  icon?: ReactNode;
  className?: string;
}

function MetricCard({ title, value, trend, icon, className }: MetricCardProps) {
  return (
    <Card className={cn('p-4', className)}>        {/* spacing token */}
      <div className="flex items-center gap-2">    {/* spacing token */}
        {icon}
        <span className="text-sm text-muted-foreground">{title}</span> {/* type scale + semantic color */}
      </div>
      <div className="mt-1 text-2xl font-semibold">{value}</div>       {/* type scale */}
      {trend && <TrendIndicator trend={trend} />}
    </Card>
  );
}
```

Notice how this component:
- Accepts generic props (`title`, `value`) — not domain-specific types
- Uses `className` with `cn()` for composition
- References semantic tokens (`text-muted-foreground`) not raw values
- Uses spacing scale (`p-4`, `gap-2`, `mt-1`) not magic numbers
- Uses type scale (`text-sm`, `text-2xl`) not ad-hoc sizes

---

## State Patterns

### Query Key Factory

```tsx
export const userKeys = {
  all: ['users'] as const,
  lists: () => [...userKeys.all, 'list'] as const,
  list: (filters: Filters) => [...userKeys.lists(), filters] as const,
  detail: (id: string) => [...userKeys.all, 'detail', id] as const,
};
```

### Optimistic Update

```tsx
const mutation = useMutation({
  mutationFn: updateTodo,
  onMutate: async (newTodo) => {
    await queryClient.cancelQueries({ queryKey: todoKeys.detail(newTodo.id) });
    const previous = queryClient.getQueryData(todoKeys.detail(newTodo.id));
    queryClient.setQueryData(todoKeys.detail(newTodo.id), newTodo);
    return { previous };
  },
  onError: (err, newTodo, ctx) => {
    queryClient.setQueryData(todoKeys.detail(newTodo.id), ctx?.previous);
  },
  onSettled: () => queryClient.invalidateQueries({ queryKey: todoKeys.all }),
});
```

### Zustand Selector

```tsx
// Granular selector - only re-renders when user changes
const useUser = () => useStore((s) => s.user);

// Full store subscription - re-renders on ANY change (avoid)
const store = useStore();
```

---

## Anti-Patterns

```tsx
// ❌ Nested component definition
function Parent() {
  function Child() { return <div>Bad</div>; }  // Recreated every render
  return <Child />;
}

// ❌ Derived state in useEffect
const [items, setItems] = useState([]);
const [filtered, setFiltered] = useState([]);  // Don't store derived!
useEffect(() => setFiltered(items.filter(...)), [items]);

// ❌ Stale closure in interval
useEffect(() => {
  setInterval(() => setCount(count + 1), 1000);  // count is stale
}, []);

// ✅ Functional update avoids stale closure
useEffect(() => {
  const id = setInterval(() => setCount(c => c + 1), 1000);
  return () => clearInterval(id);
}, []);

// ❌ Magic numbers instead of design tokens
<div className="p-[13px] text-[15px] text-[#3a7bc8]">  // visual drift

// ✅ Design system tokens
<div className="p-3 text-sm text-primary">  // consistent, themeable

// ❌ Duplicating a shared component
// features/dashboard/components/my-card.tsx — fork of shared Card
function MyCard({ children }) { return <div className="rounded-lg p-4 shadow">{children}</div>; }

// ✅ Reuse and extend
import { Card } from '@/shared/components/card';
<Card className="custom-additions">{children}</Card>
```

---

## Accessibility Checklist

- [ ] Interactive elements use `<button>`, `<a>`, `<input>`
- [ ] Form inputs have associated `<label>` elements
- [ ] Images have descriptive `alt` text (or `alt=""` if decorative)
- [ ] Focus visible on all interactive elements
- [ ] Modals trap focus and handle Escape key
- [ ] Color is not sole information carrier

---

## Skill Chaining

| Condition | Invoke | Handoff |
|-----------|--------|---------|
| Implementation complete | `test/unit` | Component paths, expected behaviors |
| API types needed | `implement/pydantic` | Response shapes |
| Quality review needed | `review/react` | File paths to review |

---

## Quality Gates

Before completing implementation:

### Code Quality
- [ ] `npx tsc --noEmit` passes with no errors
- [ ] All props have explicit TypeScript interfaces
- [ ] Server state uses TanStack Query, not local state
- [ ] `'use client'` only on leaf components needing interactivity
- [ ] Loading/error/empty states handled for async data
- [ ] No `any` types in component code
- [ ] Semantic HTML used for interactive elements

### Design System Compliance
- [ ] All colors use semantic tokens — no raw hex/oklch values or Tailwind color scales
- [ ] All spacing uses the scale — no arbitrary `p-[Xpx]` values
- [ ] Typography uses the type scale — no ad-hoc font sizes
- [ ] Motion uses token presets — no hardcoded durations or easings
- [ ] Icons from the project's icon set — no mixed icon libraries

### Reusability & Layer Placement
- [ ] Each component is in the correct layer (shared or feature) per the design's reusability assessment
- [ ] No shared component was duplicated inside a feature
- [ ] New shared components are exported through the barrel file
- [ ] New design tokens (if any) follow existing naming conventions
- [ ] Feature-local components have clean props interfaces ready for future promotion

---

## Deep References

- **[refs/shadcn.md](refs/shadcn.md)**: shadcn/ui components, CVA variants, `cn()`, theming, Tailwind CSS patterns
- **[refs/typescript.md](refs/typescript.md)**: Advanced TypeScript patterns
- **[refs/state.md](refs/state.md)**: State management decision tree
- **[refs/patterns.md](refs/patterns.md)**: Component composition patterns
- **[refs/hooks.md](refs/hooks.md)**: Custom hooks and effect patterns
- **[refs/nextjs.md](refs/nextjs.md)**: Next.js App Router patterns
- **[refs/accessibility.md](refs/accessibility.md)**: ARIA patterns by component
