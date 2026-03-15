# Next.js App Router Reference

> Server/Client component patterns for Next.js 14+ App Router.

---

## Component Types

| Type | Default | Characteristics |
|------|---------|-----------------|
| **Server Component** | ✅ Yes | Direct data access, secrets, no bundle cost |
| **Client Component** | Requires `'use client'` | State, effects, event handlers, browser APIs |

---

## When to Use Each

### Server Components (Default)

- Direct database/API calls
- Access to secrets (non-`NEXT_PUBLIC_` env vars)
- Heavy dependencies (markdown parsers, syntax highlighters)
- Reduce client bundle size
- SEO-critical content

### Client Components (`'use client'`)

- useState, useEffect, useRef
- Event handlers (onClick, onChange)
- Browser APIs (window, localStorage)
- Custom hooks with state
- Third-party libraries requiring browser

---

## Core Pattern: Push `'use client'` Down

**Goal:** Keep `'use client'` on leaf components to maximize Server Component benefits.

```tsx
// ❌ Bad: Client boundary too high
'use client';  // Everything below is now Client
export default function Page() {
  const [count, setCount] = useState(0);
  return (
    <div>
      <Header />           {/* Unnecessarily Client */}
      <DataSection />      {/* Unnecessarily Client */}
      <Counter count={count} onClick={() => setCount(c => c + 1)} />
    </div>
  );
}
```

```tsx
// ✅ Good: Client boundary on leaf only
// page.tsx (Server Component)
export default function Page() {
  return (
    <div>
      <Header />           {/* Server Component */}
      <DataSection />      {/* Server Component */}
      <Counter />          {/* Client Component */}
    </div>
  );
}

// counter.tsx (Client Component - leaf)
'use client';
export function Counter() {
  const [count, setCount] = useState(0);
  return <button onClick={() => setCount(c => c + 1)}>{count}</button>;
}
```

---

## Composition Pattern: Server Through Client

Pass Server Components as children of Client Components.

```tsx
// modal.tsx (Client Component)
'use client';
export function Modal({ children }: { children: ReactNode }) {
  const [isOpen, setIsOpen] = useState(false);
  if (!isOpen) return <button onClick={() => setIsOpen(true)}>Open</button>;
  return <div className="modal">{children}</div>;
}

// page.tsx (Server Component)
import { Modal } from './modal';
import { ProductDetails } from './product-details';  // Server Component!

export default async function Page() {
  return (
    <Modal>
      <ProductDetails />  {/* Remains a Server Component */}
    </Modal>
  );
}
```

---

## Data Fetching

### In Server Components: Call Directly

```tsx
// ✅ No Route Handler needed
async function ProductList() {
  const products = await db.product.findMany();  // Direct DB call
  return (
    <ul>
      {products.map(p => <li key={p.id}>{p.name}</li>)}
    </ul>
  );
}
```

### Parallel Fetching

```tsx
// ✅ Promise.all for parallel requests
async function Dashboard() {
  const [metrics, users, orders] = await Promise.all([
    getMetrics(),
    getUsers(),
    getOrders(),
  ]);

  return (
    <div>
      <MetricsPanel data={metrics} />
      <UsersPanel data={users} />
      <OrdersPanel data={orders} />
    </div>
  );
}
```

### Streaming with Suspense

```tsx
// page.tsx
export default function Page() {
  return (
    <div>
      <Header />  {/* Renders immediately */}

      <Suspense fallback={<MetricsSkeleton />}>
        <Metrics />  {/* Streams when ready */}
      </Suspense>

      <Suspense fallback={<ChartSkeleton />}>
        <Chart />  {/* Streams independently */}
      </Suspense>
    </div>
  );
}
```

---

## TanStack Query Hydration

### Prefetch in Server Component

```tsx
// app/todos/page.tsx (Server Component)
import { dehydrate, HydrationBoundary, QueryClient } from '@tanstack/react-query';
import { todoListOptions } from '@/lib/queries';

export default async function Page() {
  const queryClient = new QueryClient();
  await queryClient.prefetchQuery(todoListOptions());

  return (
    <HydrationBoundary state={dehydrate(queryClient)}>
      <TodoList />  {/* Client Component using useQuery */}
    </HydrationBoundary>
  );
}
```

### Query Client Provider

```tsx
// app/providers.tsx
'use client';

export function Providers({ children }: { children: ReactNode }) {
  const [queryClient] = useState(() => new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: 60 * 1000,  // Prevent immediate refetch after hydration
      },
    },
  }));

  return (
    <QueryClientProvider client={queryClient}>
      {children}
    </QueryClientProvider>
  );
}

// app/layout.tsx
export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html>
      <body>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
```

---

## Error Handling

### Route Error Boundary

```tsx
// app/dashboard/error.tsx
'use client';

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <div role="alert">
      <h2>Something went wrong!</h2>
      <button onClick={reset}>Try again</button>
    </div>
  );
}
```

### Global Error (Root Layout)

```tsx
// app/global-error.tsx
'use client';

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <html>
      <body>
        <h2>Something went wrong!</h2>
        <button onClick={reset}>Try again</button>
      </body>
    </html>
  );
}
```

**Note:** `error.tsx` doesn't catch errors in the same-level `layout.tsx`. Use `global-error.tsx` for root layout errors.

---

## Loading States

```tsx
// app/dashboard/loading.tsx
export default function Loading() {
  return <DashboardSkeleton />;
}
```

---

## URL State with searchParams

### In Server Components

```tsx
// page.tsx (Server Component)
export default function Page({
  searchParams,
}: {
  searchParams: { page?: string; sort?: string };
}) {
  const page = Number(searchParams.page) || 1;
  const sort = searchParams.sort || 'date';

  return <ProductList page={page} sort={sort} />;
}
```

### In Client Components

```tsx
'use client';
import { useSearchParams, useRouter, usePathname } from 'next/navigation';

export function Filters() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();

  const updateFilter = (key: string, value: string) => {
    const params = new URLSearchParams(searchParams);
    params.set(key, value);
    router.push(`${pathname}?${params.toString()}`);
  };

  return (
    <select onChange={(e) => updateFilter('sort', e.target.value)}>
      <option value="date">Date</option>
      <option value="price">Price</option>
    </select>
  );
}
```

---

## Anti-Patterns

### ❌ Fetching from Route Handlers in Server Components

```tsx
// ❌ Unnecessary network hop
async function Products() {
  const res = await fetch('/api/products');  // Route Handler
  const products = await res.json();
  return <ProductList products={products} />;
}

// ✅ Direct call
async function Products() {
  const products = await db.product.findMany();
  return <ProductList products={products} />;
}
```

### ❌ `redirect()` Inside try/catch

```tsx
// ❌ redirect() throws internally
try {
  if (!user) redirect('/login');
} catch (e) {
  // Catches the redirect!
}

// ✅ Check before try block
if (!user) redirect('/login');
try {
  // ... other logic
} catch (e) {}
```

### ❌ Importing Server Components into Client Components

```tsx
// ❌ Won't work - Server Component imported into Client
'use client';
import { ServerComponent } from './server';  // Error!

// ✅ Pass as children instead
'use client';
export function ClientWrapper({ children }: { children: ReactNode }) {
  return <div>{children}</div>;
}
```

---

## Protect Sensitive Code

```tsx
// lib/db.ts
import 'server-only';  // Throws if imported in Client Component

export async function getUsers() {
  return db.user.findMany();
}
```
