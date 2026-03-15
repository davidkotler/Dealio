Product Requirements Document (PRD) — Price Drop Tracker Web App

Product Name (MVP placeholder): Price Alert

Vision:
Help users save money and never miss a deal by automatically tracking product prices across any website and notifying them of price drops.

Target Users:
- Online shoppers who want to track deals
- Bargain hunters
- Users with limited time who want automated alerts

---

1️⃣ Key Features

User Management
- Sign up and log in with email
- Password reset
- Settings page:
  - Change password
  - Contact support via email

Product Tracking
- Users can add any product URL they want to track
- Limit: Up to 5 products per free user (for MVP)
- Users can remove products from tracking at any time
- Dashboard shows tracked products with:
  - Product name
  - Current price
  - Previous price
  - Last checked time

Price Monitoring
- System monitors all tracked products and detects any price drop
- Users receive notifications when a price drops

Notifications
- Email notifications sent to the user’s registered email
- In-app notifications visible in the dashboard

Dashboard / Frontend
- List of tracked products with price info
- Ability to add or remove products
- Settings page for account management

---

2️⃣ User Flows

Flow 1 — Sign Up / Login
1. User opens app → chooses Sign Up or Login
2. Enter email and password
3. Successfully logged in → redirected to dashboard

Flow 2 — Add a Product
1. User clicks “Add Product”
2. Enter product URL
3. System validates and saves the product
4. Product appears in the dashboard with current and previous price

Flow 3 — Price Drop Notification
1. System checks tracked products periodically
2. Detects price drop
3. Sends email notification
4. Shows notification in dashboard

Flow 4 — Remove a Product
1. User clicks “Remove” on a product
2. Product removed from dashboard
3. No further notifications for that product

Flow 5 — Settings / Support
1. User opens Settings
2. Options:
   - Change password
   - Contact support via email

---

3️⃣ Constraints / Considerations
- Support any product URL (scraping challenges handled internally)
- Free users limited to 5 products
- Dashboard shows current and previous price
- Notifications via email and in-app only
- MVP focused on web app; mobile app optional for future

---

4️⃣ Success Metrics (MVP)
- Users can successfully track products and receive price drop notifications
- Dashboard accurately shows current and previous price
- Email notifications are received reliably
- Users can add/remove products easily
- Users find value and continue using the app beyond first week