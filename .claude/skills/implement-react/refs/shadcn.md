# shadcn/ui + Tailwind CSS Reference

> Patterns for building with shadcn/ui components, CVA variants, theming, and Tailwind CSS utilities.

---

## Architecture

shadcn/ui is a **code distribution system**, not an npm library. Components are copied into your project
via CLI and owned entirely by you. The three-layer pipeline:

1. **Radix UI primitives** — headless behavior, accessibility, keyboard nav, ARIA
2. **CVA (Class Variance Authority)** — type-safe Tailwind variant maps
3. **`cn()` utility** — merges base styles with overrides via `clsx` + `tailwind-merge`

Data flow: **CSS variables → `@theme inline` → Tailwind utilities → CVA variants → `cn()` merge → Radix primitive → DOM**

---

## The `cn()` Utility

Every component uses `cn()` for style composition. It resolves Tailwind conflicts so the last class wins:

```tsx
import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}
```

**Always accept `className` and merge via `cn()`** — this is how consumers override styles:

```tsx
function Card({ className, ...props }: CardProps) {
  return <div className={cn("rounded-lg border bg-card p-6", className)} {...props} />;
}
```

---

## CVA Variant System

CVA creates type-safe variant functions. `VariantProps<typeof xVariants>` auto-generates TypeScript types:

```tsx
import { cva, type VariantProps } from "class-variance-authority";

const buttonVariants = cva(
  "inline-flex items-center justify-center rounded-md text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:pointer-events-none disabled:opacity-50",
  {
    variants: {
      variant: {
        default: "bg-primary text-primary-foreground hover:bg-primary/90",
        destructive: "bg-destructive text-destructive-foreground hover:bg-destructive/90",
        outline: "border border-input hover:bg-accent hover:text-accent-foreground",
        ghost: "hover:bg-accent hover:text-accent-foreground",
        link: "text-primary underline-offset-4 hover:underline",
      },
      size: {
        default: "h-10 px-4 py-2",
        sm: "h-9 rounded-md px-3",
        lg: "h-11 rounded-md px-8",
        icon: "h-10 w-10",
      },
    },
    defaultVariants: { variant: "default", size: "default" },
  }
);
```

### Component with CVA (React 19 pattern)

```tsx
function Button({ className, variant, size, asChild = false, ...props }: ButtonProps) {
  const Comp = asChild ? Slot : "button";
  return <Comp className={cn(buttonVariants({ variant, size, className }))} {...props} />;
}
```

### Custom Variants

Edit the `cva()` call directly — you own the code. Use **semantic names** (not visual):

```tsx
const statusVariants = cva("rounded-lg px-4 py-2 text-sm font-medium", {
  variants: {
    status: {
      success: "bg-green-100 text-green-800 border-green-200",
      warning: "bg-yellow-100 text-yellow-800 border-yellow-200",
      error: "bg-red-100 text-red-800 border-red-200",
      info: "bg-blue-100 text-blue-800 border-blue-200",
    },
  },
  defaultVariants: { status: "info" },
});
```

### Compound Variants

Apply styles only when multiple variant conditions match:

```tsx
compoundVariants: [
  { variant: "outline", size: "sm", className: "border-2" },
]
```

---

## The `asChild` Pattern

Radix's `Slot` component enables polymorphic rendering — the component doesn't render its default element,
instead cloning its child and merging all props onto it:

```tsx
// Renders as <a> with all Button styles and behavior
<Button asChild>
  <Link href="/dashboard">Go to Dashboard</Link>
</Button>
```

Child props take precedence, event handlers are composed (child first), and `ref` is forwarded.

---

## Theming with CSS Variables

### Background/Foreground Convention

Every semantic color is a pair: base for background, `-foreground` for text on that background.

| Token | Purpose |
|-------|---------|
| `background` / `foreground` | Page-level |
| `card` / `card-foreground` | Card surfaces |
| `primary` / `primary-foreground` | Primary brand actions |
| `secondary` / `secondary-foreground` | Secondary actions |
| `muted` / `muted-foreground` | Subdued elements, helper text |
| `accent` / `accent-foreground` | Hover states, highlights |
| `destructive` / `destructive-foreground` | Dangerous actions |
| `border`, `input`, `ring` | Borders, input borders, focus ring |

### Always Use Semantic Tokens

```tsx
// Never hardcode colors — won't respond to theme changes
<div className="bg-zinc-950 text-white" />

// Use semantic tokens that adapt to theme
<div className="bg-background text-foreground" />
<div className="bg-primary text-primary-foreground" />
```

### Adding Custom Colors

Two steps — define variables, then register with Tailwind:

```css
:root {
  --warning: oklch(0.84 0.16 84);
  --warning-foreground: oklch(0.28 0.07 46);
}
.dark {
  --warning: oklch(0.41 0.11 46);
  --warning-foreground: oklch(0.99 0.02 95);
}
@theme inline {
  --color-warning: var(--warning);
  --color-warning-foreground: var(--warning-foreground);
}
```

### Dark Mode

Dark mode redefines CSS variables under `.dark`. The `@custom-variant dark (&:is(.dark *))` directive
connects to Tailwind's `dark:` modifier. Use `next-themes` for class-based switching. **Always define
both `:root` and `.dark` for every custom color.**

---

## Component Composition

### Wrapping vs. Modifying Base Components

**Do not modify `components/ui/` files for application-specific logic.** Create wrapper components:

```tsx
import { Button, type ButtonProps } from "@/components/ui/button";
import { cn } from "@/lib/utils";

export function IconButton({ icon, className, children, ...props }: ButtonProps & { icon: React.ReactNode }) {
  return (
    <Button className={cn("flex items-center gap-2", className)} {...props}>
      {icon}
      {children}
    </Button>
  );
}
```

Only modify base components when the change is truly global (e.g., adjusting focus ring styles system-wide).

### Semantic Application Components

Build components that represent your domain, not just visual variants:

```tsx
import { Button } from "@/components/ui/button";
import { LogIn } from "lucide-react";

export function LoginButton({ isLoading, ...props }: LoginButtonProps) {
  return (
    <Button disabled={isLoading} className="w-full" {...props}>
      <LogIn className="mr-2 h-4 w-4" />
      {isLoading ? "Signing in..." : "Sign In"}
    </Button>
  );
}
```

---

## Forms

### React Hook Form + Zod + shadcn/ui

```tsx
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

const schema = z.object({
  email: z.string().email("Invalid email address"),
  name: z.string().min(2, "Name must be at least 2 characters"),
});

type FormData = z.infer<typeof schema>;

export function ContactForm() {
  const { register, handleSubmit, formState: { errors } } = useForm<FormData>({
    resolver: zodResolver(schema),
  });

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
      <div className="space-y-2">
        <Label htmlFor="name">Name</Label>
        <Input id="name" {...register("name")} />
        {errors.name && (
          <p className="text-sm text-destructive">{errors.name.message}</p>
        )}
      </div>
      <Button type="submit">Submit</Button>
    </form>
  );
}
```

### Form Tips

- Use `React.useId()` for unique field IDs
- Link error messages via `aria-describedby`, set `aria-invalid` on errored fields
- Colocate Zod schemas with forms, or share via `validators.ts`

---

## Tailwind CSS Patterns

### Never Construct Class Names Dynamically

Tailwind's compiler scans for class names at build time. Dynamic construction breaks purging:

```tsx
// Broken: Tailwind can't see the final class
const bgColor = `bg-${color}-500`;

// Correct: Map of complete literal strings
const colorMap = {
  blue: "bg-blue-500",
  red: "bg-red-500",
  green: "bg-green-500",
} as const;
```

### Utility Best Practices

- Use shorthand: `py-4` not `pt-4 pb-4`; `gap-4` on flex/grid instead of margin on children
- Mobile-first responsive: `grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3`
- Prefer CSS interactions over React state: `group-hover:opacity-100` instead of `useState(hovered)`
- Use state variants directly: `hover:bg-primary/90 focus-visible:ring-2 disabled:opacity-50`
- Avoid `@apply` in components — use composition instead
- Avoid arbitrary values (`p-[13px]`); extend theme tokens if design system gaps exist

---

## Server vs. Client Components

| Type | Components | Directive |
|------|-----------|-----------|
| **Server** (default) | Card, Badge, Table, Separator, Avatar, Skeleton, Alert | None needed |
| **Client** | Dialog, DropdownMenu, Tabs, Accordion, Select, Tooltip, Form controls | `"use client"` |

Push `"use client"` boundaries as low as possible. Lazy-load heavy client components:

```tsx
const DataTable = lazy(() => import("@/components/data-table"));

function Dashboard() {
  return (
    <Suspense fallback={<div className="animate-pulse h-96 bg-muted rounded-lg" />}>
      <DataTable />
    </Suspense>
  );
}
```

---

## TypeScript Patterns (React 19)

React 19 passes `ref` as a regular prop — no more `forwardRef`. Components use `data-slot` instead of `displayName`:

```tsx
function AccordionItem({ className, ...props }: React.ComponentProps<typeof AccordionPrimitive.Item>) {
  return (
    <AccordionPrimitive.Item
      data-slot="accordion-item"
      className={cn("border-b last:border-b-0", className)}
      {...props}
    />
  );
}
```

---

## Animations

Default animations via `tw-animate-css`. Radix exposes `data-[state=open]` / `data-[state=closed]`:

```tsx
<div className="animate-in fade-in-0 slide-in-from-bottom-4 duration-300" />
```

For advanced animations, wrap with Framer Motion:

```tsx
const MotionButton = motion(Button);
<MotionButton whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }}>Click</MotionButton>
```

---

## When → Then

| When | Then |
|------|------|
| Building a new UI component | Start with shadcn/ui base, compose from it |
| Need app-specific behavior on base component | Create wrapper component, don't modify `ui/` |
| Creating a component with visual variants | Use CVA with semantic variant names |
| Accepting `className` on any component | Merge via `cn(defaultClasses, className)` |
| Adding a new color to the design system | Define CSS variable pair (`:root` + `.dark`) + `@theme inline` |
| Using colors in components | Always use semantic tokens (`bg-primary`), never raw scales (`bg-blue-500`) |
| Component needs to render as different element | Use `asChild` prop with Radix `Slot` |
| Form with validation | React Hook Form + Zod + shadcn Input/Label |
| Conditional styling | Use `cn()` with objects or ternaries, never dynamic class construction |
| Heavy interactive component (DataTable, DatePicker) | Lazy-load with `React.lazy` + `Suspense` |
| Multiple themes beyond light/dark | Additional CSS classes redefining the same variables |

---

## Common Pitfalls

| Pitfall | Fix |
|---------|-----|
| Modifying `components/ui/` for app logic | Create wrapper components that compose the base |
| Hardcoding colors (`bg-zinc-950`) | Use semantic tokens (`bg-background`) |
| Dynamic class construction (`bg-${x}-500`) | Use complete literal strings in a map object |
| Forgetting dark mode for custom colors | Always define both `:root` and `.dark` variables |
| Missing `"use client"` on interactive components | Any component with hooks or event handlers needs the directive |
| Using `@apply` in component styles | Use component composition instead |
| Removing `asChild` from Radix wrappers | Breaks semantic HTML structure; test keyboard nav |
| Using `forwardRef` (React 19) | Use direct function with `React.ComponentProps` |
| Overriding focus styles without replacement | Removes visible focus indicators; accessibility violation |
| Barrel exports for UI components | Import directly from component files |
