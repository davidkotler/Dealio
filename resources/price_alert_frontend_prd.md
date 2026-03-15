# Price Alert — Frontend Product Requirements Document

---

## Vision

A clean, focused web app that feels effortless to use. The user should be able to add a product, see its price, and trust that they'll be notified when it drops — all without friction or confusion. The design language should feel modern and trustworthy, like a tool that quietly works in the background for you.

---

## Design Philosophy

**Calm over loud.** No aggressive upsells, no overwhelming dashboards. The interface should surface only what matters right now.

**Progress over perfection.** When a product is added and scraping hasn't completed yet, show it immediately with a "checking price..." state rather than blocking the user.

**Generous feedback.** Every action (adding, removing, error) gets a clear, human-readable response. Never leave the user wondering if something worked.

**Mobile-first, desktop-polished.** The majority of users checking prices are on their phones. Design for small screens first, then enhance for desktop.

---

## Target Experience

| Scenario | Expected Feel |
|---|---|
| First-time user lands on the app | Understands the product in under 5 seconds |
| User adds their first product | Feels instant; product appears immediately |
| User sees a price drop notification | Clear, satisfying, actionable |
| User hits the 5-product limit | Informed, not blocked or punished |
| User on mobile | Full functionality, no compromises |

---

## Screen Inventory

### Public Screens (unauthenticated)
1. **Landing Page** — App value proposition + CTA to sign up or log in
2. **Sign Up** — Email + password registration
3. **Log In** — Email + password login
4. **Forgot Password** — Email input to request reset
5. **Reset Password** — New password form (via token link from email)

### Authenticated Screens
6. **Dashboard** — Main screen; list of tracked products
7. **Add Product** — Modal or slide-in panel to add a new URL
8. **Product Detail** — Expanded view of a single tracked product
9. **Notifications** — Full list of price drop alerts
10. **Settings** — Account management (password, support)
11. **Upgrade / Plans** — Plan info + waitlist CTA (MVP) or Stripe checkout (Phase 2)

---

## Screen-by-Screen Requirements

---

### 1. Landing Page

**Purpose:** Convert a visitor into a sign-up.

**Must have:**
- Clear one-line headline: what the app does and why it matters
- A short visual showing how it works (3-step process)
- Primary CTA: "Get Started Free"
- Secondary CTA: "Log In"
- No login required to see this page

**Feel:** Clean, minimal, confident. Not a SaaS marketing sprawl — closer to a focused product page.

---

### 2. Sign Up

**Fields:** Email, Password, Confirm Password

**Behaviour:**
- Inline validation as the user types (not only on submit)
- Password strength indicator
- Submit button disabled until form is valid
- On success → redirect to Dashboard with a welcome toast
- On email already in use → inline error on the email field (not a page-level error)
- Show/hide password toggle on both password fields

---

### 3. Log In

**Fields:** Email, Password

**Behaviour:**
- "Forgot password?" link below password field
- On success → redirect to Dashboard
- On wrong credentials → single non-specific message ("Incorrect email or password") — never reveal which field is wrong
- Show/hide password toggle

---

### 4. Forgot Password

**Fields:** Email

**Behaviour:**
- On submit → always show success message regardless of whether email exists (security: don't reveal if an account exists)
- Message: "If an account exists for that email, a reset link is on its way."

---

### 5. Reset Password

**Fields:** New Password, Confirm Password

**Behaviour:**
- Token from URL validated on page load. If invalid/expired → show error with link back to Forgot Password
- On success → redirect to Log In with success toast "Password updated. Please log in."

---

### 6. Dashboard

**Purpose:** The core screen. Users spend most of their time here.

**Layout:**
- Top navigation bar: logo, notification bell (with unread badge), user avatar/menu
- Page header: "Your Tracked Products" + plan usage bar (e.g. "3 of 5 URLs used")
- Product grid/list (see Product Card below)
- Prominent "Add Product" button (always visible)
- Empty state when no products are tracked

**Product Card — States:**
- **Loading** (just added, price not yet scraped): product URL shown, shimmer on price fields, "Checking price..." label
- **Active** (price available): product name, current price (large), previous price (smaller, strikethrough if higher), last checked time, green badge if price recently dropped
- **Price Dropped** (new drop detected): card has a subtle green highlight, drop amount shown prominently (e.g. "↓ $12.00 (15% off)")
- **Scrape Failed** (price couldn't be fetched): amber warning icon, "Couldn't fetch price" with a retry button
- **Removed** (soft delete in progress): card fades out with undo option for 5 seconds before final deletion

**Plan Usage Bar:**
- Shows "X of 5 URLs used" with a visual fill bar
- At 4/5: bar turns amber, subtle nudge "1 slot remaining"
- At 5/5: bar turns red, "Add Product" button disabled with tooltip "Upgrade to track more products"

**Empty State:**
- Illustration + friendly copy: "You're not tracking anything yet. Add your first product and we'll watch the price for you."
- Large "Add Product" CTA

---

### 7. Add Product (Modal / Slide-in Panel)

**Trigger:** "Add Product" button on Dashboard

**Fields:** Product URL (single input, full width)

**Behaviour:**
- URL validated on blur: must be a valid URL (https required)
- On submit → modal closes, product card appears immediately in Dashboard with "Checking price..." state
- If at plan limit → button is disabled before modal opens; tooltip explains why
- Loading state on submit button while API call is in flight
- Error handling: if URL is a duplicate → "You're already tracking this product"

**UX Decision:** Slide-in panel (not a full modal) on desktop so the user can still see their dashboard behind it. Full screen on mobile.

---

### 8. Product Detail

**Trigger:** Clicking a product card on Dashboard

**Content:**
- Product name + URL (clickable, opens original product page in new tab)
- Current price (large, prominent)
- Previous price
- Price drop amount and percentage (if applicable)
- Last checked timestamp
- Next check scheduled time
- Remove button (with confirmation)
- Link back to Dashboard

**MVP:** Simple page layout. Phase 2: price history chart added here.

---

### 9. Notifications

**Trigger:** Bell icon in nav, or notification badge

**Layout:**
- List of price drop alerts, newest first
- Each item: product name, old price → new price, drop amount, time ago
- "Mark all as read" button at the top
- Clicking a notification → opens Product Detail
- Unread notifications have a subtle left border accent or dot indicator
- Empty state: "No price drops yet. We're watching for you."

**Badge behaviour:** Bell icon shows count of unread notifications. Disappears when all are read.

---

### 10. Settings

**Sections:**

**Account**
- Display current email (read-only)
- Change Password: current password + new password + confirm (inline form, not a separate page)
- On success → toast "Password updated"

**Support**
- "Contact Support" → opens default email client with pre-filled support address and subject line
- FAQ / Help link (static page, Phase 2)

**Plan (read-only in MVP)**
- Current plan: Free
- Usage: X of 5 URLs used
- "View Plans" button → links to Upgrade page

**Danger Zone**
- Delete Account (Phase 2, but design the section now as disabled/greyed)

---

### 11. Upgrade / Plans Page

**MVP behaviour:** No payment yet. Shows plan comparison table with a "Join Waitlist" CTA.

**Layout:**
- Current plan highlighted
- Plan cards: Free / Pro / Business with feature comparison
- CTA per paid plan: "Join Waitlist" (MVP) → "Upgrade" (Phase 2)
- Messaging: "More plans coming soon. Join the waitlist to get early access."

---

## Navigation Structure

```
Public
├── /                  Landing Page
├── /signup            Sign Up
├── /login             Log In
├── /forgot-password   Forgot Password
└── /reset-password    Reset Password (token via query param)

Authenticated
├── /dashboard         Dashboard (default after login)
├── /products/:id      Product Detail
├── /notifications     Notifications
├── /settings          Settings
└── /upgrade           Plans / Upgrade
```

**Route Guards:**
- Authenticated routes redirect to `/login` if no valid token
- Public auth routes (`/login`, `/signup`) redirect to `/dashboard` if already logged in

---

## Notification UX (In-App)

Two types of in-app feedback:

**Toast notifications** (ephemeral, 4 seconds):
- Product added successfully
- Product removed
- Password changed
- Error messages (API failures, network errors)

**Persistent notifications** (bell icon, Notifications page):
- Price drop alerts only
- Persist until manually read

---

## Empty & Loading States

Every screen must define all three:

| Screen | Loading | Empty |
|---|---|---|
| Dashboard | Skeleton card grid | Illustration + "Add your first product" |
| Notifications | Skeleton list | Illustration + "No drops yet" |
| Product Detail | Full-page skeleton | N/A (redirects to dashboard if not found) |

Loading states use skeleton screens (not spinners) wherever possible — they feel faster.

---

## Responsive Behaviour

| Breakpoint | Layout |
|---|---|
| Mobile (< 640px) | Single column, bottom nav bar, full-screen modals |
| Tablet (640–1024px) | Two-column product grid, side nav appears |
| Desktop (> 1024px) | Two or three-column grid, persistent side nav, slide-in panels |

The Add Product flow is the most critical to get right on mobile — it should feel like a native bottom sheet.

---

## Accessibility Requirements

- All interactive elements keyboard navigable
- Focus traps in modals and panels
- ARIA labels on icon-only buttons (bell, avatar, close)
- Colour is never the only indicator of state (price drop uses icon + colour + text)
- Minimum tap target: 44x44px on mobile
- Error messages associated with their inputs via `aria-describedby`

---

## Success Metrics (Frontend)

- Time from landing to first product tracked: under 2 minutes
- Zero confusion about what the plan limit means
- Users return after first price drop notification
- Mobile experience rated equivalent to desktop in feedback
