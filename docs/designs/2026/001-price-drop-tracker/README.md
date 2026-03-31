# Price Drop Tracker

> Enable online shoppers to automatically track product prices across any website and receive notifications when prices drop.

## Vision

Users add any product URL to their personal dashboard and the system continuously monitors the price. When a price drops, users are notified instantly — by email and in-app — so they never miss a deal without spending time manually checking prices. The MVP targets web users tracking up to 5 products, with a clean dashboard showing current and previous prices alongside last-checked timestamps.

## Goals

- **Automated price monitoring**: Users receive price drop alerts without any manual checking
- **Universal URL tracking**: Any product from any e-commerce site can be tracked by pasting its URL
- **Reliable notifications**: Email and in-app notifications are delivered consistently when a price drops
- **Transparent price history**: The dashboard shows current price, previous price, and last-checked time so users can evaluate savings at a glance
- **Self-service account management**: Users can sign up, log in, change their password, and manage tracked products independently

## Rationale

Online shoppers routinely miss deals because manually rechecking product pages is tedious and easy to forget. Existing deal-alert tools require retailer-specific integrations or paid subscriptions. A generic URL-based tracker removes the friction — users track what they want, from wherever they shop, and are notified automatically. The MVP validates whether automated price monitoring drives user retention beyond the first week.

## Value Proposition

| Stakeholder | Value |
|-------------|-------|
| Online shopper | Never misses a price drop; saves time vs. manual checking |
| Bargain hunter | Tracks multiple products simultaneously; buys at the right moment |
| Time-constrained user | Automated alerts eliminate the need to revisit product pages |

## Non-Goals

- Mobile app (web only for MVP)
- Price history charts or trend analysis beyond current and previous price
- Paid/premium tiers or subscription billing in MVP
- Browser extension or one-click "add from page" tracking
- Social or sharing features (wishlists, shared alerts)
- Retailer-specific integrations or partnerships
- Push notifications (email and in-app only)

## Open Questions

- How will scraping be handled for sites with anti-bot protection (Cloudflare, CAPTCHA)? — Requires a technical spike to evaluate scraping strategy (Playwright headless, proxy rotation, scraping APIs)
- What is the price-check polling frequency? — Needs decision: every hour, every 6 hours, daily? Affects infrastructure cost
- How is "price" defined for pages with variants (size, color)? — Requires UX decision: track the URL as-is, or let users pin a specific variant?
- Will there be rate limiting or abuse controls for users adding URLs? — Needs security review for MVP

## Status

| Phase | State |
|-------|-------|
| **Inception** | ✅ Complete |
| **Discovery** | ✅ Complete |
| **Design** | 🔄 In Progress — HLD complete; LLD pending |
| **Breakdown** | ⬜ Not Started |
| **Implementation** | ⬜ Not Started |
| **Ship** | ⬜ Not Started |
