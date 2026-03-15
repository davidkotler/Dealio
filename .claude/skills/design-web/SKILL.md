---
name: design-web
version: 2.0.0
description: |
  Plan and architect React component hierarchies, state management, data flow, shared component reusability,
  and design system evolution before implementation. Use when starting a new feature, designing UI components,
  planning state architecture, structuring a React application, or when any UI work touches shared/reusable
  patterns. Also use when reviewing whether a component belongs in the feature layer or should be promoted
  to the shared layer for cross-feature reuse. Relevant for React, Next.js, TypeScript frontend design,
  component APIs, state management decisions, design system tokens, and UI consistency audits.

---

# Web/React Design

> Architect robust, scalable, and **visually consistent** React applications by making critical design decisions — including reusability and design system alignment — before writing code.

## Quick Reference

| Aspect | Details |
|--------|---------|
| **Invokes** | `implement/react`, `design/api`, `implement/pydantic` |
| **Invoked By** | `design/code`, `implement/python` (for full-stack features) |
| **Outputs** | Component tree, state map, props interfaces, data flow diagram, **reusability assessment**, **design system impact** |

---

## Core Workflow

1. **Audit**: Check the project's existing shared components and design system tokens — know what already exists before designing anything new
2. **Decompose**: Break UI into component hierarchy with clear responsibilities
3. **Reuse**: Identify which components belong in the shared layer vs. the feature layer
4. **Classify**: Categorize each state (server, client, URL, form)
5. **Contract**: Define TypeScript interfaces for all component props
6. **Flow**: Map data flow from source to consumption point
7. **Align**: Ensure every visual decision uses design system tokens — colors, spacing, typography, motion
8. **Guard**: Plan error boundaries and loading states
9. **Validate**: Review against accessibility, performance, and design consistency criteria
10. **Evolve**: Identify any new tokens, variants, or shared components the design system needs
11. **Chain**: Hand off to `implement/react` with complete design artifacts

---

## Reusability & Shared Component Strategy

Every feature you build contributes to (or fragments) the product's UI consistency. The goal is a codebase where building the next feature is faster than the last because the shared layer keeps growing.

### The Reusability Decision

When designing a component, always ask: **"Will another feature ever need this?"**

The answer determines where it lives:

| Signal | Decision |
|--------|----------|
| Component is domain-agnostic (displays data, collects input, provides layout) | → Shared layer |
| Component appears in 2+ features or could plausibly appear in a future feature | → Shared layer |
| Component is a composition of existing shared primitives into a reusable pattern | → Shared layer |
| Component is tightly coupled to one feature's data model or business rules | → Feature layer |
| Component wraps a third-party library to provide a project-consistent API | → Shared layer |

**The promotion path:** Components often start in a feature. When a second feature needs the same thing, that's the signal to extract it to shared. Design with this in mind — even feature-local components should be built with clean props interfaces so promotion is easy when the time comes.

### What Belongs in the Shared Layer

Think of the shared layer as the product's **component vocabulary** — the reusable building blocks every feature draws from:

- **UI Primitives**: Buttons, inputs, selects, dialogs, tooltips — the atomic elements (often from a component library like shadcn/ui or Radix)
- **Composed Components**: Cards, page headers, empty states, data tables, metric displays — assembled from primitives with consistent styling
- **Layout Components**: Containers, stacks, grids, sidebars — structural elements that enforce consistent spacing and alignment
- **Feedback Components**: Spinners, skeleton loaders, error fallbacks, toast notifications — consistent patterns for loading/error/empty states
- **Shared Hooks**: Data fetching utilities, media queries, debounce, intersection observers — logic that transcends any single feature
- **Shared Types**: Common prop interfaces, generic container types, API response wrappers

### Designing for Extraction

When building a feature-local component that might later become shared:

- **Props over hardcoding**: Accept text, icons, actions as props rather than hardcoding them
- **Domain-free naming**: Name by what the component *does*, not what domain it serves (`StatusBadge` not `VulnerabilityBadge`)
- **Minimal assumptions**: Don't assume the shape of data — accept generic types or simple primitives
- **Self-contained styling**: Use design system tokens, not feature-specific CSS classes

### Reusability Audit Template

Include this in every design artifact:

```
┌─────────────────────────────────────────────────────────────┐
│ REUSABILITY ASSESSMENT                                       │
├────────────────────┬──────────┬──────────────────────────────┤
│ Component          │ Layer    │ Rationale                    │
├────────────────────┼──────────┼──────────────────────────────┤
│ MetricCard         │ shared   │ Reusable across dashboards   │
│ VulnDetailPanel    │ feature  │ Coupled to vuln data model   │
│ FilterBar          │ shared   │ Generic filter/sort pattern  │
│ StatusBadge        │ shared   │ Used in 3+ features          │
│ ScanConfigForm     │ feature  │ Domain-specific form         │
└────────────────────┴──────────┴──────────────────────────────┘
```

---

## Design System Stewardship

A design system is not a static artifact — it's a living contract that evolves with the product. Every feature you design is an opportunity to strengthen (or accidentally undermine) the system.

### Why This Matters

Without a well-maintained design system, each new feature introduces visual drift — slightly different grays, inconsistent spacing, one-off font sizes. Over time, the product starts looking like it was built by 10 different teams. The design system prevents this by providing a single source of truth for every visual decision.

### The Design System Contract

Every visual property in your component designs should trace back to a design system token:

| Visual Property | Must Come From |
|----------------|----------------|
| Colors (backgrounds, text, borders) | Color tokens / semantic color roles |
| Font family, size, weight, line-height | Typography scale / text presets |
| Spacing (padding, margin, gap) | Spacing scale |
| Border radius | Radius tokens |
| Shadows / elevation | Shadow / elevation scale |
| Transitions / animations | Motion tokens (duration, easing) |
| Z-index layering | Z-index scale |

**If you need a value that doesn't exist in the design system, that's a signal — you should propose a new token, not use a magic number.**

### Evolving the Design System

When designing a feature, you may discover gaps in the current design system. Handle them intentionally:

**Adding new tokens:**
- A new severity level, status color, or density mode the system doesn't cover yet
- Document the new token, its semantic meaning, and where it applies
- Ensure it follows the existing naming and scaling conventions

**Adding new shared components:**
- A UI pattern that emerges across features (metric cards, filter bars, detail panels)
- Design it as a shared component from the start if you can see multi-feature use
- Or flag it as "promote to shared after validation" if usage is uncertain

**Extending existing components:**
- A new variant of an existing shared component (e.g., a "compact" card variant)
- Add the variant to the existing component's interface — don't create a parallel component

**The design system impact should be documented in every design artifact:**

```
┌─────────────────────────────────────────────────────────────┐
│ DESIGN SYSTEM IMPACT                                         │
├──────────────────────────────────────────────────────────────┤
│ New tokens: --severity-unknown (gray, for unscored items)    │
│ New shared component: FilterBar (select + search + reset)    │
│ Extended: Card — add `density` prop (compact | default)      │
│ Extended: Badge — add `pulse` animation variant              │
│ No changes: Typography, spacing, shadows                     │
└──────────────────────────────────────────────────────────────┘
```

### Design Consistency Checklist

Before finalizing any component design:

- [ ] All colors reference semantic tokens (not raw hex/oklch values)
- [ ] Typography uses the defined type scale (not ad-hoc font sizes)
- [ ] Spacing follows the spacing scale (not arbitrary pixel values)
- [ ] Component variants align with existing variant patterns (size scales, semantic variants)
- [ ] Dark mode / light mode work without feature-specific overrides
- [ ] Motion uses the motion token presets (duration, easing, spring configs)
- [ ] Icons come from the project's icon set (not mixed icon libraries)
- [ ] Density modes are respected where applicable (compact, default, comfortable)

### Anti-Patterns to Watch For

| Anti-Pattern | Why It's Harmful | What To Do Instead |
|-------------|------------------|--------------------|
| Magic numbers (`padding: 13px`) | Breaks spacing consistency | Use the spacing scale token |
| One-off color (`#3a7bc8`) | Visual drift between features | Use or define a semantic color token |
| Duplicating a shared component locally | Two versions diverge over time | Import from shared; extend if needed |
| Feature-specific font size | Typography inconsistency | Use the type scale; propose a new step if needed |
| Hardcoded transition (`0.3s ease`) | Inconsistent motion feel | Use motion tokens |
| Creating `MyFeatureButton` when `Button` exists | Parallel components = confusion | Add a variant to the existing Button |

---

## Decision Framework

### Component Decomposition

**MUST:**

- Identify leaf components (no children) vs container components
- Name components by domain concept, not visual appearance
- Limit component responsibility to single concern
- Define explicit public API (props) for each component
- **Check the project's shared component inventory before creating any new component**

**NEVER:**

- Create components named by visual style (`BlueButton`, `BigCard`)
- Design components with more than 7 props without composition
- Mix data fetching and presentation in same component design
- Design deeply nested prop interfaces (>2 levels)
- **Recreate a component that already exists in the shared layer**

**WHEN → THEN:**

| When | Then |
|------|------|
| UI element repeats 2+ times | Design as reusable shared component |
| Component needs variants | Use discriminated union props |
| Parent-child share implicit state | Design as compound component |
| Props would drill >2 levels | Design composition slots or context |
| Component exceeds single responsibility | Split into container + presenter |
| Component is domain-agnostic | Place in shared layer from the start |
| Shared component almost fits but not quite | Extend existing component with new variant — don't fork it |

---

### State Architecture

**MUST:**

- Classify every piece of state before implementation
- Colocate state with its primary consumer
- Identify cache invalidation triggers for server state
- Document state ownership in design artifacts

**NEVER:**

- Design derived values as stored state
- Plan to store server data in client state stores
- Design form state outside form boundaries
- Create global state for single-component concerns

**WHEN → THEN:**

| When | Then |
|------|------|
| Data comes from API | → TanStack Query / SWR (server state) |
| UI-only state (open/closed) | → useState, colocated |
| Shared across distant siblings | → Context or Zustand |
| Filter/sort/pagination | → URL params (searchParams) |
| Complex form with validation | → React Hook Form + Zod |
| Optimistic updates needed | → Plan mutation + rollback strategy |

**State Classification Template:**

```
┌─────────────────────────────────────────────────────────┐
│ STATE INVENTORY                                         │
├──────────────┬──────────────┬──────────────┬───────────┤
│ State        │ Type         │ Location     │ Scope     │
├──────────────┼──────────────┼──────────────┼───────────┤
│ users        │ server       │ TanStack     │ feature   │
│ selectedId   │ client       │ useState     │ component │
│ filters      │ url          │ searchParams │ route     │
│ formData     │ form         │ useForm      │ component │
└──────────────┴──────────────┴──────────────┴───────────┘
```

---

### Props Interface Design

**MUST:**

- Use `interface` for component props (extensible)
- Design discriminated unions for variant components
- Extend native element props with `ComponentPropsWithoutRef`
- Mark optional props with sensible defaults documented

**NEVER:**

- Use `any` or `unknown` in prop types
- Design required callback props without clear trigger
- Create boolean prop pairs (`isOpen`/`isClosed`)
- Design props that require parent to know implementation

**WHEN → THEN:**

| When | Then |
|------|------|
| Component wraps native element | Extend `ComponentPropsWithoutRef<'element'>` |
| Multiple mutually exclusive modes | Use discriminated union with `type` field |
| Component can render as different elements | Design polymorphic with `as` prop |
| Children have specific structure | Use compound component pattern |
| Callback needs data context | Include relevant data in callback signature |

**Props Pattern:**

```typescript
// Discriminated union for variants
type ButtonProps =
  | { variant: 'solid'; onClick: () => void }
  | { variant: 'link'; href: string };

// Compound component slots
interface DialogProps {
  children: ReactNode;  // Accepts Dialog.Title, Dialog.Body, Dialog.Actions
}
```

---

### Data Flow Design

**MUST:**

- Diagram data flow from source to UI
- Identify transformation/normalization points
- Plan loading, error, and empty states for each data source
- Design query key factories for cache management

**NEVER:**

- Design bidirectional data flow without explicit justification
- Plan prop drilling through 4+ component levels
- Design mutations without optimistic update strategy
- Ignore cache invalidation in design phase

**Data Flow Template:**

```
[API] ──► [Query Layer] ──► [Container] ──► [Presenter]
              │                   │              │
              ▼                   ▼              ▼
         Cache keys         Transform      Pure render
         Stale time         Normalize      No side effects
         Retry logic        Error map      Props only
```

---

### Accessibility Planning

**MUST:**

- Map semantic HTML elements to each component
- Identify ARIA requirements before implementation
- Plan keyboard navigation flow
- Design focus management for modals/dialogs

**NEVER:**

- Design interactive elements as div/span
- Plan color as sole information carrier
- Design without considering screen reader flow
- Ignore focus trap requirements for overlays

**Accessibility Checklist:**

| Component Type | Required Planning |
|----------------|-------------------|
| Button/Link | Native element, keyboard handler, focus style |
| Form Field | Label association, error announcement, validation timing |
| Modal/Dialog | Focus trap, escape handler, aria-modal, return focus |
| List/Grid | Arrow key navigation, aria-activedescendant |
| Live Content | aria-live region, update strategy |

---

### Error Boundary Planning

**MUST:**

- Design error boundary placement at route level minimum
- Plan fallback UI for each boundary
- Identify reset triggers for each boundary
- Design error reporting integration points

**WHEN → THEN:**

| When | Then |
|------|------|
| Route-level feature | Wrap with dedicated boundary |
| Third-party widget | Isolate with boundary |
| Data-dependent section | Boundary + retry mechanism |
| Critical vs non-critical | Different fallback strategies |

---

## Design Artifacts

### Output: Component Tree Document

```markdown
## Component Hierarchy

### Feature: UserDashboard

UserDashboard (Container)
├── DashboardHeader
│   ├── UserAvatar          ← shared (already exists)
│   └── NotificationBell    ← shared (already exists)
├── MetricsGrid (Server State: metrics query)
│   └── MetricCard (×n)    ← shared (new — promote)
└── ActivityFeed (Server State: activities query)
    ├── ActivityItem (×n)   ← feature (domain-specific)
    └── LoadMoreButton      ← shared (already exists)

### State Map
- metrics: server state, 5min stale, invalidate on user action
- activities: server state, infinite query, append-only
- selectedMetric: client state, local to MetricsGrid

### Reusability Assessment
- MetricCard → promote to shared (generic title/value/trend display)
- ActivityItem → keep in feature (tightly coupled to activity schema)
- DashboardHeader → feature composition of shared components

### Design System Impact
- No new tokens needed
- New shared component: MetricCard (title, value, trend, selected state)
```

### Output: Props Interface Sketch

```typescript
// Design phase - interfaces only, no implementation
interface MetricsGridProps {
  userId: string;
  timeRange: '7d' | '30d' | '90d';
  onMetricSelect?: (metricId: string) => void;
}

interface MetricCardProps {
  title: string;
  value: number;
  trend: 'up' | 'down' | 'stable';
  isSelected?: boolean;
}
```

---

## Skill Chaining

| Condition | Invoke | Handoff |
|-----------|--------|---------|
| Design complete, ready to code | `implement/react` | Component tree, state map, interfaces, **reusability assessment**, **design system impact** |
| API contracts needed | `design/api` | Data requirements, endpoint shapes |
| Backend models needed | `implement/pydantic` | Response schemas |

---

## Patterns

### Do

- **Start with an audit** — check existing shared components and design tokens before designing anything
- Start with user flow, decompose into components
- Design state location before component structure
- Sketch TypeScript interfaces in design docs
- Plan loading/error/empty states for every data source
- Identify compound component opportunities early
- **Mark each component as shared or feature-local in the design**
- **Document design system additions/extensions needed**
- **Name components generically when they could serve multiple features**

### Don't

- Jump to implementation without state classification
- Design prop drilling as default strategy
- Create god components in design phase
- Ignore accessibility until implementation
- Design mutations without optimistic update plan
- **Duplicate a component that exists in the shared layer**
- **Use magic numbers when design tokens exist**
- **Create feature-specific variants of shared components without extending the original**

---

## Quality Gates

Before handing off to `implement/react`:

- [ ] Component tree documented with responsibilities
- [ ] Every state classified (server/client/url/form)
- [ ] Props interfaces sketched for all components
- [ ] Data flow diagrammed from source to UI
- [ ] Loading, error, empty states planned
- [ ] Accessibility requirements identified
- [ ] Error boundaries placed strategically
- [ ] No component exceeds single responsibility
- [ ] **Reusability assessment completed — each component assigned to shared or feature layer**
- [ ] **Existing shared components checked — no unnecessary duplication**
- [ ] **All visual values trace to design system tokens — no magic numbers**
- [ ] **Design system impact documented — new tokens, components, or variants identified**

---

## Deep References

- **[refs/patterns.md](refs/patterns.md)**: Component composition patterns
- **[refs/state-decisions.md](refs/state-decisions.md)**: State management decision tree
- **[refs/accessibility.md](refs/accessibility.md)**: ARIA patterns by component type
