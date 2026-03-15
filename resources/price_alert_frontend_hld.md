# Price Alert — Frontend High Level Design

---

## 1. Tech Stack

| Layer | Choice | Rationale |
|---|---|---|
| Framework | React 18 + TypeScript | Component model, ecosystem, type safety |
| Build Tool | Vite | Fast HMR, small bundles, first-class TS support |
| Routing | React Router v6 | Declarative, nested routes, route guards |
| State Management | Zustand | Lightweight, no boilerplate, easy async slices |
| Server State | TanStack Query (React Query) | Caching, background refetch, loading/error states out of the box |
| Styling | Tailwind CSS | Utility-first, responsive breakpoints built-in, no CSS files |
| Component Library | shadcn/ui (on top of Tailwind) | Accessible, unstyled primitives, fully customisable |
| Forms | React Hook Form + Zod | Schema-driven validation, minimal re-renders |
| HTTP Client | Axios | Interceptors for token refresh, consistent error shape |
| Notifications (toast) | Sonner | Beautiful, lightweight, stacks correctly |
| Icons | Lucide React | Clean, consistent, tree-shakeable |
| Animation | Framer Motion | Page transitions, card animations, micro-interactions |
| Date formatting | date-fns | Lightweight, tree-shakeable |

---

## 2. Project Structure

```
src/
├── main.tsx                    # App entry point
├── App.tsx                     # Router setup, providers
├── config/
│   └── plans.ts                # Plan limits (mirrors backend plans.py)
├── api/
│   ├── client.ts               # Axios instance + interceptors
│   ├── auth.api.ts             # Auth endpoints
│   ├── products.api.ts         # Products endpoints
│   └── notifications.api.ts   # Notifications endpoints
├── store/
│   ├── auth.store.ts           # Zustand: user, tokens, login/logout
│   └── ui.store.ts             # Zustand: global UI state (modals, panels)
├── hooks/
│   ├── useAuth.ts              # Auth state + helpers
│   ├── useProducts.ts          # TanStack Query wrappers for products
│   └── useNotifications.ts    # TanStack Query wrappers for notifications
├── components/
│   ├── ui/                     # shadcn/ui primitives (Button, Input, Dialog…)
│   ├── layout/
│   │   ├── AppShell.tsx        # Authenticated layout (nav + content area)
│   │   ├── TopNav.tsx          # Logo, bell, avatar menu
│   │   ├── SideNav.tsx         # Desktop sidebar navigation
│   │   └── BottomNav.tsx       # Mobile bottom navigation bar
│   ├── auth/
│   │   ├── AuthCard.tsx        # Shared card wrapper for auth pages
│   │   └── PasswordInput.tsx   # Input with show/hide toggle
│   ├── products/
│   │   ├── ProductCard.tsx     # Product card with all states
│   │   ├── ProductGrid.tsx     # Responsive grid of ProductCards
│   │   ├── AddProductPanel.tsx # Slide-in / bottom sheet for adding URL
│   │   ├── PlanUsageBar.tsx    # "X of 5 URLs used" bar
│   │   └── EmptyProducts.tsx   # Empty state illustration + CTA
│   ├── notifications/
│   │   ├── NotificationItem.tsx
│   │   ├── NotificationBell.tsx # Bell icon + unread badge
│   │   └── EmptyNotifications.tsx
│   └── shared/
│       ├── SkeletonCard.tsx    # Loading skeleton for product cards
│       ├── SkeletonList.tsx    # Loading skeleton for lists
│       ├── ErrorBoundary.tsx
│       └── ConfirmDialog.tsx   # Reusable confirmation modal
├── pages/
│   ├── LandingPage.tsx
│   ├── SignUpPage.tsx
│   ├── LoginPage.tsx
│   ├── ForgotPasswordPage.tsx
│   ├── ResetPasswordPage.tsx
│   ├── DashboardPage.tsx
│   ├── ProductDetailPage.tsx
│   ├── NotificationsPage.tsx
│   ├── SettingsPage.tsx
│   └── UpgradePage.tsx
├── types/
│   ├── auth.types.ts
│   ├── product.types.ts
│   └── notification.types.ts
└── utils/
    ├── formatPrice.ts
    ├── formatDate.ts
    └── cn.ts                   # Tailwind class merge utility
```

---

## 3. Routing & Route Guards

```tsx
// App.tsx
<Routes>
  {/* Public routes */}
  <Route element={<PublicOnlyRoute />}>
    <Route path="/" element={<LandingPage />} />
    <Route path="/signup" element={<SignUpPage />} />
    <Route path="/login" element={<LoginPage />} />
    <Route path="/forgot-password" element={<ForgotPasswordPage />} />
    <Route path="/reset-password" element={<ResetPasswordPage />} />
  </Route>

  {/* Authenticated routes — wrapped in AppShell */}
  <Route element={<PrivateRoute />}>
    <Route element={<AppShell />}>
      <Route path="/dashboard" element={<DashboardPage />} />
      <Route path="/products/:id" element={<ProductDetailPage />} />
      <Route path="/notifications" element={<NotificationsPage />} />
      <Route path="/settings" element={<SettingsPage />} />
      <Route path="/upgrade" element={<UpgradePage />} />
    </Route>
  </Route>

  <Route path="*" element={<Navigate to="/" />} />
</Routes>
```

**PrivateRoute** — reads auth token from Zustand store. If absent, redirects to `/login` and stores the intended path in location state so the user is sent back after login.

**PublicOnlyRoute** — if user is already authenticated, redirects to `/dashboard`.

---

## 4. Authentication & Token Management

### Token Storage
- **Access token**: stored in Zustand memory (never in localStorage)
- **Refresh token**: `httpOnly` cookie (set by API, invisible to JS)

### Axios Interceptor — Auto Token Refresh
```
Request interceptor: attach Authorization: Bearer <accessToken> header

Response interceptor:
  On 401 response:
    → call POST /auth/refresh (cookie is sent automatically)
    → on success: update access token in Zustand, retry original request
    → on failure (refresh expired): clear store, redirect to /login
```

This means token expiry is completely invisible to the user — they never get logged out mid-session unless the refresh token itself has expired (30 days).

### Auth Store (Zustand)
```ts
interface AuthStore {
  user: User | null          // id, email, plan, plan_limits
  accessToken: string | null
  isAuthenticated: boolean
  login: (email, password) => Promise<void>
  logout: () => void
  setTokens: (accessToken) => void
}
```

---

## 5. Design System

### Color Palette

| Token | Value | Usage |
|---|---|---|
| `primary` | #2563EB (blue-600) | CTA buttons, links, active states |
| `primary-hover` | #1D4ED8 (blue-700) | Button hover |
| `success` | #16A34A (green-600) | Price drop indicators, success states |
| `warning` | #D97706 (amber-600) | Plan limit warnings, scrape failures |
| `danger` | #DC2626 (red-600) | Errors, destructive actions |
| `surface` | #F8FAFC (slate-50) | Page background |
| `card` | #FFFFFF | Card backgrounds |
| `border` | #E2E8F0 (slate-200) | Card borders, dividers |
| `text-primary` | #0F172A (slate-900) | Headings, primary text |
| `text-secondary` | #64748B (slate-500) | Labels, metadata, secondary text |
| `text-muted` | #94A3B8 (slate-400) | Placeholders, disabled |

### Typography

| Role | Size | Weight | Usage |
|---|---|---|---|
| Display | 2.25rem / 36px | 700 | Landing headline |
| H1 | 1.875rem / 30px | 700 | Page titles |
| H2 | 1.5rem / 24px | 600 | Section headers |
| H3 | 1.125rem / 18px | 600 | Card titles, product names |
| Body | 1rem / 16px | 400 | Default text |
| Small | 0.875rem / 14px | 400 | Labels, metadata |
| XSmall | 0.75rem / 12px | 400 | Timestamps, badges |

Font: **Inter** (Google Fonts) — friendly, highly legible, widely available.

### Spacing Scale
Based on 4px base unit (Tailwind default). Key values:
- Component padding: 16px (p-4)
- Card padding: 20px (p-5)
- Section gaps: 24px (gap-6)
- Page padding: 24px mobile, 32px desktop

### Border Radius
- Cards: `rounded-xl` (12px)
- Buttons: `rounded-lg` (8px)
- Inputs: `rounded-lg` (8px)
- Badges: `rounded-full`

### Shadows
- Cards: `shadow-sm` (subtle lift)
- Modals/panels: `shadow-xl`
- Dropdowns: `shadow-lg`

---

## 6. Component Specifications

---

### ProductCard

The most important component. Four distinct states:

```
┌─────────────────────────────────────────┐
│  [Product Image or Favicon]             │
│  Nike Air Max 90          [Remove icon] │
│  amazon.com/dp/...                      │
│                                         │
│  Current Price    Previous Price        │
│  $89.99           ~~$109.99~~           │
│                                         │
│  ↓ $20.00 saved (18% off)  [green pill] │
│                                         │
│  Last checked: 2 hours ago              │
└─────────────────────────────────────────┘
```

**State: Loading (newly added)**
- Favicon placeholder (grey circle)
- URL shown in text-muted
- Price area: animated shimmer skeleton
- "Checking price..." label

**State: Active (normal)**
- Product name as H3
- Current price: large, text-primary, bold
- Previous price: smaller, text-muted, strikethrough
- Last checked: text-muted, relative time ("2 hours ago")

**State: Price Dropped (new drop)**
- Left border: 3px solid success green
- Drop pill: "↓ $20.00 (18% off)" with green background
- Card has subtle green tint on background
- Animated on first appearance (slide-in from left)

**State: Scrape Failed**
- Warning icon (amber)
- "Couldn't fetch price" in text-warning
- "Retry" text button

**Interactions:**
- Hover: slight shadow lift (`shadow-md`), cursor pointer
- Click → navigate to Product Detail
- Remove icon: visible on hover (desktop), always visible (mobile)
- Remove click → ConfirmDialog → on confirm: card animates out, undo toast appears for 5s

---

### PlanUsageBar

```
Tracked Products    3 of 5 used
[████████░░░░░░░░]  60%
```

- Below 60%: bar colour = primary blue
- At 80% (4/5): bar colour = amber, text "1 slot remaining — upgrade for more"
- At 100% (5/5): bar colour = red, "Add Product" button disabled with tooltip

---

### AddProductPanel

**Desktop:** Right-side slide-in panel (400px wide), overlays dashboard with a semi-transparent backdrop.

**Mobile:** Bottom sheet that slides up from the bottom edge, with a drag handle at the top.

```
┌─────────────────────────────────────────┐
│  ✕   Track a new product                │
├─────────────────────────────────────────┤
│                                         │
│  Paste the product URL                  │
│  ┌─────────────────────────────────────┐│
│  │ https://...                         ││
│  └─────────────────────────────────────┘│
│                                         │
│  Works with Amazon, eBay, any shop ✓    │
│                                         │
│  [    Track This Product    ]           │
│                                         │
└─────────────────────────────────────────┘
```

- URL field is auto-focused when panel opens
- Paste detection: if clipboard contains a URL, auto-fills the field
- Inline validation on blur
- Submit button shows spinner while API call is in flight
- On success: panel closes, new card animates into the grid

---

### NotificationBell

- Bell icon in top nav
- Red badge with count appears when unread > 0
- Badge shows "9+" for counts above 9
- Click → navigates to /notifications
- Badge disappears after visiting /notifications (all marked as read via API)

---

### AppShell (Layout)

**Desktop (> 1024px):**
```
┌──────────┬──────────────────────────────────────────┐
│          │  TopNav                                   │
│ SideNav  ├──────────────────────────────────────────┤
│          │                                           │
│ Dashboard│  Page Content (Outlet)                   │
│ Notifs   │                                           │
│ Settings │                                           │
│          │                                           │
│ [Plan    │                                           │
│  badge]  │                                           │
└──────────┴──────────────────────────────────────────┘
```

**Mobile (< 640px):**
```
┌──────────────────────────────────────────┐
│  TopNav (logo + bell + avatar)           │
├──────────────────────────────────────────┤
│                                          │
│  Page Content (Outlet)                   │
│                                          │
│                                          │
│                                          │
│                                          │
├──────────────────────────────────────────┤
│  BottomNav  [🏠] [🔔] [⚙️]              │
└──────────────────────────────────────────┘
```

**SideNav items:**
- Dashboard (home icon)
- Notifications (bell icon + unread badge)
- Settings (gear icon)
- Plan badge at bottom: "Free Plan · 3/5 used" → links to /upgrade

---

## 7. Page-by-Page Flow Details

---

### Landing Page Flow

```
User lands on /
    │
    ├── Hero section: headline + "Get Started Free" CTA
    │
    ├── How it works: 3 steps (Add URL → We watch it → Get notified)
    │
    └── Footer: "Already have an account? Log in"
```

---

### Sign Up Flow

```
User fills email + password + confirm password
    │
    ├── Inline validation fires on blur per field
    │
    ├── On submit → POST /auth/register
    │       │
    │       ├── Success → store tokens → redirect /dashboard
    │       │            → toast "Welcome to Price Alert! 🎉"
    │       │
    │       └── Error (email taken) → inline error on email field
    │                                  "An account with this email already exists"
    │                                  + "Log in instead?" link
```

---

### Login Flow

```
User fills email + password
    │
    ├── On submit → POST /auth/login
    │       │
    │       ├── Success → store token → redirect /dashboard (or intended URL)
    │       │
    │       └── Error → "Incorrect email or password" (field-level agnostic)
    │
    └── "Forgot password?" → /forgot-password
```

---

### Add Product Flow

```
User clicks "Add Product"
    │
    ├── Panel/sheet opens, URL field auto-focused
    │
    ├── User pastes URL
    │       │
    │       ├── URL valid → submit enabled
    │       └── URL invalid → inline "Please enter a valid product URL (https://...)"
    │
    ├── On submit → POST /products
    │       │
    │       ├── 201 Success:
    │       │     → panel closes
    │       │     → new card inserted at top of grid with "Checking price..." state
    │       │     → background: Celery job scrapes price
    │       │     → card auto-updates when price is available (polling or SSE)
    │       │
    │       ├── 403 PLAN_LIMIT_REACHED:
    │       │     → panel stays open
    │       │     → inline banner: "You've reached your 5-URL limit."
    │       │                       "Upgrade to track more products" [button]
    │       │
    │       └── 409 Duplicate URL:
    │             → inline error: "You're already tracking this product"
```

---

### Price Drop Notification Flow

```
(Background) Celery detects price drop
    │
    ├── API: notification row inserted + email sent
    │
    ├── Frontend: next time user opens app or dashboard refreshes
    │       │
    │       ├── Bell badge updates with new count
    │       ├── Affected product card gets green "price dropped" state
    │       └── If user is actively on dashboard: toast appears
    │           "📉 Nike Air Max dropped from $109 to $89!"
    │
    └── User clicks bell → /notifications
            │
            ├── Sees list of all price drops
            ├── Unread items highlighted
            ├── Clicks item → Product Detail page
            └── "Mark all as read" → clears badge
```

---

### Remove Product Flow

```
User clicks remove icon on card
    │
    ├── ConfirmDialog appears:
    │   "Stop tracking Nike Air Max 90?
    │    You won't receive any more price alerts for this product."
    │   [Cancel]  [Stop Tracking]
    │
    ├── On confirm → DELETE /products/:id
    │       │
    │       ├── Card animates out (fade + slide up)
    │       ├── Toast appears: "Stopped tracking Nike Air Max 90"
    │       │                   [Undo] button visible for 5 seconds
    │       │
    │       └── On "Undo" click within 5s:
    │             → POST /products (re-add same URL)
    │             → card re-appears with previous state
    │
    └── Plan usage bar updates immediately (optimistic)
```

---

### Settings Flow

```
User opens /settings
    │
    ├── Change Password section
    │     ├── Fields: Current password, New password, Confirm new password
    │     ├── Submit → PATCH /me/password
    │     └── Success → toast "Password updated" + fields cleared
    │
    └── Plan section
          ├── Shows: "Free Plan · 3 of 5 URLs used"
          └── "View Plans" → /upgrade
```

---

## 8. Server State Strategy (TanStack Query)

```ts
// hooks/useProducts.ts

// Fetch all products — refetches every 30s (catches price updates)
useQuery({ queryKey: ['products'], queryFn: fetchProducts, refetchInterval: 30_000 })

// Add product — optimistic update
useMutation({
  mutationFn: addProduct,
  onMutate: (newUrl) => {
    // Insert optimistic card with loading state immediately
    queryClient.setQueryData(['products'], (old) => [optimisticCard, ...old])
  },
  onSuccess: (serverProduct) => {
    // Replace optimistic card with real data
    queryClient.invalidateQueries({ queryKey: ['products'] })
  },
  onError: () => {
    // Roll back optimistic card
    queryClient.invalidateQueries({ queryKey: ['products'] })
  }
})

// Remove product — optimistic removal
useMutation({
  mutationFn: removeProduct,
  onMutate: (id) => {
    // Remove card immediately from cache
  },
  onError: () => {
    // Re-add card if API call fails
    queryClient.invalidateQueries({ queryKey: ['products'] })
  }
})
```

**Key decisions:**
- `refetchInterval: 30_000` on the products list catches price updates from the worker without needing WebSockets in MVP
- Optimistic updates on add/remove make the UI feel instant
- Notifications refetch every 60 seconds (less urgent than price data)

---

## 9. Form Validation (React Hook Form + Zod)

```ts
// schemas/auth.schema.ts
const signUpSchema = z.object({
  email: z.string().email("Please enter a valid email address"),
  password: z.string()
    .min(8, "Password must be at least 8 characters")
    .regex(/[A-Z]/, "Must contain at least one uppercase letter")
    .regex(/[0-9]/, "Must contain at least one number"),
  confirmPassword: z.string()
}).refine(data => data.password === data.confirmPassword, {
  message: "Passwords don't match",
  path: ["confirmPassword"]
})

// schemas/product.schema.ts
const addProductSchema = z.object({
  url: z.string()
    .url("Please enter a valid URL")
    .startsWith("https://", "URL must start with https://")
})
```

All validation schemas live in `/schemas`. They are the single source of truth for field rules — used by both the form and displayed inline without a page reload.

---

## 10. Responsive Breakpoints

| Breakpoint | px | Layout changes |
|---|---|---|
| `sm` | 640px | Panel → full screen modal |
| `md` | 768px | 2-column product grid |
| `lg` | 1024px | Side nav appears, bottom nav hides, 3-column grid |
| `xl` | 1280px | Content max-width cap (1200px), centred |

### Product Grid
```
Mobile:  1 column  (full width cards)
Tablet:  2 columns
Desktop: 3 columns
XL:      3 columns (max-width capped, not 4 — cards get too wide)
```

---

## 11. Micro-Interactions & Animation

All animations use Framer Motion. They should be subtle — fast enough to not get in the way.

| Interaction | Animation | Duration |
|---|---|---|
| Page transition | Fade in (opacity 0→1) | 150ms |
| Product card enter | Slide up + fade (y: 20→0, opacity 0→1) | 200ms |
| Product card remove | Slide up + fade out | 200ms |
| Panel slide-in (desktop) | Slide from right (x: 100%→0) | 250ms |
| Bottom sheet (mobile) | Slide from bottom (y: 100%→0) | 300ms |
| Price dropped highlight | Pulse green glow once | 600ms |
| Toast enter | Slide from top-right | 200ms |
| Skeleton shimmer | Continuous left-right shine | 1.5s loop |

---

## 12. Error States

| Error | Where | Message |
|---|---|---|
| Network offline | Global toast | "You're offline. Changes will retry when reconnected." |
| API 500 | Inline on affected section | "Something went wrong. Please try again." + Retry button |
| Product not found (404) | Product Detail | "This product doesn't exist or was removed." + Back to Dashboard |
| Session expired | Global redirect | Redirect to /login + toast "Your session expired. Please log in again." |
| Rate limited (429) | Form submit | "Too many attempts. Please wait a moment and try again." |

---

## 13. Environment Variables

```bash
VITE_API_BASE_URL=http://localhost:8000
VITE_APP_NAME=Price Alert
VITE_SUPPORT_EMAIL=support@pricealert.com
```

---

## 14. MVP vs Phase 2

| Feature | MVP | Phase 2 |
|---|---|---|
| All 11 screens built | ✅ | — |
| Responsive (mobile + desktop) | ✅ | — |
| Optimistic UI on add/remove | ✅ | — |
| 30s polling for price updates | ✅ | — |
| Skeleton loading states | ✅ | — |
| Toast notifications | ✅ | — |
| Upgrade page (waitlist CTA) | ✅ | — |
| Real-time updates (SSE/WebSocket) | ❌ | ✅ |
| Price history chart on Product Detail | ❌ | ✅ |
| Price threshold input per product | ❌ | ✅ |
| Stripe Checkout / billing UI | ❌ | ✅ |
| Dark mode | ❌ | ✅ |
| PWA / installable | ❌ | ✅ |
