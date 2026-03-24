# Dealio Price Alert — Frontend Design Document

> Produced from: UI/UX Pro Max + design/web skills, scoped to actual backend API contracts.
> Date: 2026-03-18

---

## 1. Backend API Audit — What Is Actually Supported

Before designing any screen, every user flow is anchored to a real backend endpoint.

### 1.1 Auth Endpoints (`/api/v1/auth/...`)

| Method | Path | Request | Response | Error Codes |
|--------|------|---------|----------|-------------|
| POST | `/auth/register` | `{email, password}` | `{id, email, created_at}` + session cookie | `EMAIL_ALREADY_REGISTERED` (409), `WEAK_PASSWORD` (422) |
| POST | `/auth/login` | `{email, password}` | `{id, email}` + session cookie | `INVALID_CREDENTIALS` (401) |
| POST | `/auth/logout` | — | 204, clears cookie | — |
| GET | `/auth/google/login` | — | 302 redirect to Google | — |
| GET | `/auth/google/callback` | `?code=&state=` | 303 redirect → `/dashboard` | Redirects with `?error=` param |
| POST | `/auth/password-reset` | `{email}` | 204 | — (always 204 for security) |
| POST | `/auth/password-reset/confirm` | `{token, new_password}` | 204 | `INVALID_RESET_TOKEN` (400) |
| PUT | `/auth/password` | `{current_password, new_password}` | 204 | `PASSWORD_CHANGE_NOT_ALLOWED` (422) |

**Auth mechanism:** httpOnly session cookie (`session`), max_age = 86400s (1 day).
No access token is returned in the response body — the frontend never handles a Bearer token.

### 1.2 Product Endpoints (`/api/v1/...`)

| Method | Path | Request | Response | Error Codes |
|--------|------|---------|----------|-------------|
| GET | `/products` | — (auth cookie) | `{products: ProductResponse[], unread_notification_count: int}` | — |
| POST | `/products` | `{url: string}` | `ProductResponse` | `INVALID_PRODUCT_URL` (422), `PRODUCT_LIMIT_EXCEEDED` (422), `DUPLICATE_PRODUCT` (409), `SCRAPING_FAILED` (422) |
| DELETE | `/products/{id}` | — | 204 | `PRODUCT_NOT_FOUND` (404) |

**`ProductResponse` shape:**
```ts
{
  id: string           // UUID
  url: string
  product_name: string
  current_price: string   // decimal string e.g. "89.99"
  previous_price: string | null
  last_checked_at: string | null  // ISO datetime
  created_at: string              // ISO datetime
}
```

**`DashboardResponse` shape:**
```ts
{
  products: ProductResponse[]
  unread_notification_count: int
}
```

### 1.3 Notification Endpoints (`/api/v1/...`)

| Method | Path | Request | Response | Error Codes |
|--------|------|---------|----------|-------------|
| GET | `/notifications` | `?cursor=&limit=1-50` | `{notifications: NotificationResponse[], next_cursor: string \| null}` | — |
| PATCH | `/notifications/{id}/read` | — | `NotificationResponse` | `NOTIFICATION_NOT_FOUND` (404) |

**`NotificationResponse` shape:**
```ts
{
  id: string
  tracked_product_id: string
  old_price: string    // decimal string
  new_price: string    // decimal string
  created_at: string   // ISO datetime
  read_at: string | null
}
```

**Error response envelope (all errors):**
```ts
{ detail: string; code: string }
```

---

## 2. Backend Constraints — What Changes From the HLD

These are critical corrections to `price_alert_frontend_hld.md`:

| HLD Assumption | Actual Backend Behaviour | Frontend Impact |
|----------------|--------------------------|-----------------|
| Access token in Zustand + refresh cookie | Single httpOnly session cookie (1 day) | No token refresh interceptor needed; 401 → redirect to login |
| `POST /products` starts async scraping → "Checking price..." loading state | Scraping is **synchronous** — product is returned with full data or fails | No pending/loading card state; show error on `SCRAPING_FAILED` instead |
| `/me` endpoint for current user | **Does not exist** | Persist `{id, email}` from login/register in localStorage; invalidate on 401 |
| "Mark all as read" batch endpoint | **Does not exist** — only `PATCH /notifications/{id}/read` | Visiting the page does NOT auto-mark all; user marks individually or we call each one |
| Product Detail has its own API call | No `GET /products/{id}` endpoint | Product Detail reads from TanStack Query cache of `GET /products` |
| Plan usage bar showing X/5 | No plan/limits endpoint | Derive usage from `products.length`; hardcode limit of 5 from `config/plans.ts` |
| Upgrade / Plans page | No billing/plan endpoint | Build as static page (waitlist CTA only, no live plan data) |
| `Next check scheduled at` on Product Detail | **Not in response** | Remove from Product Detail design |

---

## 3. Screen Inventory — Backend-Constrained

### Screens IN (backend supports full flow)
1. **Landing Page** — static
2. **Sign Up** — `POST /auth/register`, Google via `GET /auth/google/login`
3. **Log In** — `POST /auth/login`, Google via `GET /auth/google/login`
4. **Forgot Password** — `POST /auth/password-reset`
5. **Reset Password** — `POST /auth/password-reset/confirm` (token from `?token=` query param)
6. **Dashboard** — `GET /products` (products + unread count)
7. **Add Product** (panel) — `POST /products`
8. **Product Detail** — client-side, reads from `GET /products` cache
9. **Notifications** — `GET /notifications`, `PATCH /notifications/{id}/read`
10. **Settings** — `PUT /auth/password` (password change only)

### Screens OUT (no backend support in MVP)
- ~~Upgrade / Plans page~~ → static waitlist page only (no live data)
- ~~Delete Account~~ → not implemented
- ~~Mark all as read~~ → individual dismiss only

---

## 4. Design System

### 4.1 Color Palette

Based on UI/UX Pro Max recommendation for "price alert tracker saas productivity minimal trustworthy":

| Token | Tailwind | Hex | Usage |
|-------|----------|-----|-------|
| `--primary` | `blue-600` | `#2563EB` | Primary CTA, links, active nav |
| `--primary-hover` | `blue-700` | `#1D4ED8` | Button hover |
| `--success` | `green-600` | `#16A34A` | Price drop indicators, success states |
| `--warning` | `amber-600` | `#D97706` | Plan limit warnings, scrape failed |
| `--danger` | `red-600` | `#DC2626` | Errors, destructive actions |
| `--surface` | `slate-50` | `#F8FAFC` | Page background |
| `--card` | `white` | `#FFFFFF` | Card backgrounds |
| `--border` | `slate-200` | `#E2E8F0` | Card borders, dividers |
| `--text-primary` | `slate-900` | `#0F172A` | Headings, primary text |
| `--text-secondary` | `slate-500` | `#64748B` | Labels, metadata |
| `--text-muted` | `slate-400` | `#94A3B8` | Placeholders, disabled |

All color references in components use Tailwind utility classes that map to these tokens.
Never use raw hex values in component code.

### 4.2 Typography

**Font:** Plus Jakarta Sans (Google Fonts) — friendly, modern, SaaS-grade, highly legible.

```css
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700&display=swap');
```

| Role | Size | Weight | Tailwind | Usage |
|------|------|--------|----------|-------|
| Display | 36px | 700 | `text-4xl font-bold` | Landing headline |
| H1 | 30px | 700 | `text-3xl font-bold` | Page titles |
| H2 | 24px | 600 | `text-2xl font-semibold` | Section headers |
| H3 | 18px | 600 | `text-lg font-semibold` | Card titles |
| Body | 16px | 400 | `text-base` | Default text |
| Small | 14px | 400 | `text-sm` | Labels, metadata |
| XSmall | 12px | 400 | `text-xs` | Timestamps, badges |

### 4.3 Spacing Scale

4px base unit (Tailwind default). Key values:
- Component padding: `p-4` (16px)
- Card padding: `p-5` (20px)
- Section gaps: `gap-6` (24px)
- Page horizontal padding: `px-4` mobile → `px-8` desktop

### 4.4 Border Radius

| Element | Tailwind | px |
|---------|----------|-----|
| Cards | `rounded-xl` | 12px |
| Buttons, Inputs | `rounded-lg` | 8px |
| Badges | `rounded-full` | — |
| Small chips | `rounded-md` | 6px |

### 4.5 Shadows

| Context | Tailwind | Usage |
|---------|----------|-------|
| Cards (resting) | `shadow-sm` | Subtle lift |
| Cards (hover) | `shadow-md` | Hover interaction |
| Panels/Modals | `shadow-xl` | Overlaid content |
| Dropdowns | `shadow-lg` | Contextual menus |

### 4.6 Motion Tokens

All animations use Framer Motion. Respect `prefers-reduced-motion`.

| Interaction | Duration | Easing |
|-------------|----------|--------|
| Micro-interactions (hover, press) | 150ms | `ease-out` |
| Card enter/exit | 200ms | `ease-out` / `ease-in` |
| Panel slide-in (desktop) | 250ms | `ease-out` |
| Bottom sheet (mobile) | 300ms | `spring` |
| Page transition | 150ms | `ease-out` (opacity only) |
| Skeleton shimmer | 1.5s | `linear` loop |

---

## 5. Component Architecture

### 5.1 Full Component Tree

```
src/
├── main.tsx                    — App entry + QueryClient + Sonner provider
├── App.tsx                     — Router + route guards
│
├── config/
│   └── plans.ts               — MAX_PRODUCTS = 5 (mirrors backend limit)
│
├── api/
│   ├── client.ts              — Axios: baseURL, withCredentials, 401 interceptor
│   ├── auth.api.ts            — register, login, logout, googleLogin, passwordReset, confirmReset, changePassword
│   ├── products.api.ts        — getProducts (dashboard), addProduct, removeProduct
│   └── notifications.api.ts  — listNotifications (cursor-paginated), readNotification
│
├── store/
│   └── auth.store.ts          — Zustand: {user: {id,email} | null}; persisted to localStorage
│
├── hooks/
│   ├── useAuth.ts             — Reads auth.store, provides isAuthenticated, logout
│   ├── useProducts.ts         — TanStack Query wrappers: useDashboard, useAddProduct, useRemoveProduct
│   └── useNotifications.ts   — useInfiniteNotifications, useReadNotification
│
├── schemas/
│   ├── auth.schema.ts         — Zod: signUpSchema, loginSchema, changePasswordSchema
│   └── product.schema.ts     — Zod: addProductSchema
│
├── types/
│   ├── auth.types.ts          — User, AuthStore interfaces
│   ├── product.types.ts       — ProductResponse, DashboardResponse
│   └── notification.types.ts — NotificationResponse, NotificationListResponse
│
├── utils/
│   ├── formatPrice.ts         — "$89.99" from decimal string
│   ├── formatDate.ts          — relative time ("2 hours ago")
│   ├── priceDiff.ts           — calculateDrop(current, previous) → {amount, percent}
│   └── cn.ts                  — Tailwind class merge (clsx + tailwind-merge)
│
├── components/
│   ├── ui/                    — shadcn/ui primitives (Button, Input, Dialog, Sheet…)
│   │
│   ├── layout/                — SHARED
│   │   ├── AppShell.tsx       — Authenticated wrapper: TopNav + SideNav/BottomNav + <Outlet>
│   │   ├── TopNav.tsx         — Logo, NotificationBell, UserMenu
│   │   ├── SideNav.tsx        — Desktop sidebar (Dashboard, Notifications, Settings)
│   │   └── BottomNav.tsx      — Mobile bottom bar (3 items max)
│   │
│   ├── auth/                  — FEATURE
│   │   ├── AuthCard.tsx       — Card wrapper for auth pages (logo + children)
│   │   └── PasswordInput.tsx  — Input + show/hide toggle (SHARED candidate)
│   │
│   ├── products/              — FEATURE
│   │   ├── ProductCard.tsx    — Card with Active / PriceDropped / ScrapeFailed states
│   │   ├── ProductGrid.tsx    — Responsive grid of ProductCards + skeleton states
│   │   ├── AddProductPanel.tsx — Sheet (desktop: right-slide, mobile: bottom-sheet)
│   │   ├── PlanUsageBar.tsx   — "X of 5 used" progress bar with colour states
│   │   └── EmptyProducts.tsx  — Illustration + "Add your first product" CTA
│   │
│   ├── notifications/         — FEATURE
│   │   ├── NotificationItem.tsx — Single notification row
│   │   └── EmptyNotifications.tsx
│   │
│   └── shared/                — SHARED
│       ├── SkeletonCard.tsx   — Product card skeleton (shimmer)
│       ├── SkeletonList.tsx   — List item skeleton
│       ├── ErrorBoundary.tsx  — Route-level error boundary
│       └── ConfirmDialog.tsx  — Reusable confirmation modal
│
└── pages/
    ├── LandingPage.tsx
    ├── SignUpPage.tsx
    ├── LoginPage.tsx
    ├── ForgotPasswordPage.tsx
    ├── ResetPasswordPage.tsx
    ├── DashboardPage.tsx
    ├── ProductDetailPage.tsx   — Reads from TanStack Query cache (no extra API call)
    ├── NotificationsPage.tsx
    └── SettingsPage.tsx
```

### 5.2 Reusability Assessment

```
┌─────────────────────────────────────────────────────────────┐
│ REUSABILITY ASSESSMENT                                       │
├────────────────────────┬──────────┬──────────────────────────┤
│ Component              │ Layer    │ Rationale                │
├────────────────────────┼──────────┼──────────────────────────┤
│ AppShell               │ shared   │ Wraps all auth pages      │
│ TopNav                 │ shared   │ Present on all auth pages │
│ SideNav                │ shared   │ Present on all auth pages │
│ BottomNav              │ shared   │ Mobile nav, all pages     │
│ PasswordInput          │ shared   │ Used in 3 auth forms      │
│ ConfirmDialog          │ shared   │ Delete product + future   │
│ SkeletonCard           │ shared   │ Products + future lists   │
│ SkeletonList           │ shared   │ Notifications + future    │
│ ErrorBoundary          │ shared   │ All routes                │
│ AuthCard               │ shared   │ All auth pages            │
│ ProductCard            │ feature  │ Coupled to product schema │
│ ProductGrid            │ feature  │ Specific grid layout      │
│ AddProductPanel        │ feature  │ Product-specific logic    │
│ PlanUsageBar           │ feature  │ Plan limit + product count│
│ EmptyProducts          │ feature  │ Product-specific copy     │
│ NotificationItem       │ feature  │ Notification schema       │
│ EmptyNotifications     │ feature  │ Notification-specific     │
└────────────────────────┴──────────┴──────────────────────────┘
```

### 5.3 Design System Impact

```
┌─────────────────────────────────────────────────────────────┐
│ DESIGN SYSTEM IMPACT                                         │
├──────────────────────────────────────────────────────────────┤
│ New tokens: none (all map to Tailwind semantic palette)      │
│ New shared components:                                        │
│   PasswordInput — input + show/hide toggle, reused 3x        │
│   SkeletonCard  — shimmer placeholder, reused 2+ times       │
│   ConfirmDialog — wraps shadcn Dialog with confirm pattern   │
│ Extended: shadcn Sheet — used for AddProductPanel bottom/side│
│ No changes: Typography, shadows, border-radius scale         │
└─────────────────────────────────────────────────────────────┘
```

---

## 6. State Architecture

### 6.1 State Inventory

```
┌─────────────────────────────────────────────────────────────┐
│ STATE INVENTORY                                             │
├──────────────────┬──────────────┬─────────────┬────────────┤
│ State            │ Type         │ Location    │ Scope      │
├──────────────────┼──────────────┼─────────────┼────────────┤
│ user (id,email)  │ client       │ Zustand     │ global     │
│ dashboard data   │ server       │ TanStack    │ app        │
│ notifications    │ server       │ TanStack    │ app        │
│ addPanelOpen     │ client       │ useState    │ Dashboard  │
│ removeConfirmId  │ client       │ useState    │ Dashboard  │
│ selectedProduct  │ url          │ /products/:id│ route     │
│ notif.cursor     │ server       │ TanStack    │ Notif page │
│ form (sign up)   │ form         │ useForm     │ component  │
│ form (login)     │ form         │ useForm     │ component  │
│ form (add prod)  │ form         │ useForm     │ component  │
│ form (change pw) │ form         │ useForm     │ component  │
└──────────────────┴──────────────┴─────────────┴────────────┘
```

### 6.2 Auth Store (Zustand + localStorage)

```ts
// store/auth.store.ts
interface AuthUser {
  id: string;
  email: string;
}

interface AuthStore {
  user: AuthUser | null;
  setUser: (user: AuthUser) => void;
  clearUser: () => void;
}

// persist to localStorage so page-refresh doesn't lose user identity
// actual session validity is the httpOnly cookie — backend enforces it
// any 401 from API → clearUser() + redirect to /login
```

**No access token stored.** The session cookie is httpOnly and managed entirely by the browser.

### 6.3 TanStack Query Configuration

```ts
// hooks/useProducts.ts

// Dashboard — refetch every 30s (catches price changes from worker)
const useDashboard = () => useQuery({
  queryKey: ['dashboard'],
  queryFn: getProducts,
  refetchInterval: 30_000,
  staleTime: 20_000,
})

// Add product — backend scrapes synchronously, returns full data or error
const useAddProduct = () => useMutation({
  mutationFn: addProduct,
  onSuccess: () => queryClient.invalidateQueries({ queryKey: ['dashboard'] }),
  // No optimistic card needed — result is synchronous (data or error)
})

// Remove product — optimistic removal
const useRemoveProduct = () => useMutation({
  mutationFn: removeProduct,
  onMutate: async (productId) => {
    await queryClient.cancelQueries({ queryKey: ['dashboard'] })
    const previous = queryClient.getQueryData(['dashboard'])
    queryClient.setQueryData(['dashboard'], (old: DashboardResponse) => ({
      ...old,
      products: old.products.filter(p => p.id !== productId)
    }))
    return { previous }
  },
  onError: (_err, _vars, context) => {
    queryClient.setQueryData(['dashboard'], context?.previous)
  },
  onSettled: () => queryClient.invalidateQueries({ queryKey: ['dashboard'] }),
})

// hooks/useNotifications.ts
// Cursor-paginated infinite query
const useInfiniteNotifications = () => useInfiniteQuery({
  queryKey: ['notifications'],
  queryFn: ({ pageParam }) => listNotifications({ cursor: pageParam }),
  getNextPageParam: (last) => last.next_cursor ?? undefined,
  refetchInterval: 60_000,
})

const useReadNotification = () => useMutation({
  mutationFn: readNotification,
  onSuccess: (updated) => {
    // update individual item in cache
    queryClient.setQueryData(['notifications'], (old) => /* update read_at */)
    // also decrement unread count in dashboard cache
    queryClient.invalidateQueries({ queryKey: ['dashboard'] })
  }
})
```

### 6.4 Key Derivations (never stored as state)

```ts
// From dashboard data
const productCount = dashboard.products.length              // plan usage
const isAtLimit = productCount >= MAX_PRODUCTS              // disable add button
const unreadCount = dashboard.unread_notification_count    // bell badge

// From a ProductResponse
const hasPriceDrop = (p: ProductResponse): boolean =>
  p.previous_price !== null &&
  parseFloat(p.current_price) < parseFloat(p.previous_price)

const priceDrop = (p: ProductResponse) => {
  const curr = parseFloat(p.current_price)
  const prev = parseFloat(p.previous_price!)
  return { amount: prev - curr, percent: ((prev - curr) / prev) * 100 }
}

// Notification unread
const isUnread = (n: NotificationResponse): boolean => n.read_at === null
```

---

## 7. TypeScript Interfaces

```ts
// types/auth.types.ts
export interface AuthUser {
  id: string;
  email: string;
}

// types/product.types.ts
export interface ProductResponse {
  id: string;
  url: string;
  product_name: string;
  current_price: string;     // decimal string, parse with parseFloat
  previous_price: string | null;
  last_checked_at: string | null;
  created_at: string;
}

export interface DashboardResponse {
  products: ProductResponse[];
  unread_notification_count: number;
}

// types/notification.types.ts
export interface NotificationResponse {
  id: string;
  tracked_product_id: string;
  old_price: string;
  new_price: string;
  created_at: string;
  read_at: string | null;
}

export interface NotificationListResponse {
  notifications: NotificationResponse[];
  next_cursor: string | null;
}

// types/api.types.ts
export interface ErrorResponse {
  detail: string;
  code: string;
}

export type ApiErrorCode =
  | 'EMAIL_ALREADY_REGISTERED'
  | 'INVALID_CREDENTIALS'
  | 'WEAK_PASSWORD'
  | 'PASSWORD_CHANGE_NOT_ALLOWED'
  | 'INVALID_RESET_TOKEN'
  | 'INVALID_PRODUCT_URL'
  | 'PRODUCT_LIMIT_EXCEEDED'
  | 'DUPLICATE_PRODUCT'
  | 'SCRAPING_FAILED'
  | 'PRODUCT_NOT_FOUND'
  | 'NOTIFICATION_NOT_FOUND'
  | 'VALIDATION_ERROR'
  | 'INTERNAL_ERROR';
```

---

## 8. API Client Design

```ts
// api/client.ts
const client = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL + '/api/v1',
  withCredentials: true,  // CRITICAL: sends the httpOnly session cookie
  headers: { 'Content-Type': 'application/json' },
})

// Response interceptor: 401 → clear auth store, redirect to /login
client.interceptors.response.use(
  response => response,
  (error: AxiosError<ErrorResponse>) => {
    if (error.response?.status === 401) {
      useAuthStore.getState().clearUser()
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)
```

No token refresh needed — the session cookie is managed entirely by the browser.

---

## 9. Routing & Guards

```tsx
// App.tsx
<Routes>
  {/* Public-only: redirect to /dashboard if already authenticated */}
  <Route element={<PublicOnlyRoute />}>
    <Route path="/" element={<LandingPage />} />
    <Route path="/signup" element={<SignUpPage />} />
    <Route path="/login" element={<LoginPage />} />
    <Route path="/forgot-password" element={<ForgotPasswordPage />} />
    <Route path="/reset-password" element={<ResetPasswordPage />} />
  </Route>

  {/* Authenticated: redirect to /login if no user in store */}
  <Route element={<PrivateRoute />}>
    <Route element={<AppShell />}>
      <Route path="/dashboard" element={<DashboardPage />} />
      <Route path="/products/:id" element={<ProductDetailPage />} />
      <Route path="/notifications" element={<NotificationsPage />} />
      <Route path="/settings" element={<SettingsPage />} />
    </Route>
  </Route>

  <Route path="*" element={<Navigate to="/" replace />} />
</Routes>
```

**PrivateRoute:** reads `user` from `auth.store`. If null → redirect to `/login` with `state.from = location`.
**PublicOnlyRoute:** if `user !== null` → redirect to `/dashboard`.
**Google OAuth:** `GET /auth/google/login` is a full browser redirect (not an Axios call); use `window.location.href`.

---

## 10. Screen-by-Screen Design

---

### 10.1 Landing Page

**Purpose:** Convert visitor → sign up.

**Component structure:**
```
LandingPage
├── Hero (headline + subheadline + CTA buttons)
├── HowItWorks (3 steps: Add URL → We watch it → Get notified)
└── Footer (Log in link)
```

**Props interfaces:**
```ts
// No data fetching; fully static
```

**Key UX decisions:**
- Single primary CTA: "Get Started Free" → `/signup`
- Secondary: "Log In" → `/login`
- Google Sign In button → triggers `window.location.href = '/api/v1/auth/google/login'`
- HowItWorks: numbered steps, icon per step, minimal copy

---

### 10.2 Sign Up Page

**API:** `POST /auth/register`

**Component structure:**
```
SignUpPage
└── AuthCard
    └── SignUpForm (React Hook Form + Zod)
        ├── EmailField
        ├── PasswordInput (show/hide toggle)
        ├── ConfirmPasswordInput (show/hide toggle)
        ├── SubmitButton (disabled until valid, loading spinner)
        └── GoogleSignInButton
```

**Zod schema:**
```ts
const signUpSchema = z.object({
  email: z.string().email('Please enter a valid email'),
  password: z.string()
    .min(8, 'At least 8 characters')
    .regex(/[A-Z]/, 'Must contain an uppercase letter')
    .regex(/[0-9]/, 'Must contain a number'),
  confirmPassword: z.string(),
}).refine(d => d.password === d.confirmPassword, {
  message: "Passwords don't match",
  path: ['confirmPassword'],
})
```

**Error mapping:**
| API Error Code | Field / Location | Message |
|----------------|-----------------|---------|
| `EMAIL_ALREADY_REGISTERED` | email field | "An account with this email already exists" + "Log in instead?" link |
| `WEAK_PASSWORD` | password field | "Password is too weak" |
| Network error | toast | "Something went wrong. Please try again." |

**On success:** store user → navigate to `/dashboard` → toast "Welcome to Price Alert!"

**Google:** `window.location.href = '/api/v1/auth/google/login'` — no Axios, full browser redirect.

**Google error handling:** On `/login?error=OIDC_EXCHANGE_FAILED` etc., show inline error banner.

---

### 10.3 Log In Page

**API:** `POST /auth/login`

**Component structure:**
```
LoginPage
└── AuthCard
    └── LoginForm
        ├── EmailField
        ├── PasswordInput (show/hide)
        ├── ForgotPasswordLink
        ├── SubmitButton
        └── GoogleSignInButton
```

**Error mapping:**
| API Error Code | Location | Message |
|----------------|----------|---------|
| `INVALID_CREDENTIALS` | form-level (not field-level) | "Incorrect email or password" |

**On success:** store user → navigate to `location.state.from ?? '/dashboard'`

---

### 10.4 Forgot Password Page

**API:** `POST /auth/password-reset`

**Behaviour:** Always shows success message regardless of whether email exists.
No loading state after submit on the response — show "If an account exists for that email, a reset link is on its way."

---

### 10.5 Reset Password Page

**API:** `POST /auth/password-reset/confirm`

**On load:** Read `?token=` query param. If absent → show error + link to `/forgot-password`.

**Zod schema:**
```ts
const resetPasswordSchema = z.object({
  new_password: z.string().min(8, 'At least 8 characters'),
  confirm_password: z.string(),
}).refine(...)
```

**Error mapping:**
| API Error Code | Location | Message |
|----------------|----------|---------|
| `INVALID_RESET_TOKEN` | form-level banner | "This link has expired or already been used." + "Request a new one" link |

**On success:** navigate to `/login` → toast "Password updated. Please log in."

---

### 10.6 Dashboard Page

**API:** `GET /products` (refetch every 30s)

**Component structure:**
```
DashboardPage
├── PageHeader ("Your Tracked Products")
├── PlanUsageBar (derived from products.length, MAX_PRODUCTS=5)
├── AddProductButton (disabled at limit, tooltip if disabled)
│
├── [if loading]  → ProductGrid with 3 SkeletonCards
├── [if empty]    → EmptyProducts
├── [if data]     → ProductGrid
│   └── ProductCard[] (Active or PriceDropped or ScrapeFailed)
│
└── AddProductPanel (Sheet; open/close controlled by useState)
```

**ProductCard States:**

| State | Condition | Visual |
|-------|-----------|--------|
| Active | `current_price` set, no drop | Standard card |
| PriceDropped | `hasPriceDrop(product) === true` | Green left border + drop pill |
| ScrapeFailed | `current_price === "0" or null` (backend always sets price) | N/A — backend errors synchronously |

> **Note:** Because `POST /products` is synchronous, there is no "pending/checking price" state.
> If scraping fails, the API returns `SCRAPING_FAILED` (422) and no product is created.
> All products in the dashboard already have a `current_price`.

**PlanUsageBar colour states:**
- `< 4/5`: blue progress bar
- `4/5`: amber bar + "1 slot remaining"
- `5/5`: red bar + "Add Product" button disabled with tooltip "Upgrade to track more products"

**Remove flow:**
1. Click remove icon → `ConfirmDialog`
2. On confirm → `DELETE /products/{id}` → optimistic removal from cache → undo toast (5s)
3. Undo: re-add via `POST /products` with same URL (re-scrapes; show loading state on undo button)

---

### 10.7 Add Product Panel

**API:** `POST /products`

**Responsive:** Right-side Sheet (desktop ≥1024px) vs bottom Sheet (mobile <640px).

**Zod schema:**
```ts
const addProductSchema = z.object({
  url: z.string().url('Please enter a valid URL').startsWith('https://', 'URL must start with https://'),
})
```

**Submit flow:**
1. Submit button → spinner
2. On `201` success: panel closes, `queryClient.invalidateQueries(['dashboard'])`
3. On error: panel stays open, inline error shown

**Error mapping:**
| API Error Code | Location | Message |
|----------------|----------|---------|
| `PRODUCT_LIMIT_EXCEEDED` | form banner | "You've reached your 5-product limit. Upgrade to track more." |
| `DUPLICATE_PRODUCT` | url field | "You're already tracking this product." |
| `INVALID_PRODUCT_URL` | url field | "This URL doesn't appear to be a valid product page." |
| `SCRAPING_FAILED` | url field | "We couldn't fetch the price for this product. Check the URL and try again." |

**Auto-focus:** URL input auto-focused on panel open.
**Clipboard paste detection:** On panel open, check `navigator.clipboard.readText()` → if valid URL, pre-fill field.

---

### 10.8 Product Detail Page

**Route:** `/products/:id`

**API:** No extra call — reads from `queryClient.getQueryData(['dashboard'])`.

```ts
// ProductDetailPage.tsx
const { id } = useParams()
const { data: dashboard } = useDashboard()
const product = dashboard?.products.find(p => p.id === id)

// If product not found in cache → navigate back to dashboard
useEffect(() => {
  if (dashboard && !product) navigate('/dashboard', { replace: true })
}, [dashboard, product])
```

**Content:**
- Product name (H1)
- URL (clickable, `target="_blank"`)
- Current price (large, bold)
- Previous price (smaller, strikethrough if higher)
- Price drop amount + % (if applicable, green pill)
- Last checked: relative time
- Remove button → ConfirmDialog → navigate to `/dashboard` on confirm

**No "Next check scheduled" field** — not in API response.

---

### 10.9 Notifications Page

**API:** `GET /notifications?cursor=&limit=20`, `PATCH /notifications/{id}/read`

**Component structure:**
```
NotificationsPage
├── PageHeader ("Price Drops") + unread count badge
│
├── [if loading]  → SkeletonList (5 items)
├── [if empty]    → EmptyNotifications
├── [if data]     → NotificationList
│   └── NotificationItem[] (unread: accent border, read: muted)
│       └── onClick → readNotification(id) → navigate to /products/:tracked_product_id
│
└── LoadMoreButton (if next_cursor exists)
```

**Individual read on click:** When user clicks a notification, `PATCH /notifications/{id}/read` is called, then navigate to `/products/{tracked_product_id}`.

**No "Mark all as read"** — backend only supports individual dismissal.

**NotificationItem content:**
- Product name (looked up from dashboard cache by `tracked_product_id`)
- `old_price → new_price` with drop amount
- Relative time ("2 hours ago")
- Unread indicator: `read_at === null` → subtle left border accent + bold text

---

### 10.10 Settings Page

**API:** `PUT /auth/password`

**Content:** Change password only (no account deletion, no plan info endpoint).

**Component structure:**
```
SettingsPage
├── SectionHeader ("Account")
├── EmailDisplay (read-only, current user email from auth store)
├── ChangePasswordForm
│   ├── CurrentPasswordInput (show/hide)
│   ├── NewPasswordInput (show/hide)
│   ├── ConfirmNewPasswordInput (show/hide)
│   └── SubmitButton
│
└── SectionHeader ("Plan") — read-only display
    ├── "Free Plan" label
    ├── ProductUsageDisplay (derived from dashboard cache)
    └── "Coming soon: paid plans"
```

**Error mapping:**
| API Error Code | Location | Message |
|----------------|----------|---------|
| `PASSWORD_CHANGE_NOT_ALLOWED` | form banner | "Your account uses Google Sign-In. Password change is not available." |
| `INVALID_CREDENTIALS` (wrong current pw) | current_password field | "Incorrect current password." |

**On success:** toast "Password updated" + form fields cleared.

---

## 11. Data Flow

```
[Browser] ──httpOnly cookie──► [Backend /api/v1]
                                      │
           ┌──────────────────────────┤
           │                          │
    GET /products              POST /products
           │                          │
           ▼                          ▼
  TanStack Query cache         Mutation → invalidate
  (stale: 20s, refetch: 30s)   ['dashboard'] query
           │
    ┌──────┴────────┐
    ▼               ▼
 DashboardPage  ProductDetailPage
 (ProductGrid)  (reads from cache)
    │
    ▼
 ProductCard (derives: hasPriceDrop, priceDrop %)
 PlanUsageBar (derives: count/MAX_PRODUCTS)
 TopNav bell (uses: unread_notification_count)
```

---

## 12. Error Boundary Placement

```
App.tsx
└── ErrorBoundary (top-level: catches unexpected errors)
    ├── PublicOnlyRoute
    └── PrivateRoute
        └── AppShell
            ├── ErrorBoundary (route-level: per page)
            │   └── DashboardPage
            ├── ErrorBoundary
            │   └── NotificationsPage
            └── ErrorBoundary
                └── SettingsPage
```

**Fallback UI:** "Something went wrong. Try refreshing the page." + Retry button.

---

## 13. Accessibility Requirements

| Component | Requirements |
|-----------|-------------|
| All form inputs | `<label>` with `htmlFor`, `aria-describedby` for errors |
| AddProductPanel | Focus trap, `aria-modal`, auto-focus URL input on open |
| ConfirmDialog | Focus trap, Escape closes, focus returns to trigger |
| NotificationBell | `aria-label="Notifications"`, `aria-label="X unread"` on badge |
| ProductCard remove | `aria-label="Stop tracking {product_name}"` |
| PlanUsageBar | `role="progressbar"`, `aria-valuenow`, `aria-valuemax` |
| PasswordInput toggle | `aria-label="Show/hide password"` |
| SkeletonCard | `aria-hidden="true"` + `aria-busy="true"` on parent |
| Toast notifications | `aria-live="polite"`, do not steal focus |
| Colour indicators | Never colour-only: price drop uses icon + colour + text |
| Touch targets | Min 44×44px on all interactive elements |

---

## 14. Responsive Behaviour

| Breakpoint | Changes |
|------------|---------|
| Mobile `< 640px` | Single-column grid, BottomNav, AddProduct as full-height bottom sheet |
| Tablet `640–1024px` | Two-column grid, BottomNav, AddProduct as bottom sheet |
| Desktop `≥ 1024px` | Three-column grid, SideNav replaces BottomNav, AddProduct as right slide-in panel |

**ProductGrid:**
```
Mobile:  grid-cols-1
Tablet:  grid-cols-2  (sm:grid-cols-2)
Desktop: grid-cols-3  (lg:grid-cols-3)
```

---

## 15. Loading & Empty State Plan

| Screen | Loading | Empty |
|--------|---------|-------|
| Dashboard | `grid-cols-1/2/3` of SkeletonCards | Illustration + "Add your first product" CTA |
| Notifications | SkeletonList (5 rows) | "No price drops yet. We're watching for you." |
| Product Detail | Redirects to dashboard (no data = product gone) | N/A |
| Settings | None (form renders immediately from auth store) | N/A |

Skeleton screens use `animate-pulse` background shimmer. Never show blank white for > 300ms.

---

## 16. MVP vs Phase 2 Scope

| Feature | MVP (build now) | Phase 2 |
|---------|----------------|---------|
| All 10 screens | ✅ | — |
| Cookie-based auth (email + Google) | ✅ | — |
| Responsive (mobile + desktop) | ✅ | — |
| Optimistic UI on remove | ✅ | — |
| 30s polling for price updates | ✅ | — |
| Skeleton loading states | ✅ | — |
| Toast notifications (Sonner) | ✅ | — |
| Individual notification dismiss | ✅ | — |
| Product Detail (from cache) | ✅ | — |
| Mark all as read | ❌ (no backend endpoint) | ✅ |
| Price history chart | ❌ | ✅ |
| Upgrade / Plans page (live data) | ❌ | ✅ |
| Price threshold per product | ❌ | ✅ |
| Real-time updates (SSE) | ❌ | ✅ |
| Dark mode | ❌ | ✅ |
| PWA / installable | ❌ | ✅ |