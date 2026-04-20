# SaaS Subscription Manager — Odoo 19

A production-ready Odoo 19 module for managing SaaS subscriptions, restricting company access based on plan type and duration, and tracking revenue analytics.

---

## Table of Contents

- [Features](#features)
- [Module Structure](#module-structure)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [Access Control Logic](#access-control-logic)
- [Payment Integrations](#payment-integrations)
- [Testing](#testing)
- [SaaS Best Practices](#saas-best-practices)

---

## Features

| Area | Details |
|------|---------|
| **Plans** | Gold, Silver, Diamond (and custom) with pricing, duration, feature limits |
| **State Machine** | Draft → Trial → Active → Grace → Expired → Cancelled |
| **Access Control** | `subscription_locked` flag auto-synced; admins bypass all restrictions |
| **Notifications** | Automated email alerts at 7 days, 3 days, 1 day before expiry, and on expiry |
| **Grace Period** | Configurable per plan (e.g., 7 days after expiry before full lockout) |
| **Analytics** | Pivot / graph views, MRR calculation, revenue by plan, activity logs |
| **Renewal Wizard** | One-click plan upgrade / renewal with optional invoice creation |
| **Payment Hooks** | Stripe & PayPal webhook endpoints (`/saas/webhook/stripe`, `/saas/webhook/paypal`) |
| **PDF Report** | Printable subscription certificate |
| **Demo Data** | 4 plans + 1 sample active subscription on install |
| **Unit Tests** | 20+ tests covering creation, state machine, expiry, access control, notifications |

---

## Module Structure

```
saas_subscription/
├── __init__.py
├── __manifest__.py
│
├── models/
│   ├── subscription_type.py    # Plan definitions (Gold, Silver, Diamond …)
│   ├── subscription.py         # Core subscription model + cron logic
│   ├── subscription_log.py     # Immutable activity log
│   ├── res_company.py          # Adds subscription_locked + computed fields
│   └── res_users.py            # Access control helpers + is_saas_admin flag
│
├── views/
│   ├── subscription_type_views.xml
│   ├── subscription_views.xml
│   ├── res_company_views.xml
│   ├── dashboard_views.xml
│   ├── report_views.xml
│   └── menu_views.xml
│
├── wizards/
│   ├── subscription_renewal_wizard.py
│   └── subscription_renewal_wizard_views.xml
│
├── controllers/
│   └── main.py                 # Portal page + Stripe/PayPal webhooks + dashboard API
│
├── report/
│   └── subscription_report.xml # QWeb PDF certificate
│
├── security/
│   ├── security.xml            # Groups + record rules
│   └── ir.model.access.csv
│
├── data/
│   ├── sequence_data.xml       # SUB/YYYY/MM/XXXX sequence
│   ├── email_templates.xml     # 4 mail.template records
│   ├── cron_jobs.xml           # Daily expiry cron
│   └── demo_data.xml           # Sample plans + subscription
│
├── static/src/
│   ├── css/dashboard.css
│   ├── js/dashboard.js         # OWL Dashboard component
│   └── xml/dashboard.xml       # OWL template
│
└── tests/
    └── test_subscription.py    # Full test suite
```

---

## Installation

### Prerequisites

- Odoo 19 (Community or Enterprise)
- Python packages: `python-dateutil` (usually bundled)

### Steps

1. **Clone / copy** this module into your Odoo `addons` directory:

   ```bash
   cp -r saas_subscription /opt/odoo/addons/
   ```

2. **Update the apps list** in Odoo:

   ```bash
   # Restart Odoo with --update=all or via the UI
   ./odoo-bin -c odoo.conf -u all
   ```

   Or, from Settings → Activate developer mode → Apps → Update Apps List.

3. **Install** the module:

   Search for *"SaaS Subscription Manager"* in the Apps menu and click **Install**.

4. **Restart Odoo** after installation to ensure static assets and cron jobs are registered.

---

## Configuration

### 1. Create Subscription Plans

Go to **SaaS Subscriptions → Configuration → Subscription Plans** and create your plans:

| Field | Example |
|-------|---------|
| Plan Name | Gold |
| Plan Code | GOLD |
| Plan Level | gold |
| Duration | 6 months |
| Price | $99.99 |
| Max Users | 50 |
| Max Storage | 100 GB |
| Grace Period | 7 days |
| Trial Days | 14 |

### 2. Assign Subscriptions to Companies

Go to **SaaS Subscriptions → Subscriptions → All Subscriptions** → New:

- Select the **Company**
- Select the **Plan**
- Set the **Start Date**
- Click **Confirm** to activate

### 3. Security Groups

| Group | Capabilities |
|-------|-------------|
| **SaaS Administrator** | Full access; bypasses all subscription locks; inherits `base.group_system` |
| **SaaS Manager** | Create/manage subscriptions; view analytics |
| **SaaS User** | Read-only access to their own company's subscription |

Assign via **Settings → Users → (user) → SaaS Subscription** tab.

### 4. Mark SaaS Admin users

On any user form, set **Is SaaS Admin = True** to bypass subscription enforcement at runtime.

### 5. Email Outbound Server

Configure an outbound mail server under **Settings → Technical → Outbound Mail Servers** so expiry email notifications are delivered.

### 6. Payment Gateway Webhooks

| Gateway | Webhook URL |
|---------|------------|
| Stripe | `https://yourdomain.com/saas/webhook/stripe` |
| PayPal | `https://yourdomain.com/saas/webhook/paypal` |

Set `metadata.subscription_reference` on your Stripe invoices (or `resource.custom` on PayPal) to the subscription `reference` field value to enable auto-renewal.

---

## Usage

### Subscription Lifecycle

```
Draft ──► Trial (optional) ──► Active ──► Grace ──► Expired
  │                               │                      │
  └───────────────────────────────┴──────────────────────┴── Cancelled (any time)
```

- **Confirm** a draft to start the subscription
- The daily cron automatically advances states based on dates
- **Renew Wizard** (button on form): upgrade plan + extend end date + optionally invoice

### Renewal Wizard

From any subscription form, click **Renew** to open the wizard:

1. Select the new plan (can be an upgrade/downgrade)
2. Set the new start date
3. Toggle *Create Invoice* if billing is required
4. Click **Renew Subscription**

### Dashboard

Navigate to **SaaS Subscriptions → Dashboard** for a real-time view of:

- Active / Trial / Grace / Expired KPI cards
- Monthly Recurring Revenue (MRR)
- Subscriptions expiring in ≤ 7 days (click to drill down)
- Revenue distribution by plan (table with progress bars)

### PDF Certificate

From any subscription form, use the **Print** menu → **Subscription Certificate** to generate a PDF.

---

## Access Control Logic

### How locking works

1. The `res.company.subscription_locked` boolean is set/cleared by `_sync_company_lock()` after every state change.
2. `res.users._check_subscription_access()` is called at login/session check.
3. If `subscription_locked = True` and no active/trial/grace subscription exists, an `AccessError` is raised.
4. **Bypass conditions** (never blocked):
   - Users with `base.group_system` (Odoo admins)
   - Users with `is_saas_admin = True`

### User Quota Enforcement

`res.users._check_user_limit()` can be called before creating new users to verify the active subscription's `max_users` limit. Returns `True` if unlimited (`max_users = 0`).

---

## Payment Integrations

### Stripe

The webhook at `/saas/webhook/stripe` handles:

- `invoice.payment_succeeded` → auto-renew the matching subscription
- `invoice.payment_failed` → log a warning

**Setup in Stripe Dashboard:**

1. Add the webhook endpoint URL
2. Select events: `invoice.payment_succeeded`, `invoice.payment_failed`
3. On each invoice, set `metadata.subscription_reference` to the Odoo subscription reference (e.g., `SUB/2025/04/0001`)

### PayPal

The webhook at `/saas/webhook/paypal` handles:

- `PAYMENT.SALE.COMPLETED` → auto-renew

**Setup:**

1. Register the webhook in PayPal Developer Dashboard
2. Set `resource.custom` to the subscription reference on each PayPal order

---

## Testing

### Run all tests

```bash
# From the Odoo root directory
python odoo-bin \
  -c odoo.conf \
  --test-enable \
  --stop-after-init \
  -d your_test_db \
  -i saas_subscription
```

### Run specific test class

```bash
python odoo-bin \
  -c odoo.conf \
  --test-tags saas_subscription.TestExpiryLogic \
  --stop-after-init \
  -d your_test_db
```

### Test classes

| Class | What it tests |
|-------|--------------|
| `TestSubscriptionCreation` | Sequence, computed dates, grace period, plan code uniqueness |
| `TestSubscriptionStateMachine` | All state transitions, trial flow, renewal flag reset |
| `TestExpiryLogic` | Cron advancing Active→Grace→Expired, `days_remaining`, `is_near_expiry` |
| `TestAccessControl` | `subscription_locked` toggling, user limit checks |
| `TestNotifications` | Cron calls notification method; flag behavior |
| `TestRenewalWizard` | Plan upgrade, end date computation |
| `TestSubscriptionType` | MRR computation, subscription count |

---

## SaaS Best Practices

### Multi-tenancy

- Each company is isolated via record rules; users only see their own subscription.
- Use Odoo's multi-company feature to host multiple tenants in one instance.
- Use the `max_users` / `max_storage_gb` limits to enforce plan quotas at the application level.

### Grace Periods

- Always configure a grace period (7–14 days recommended) to avoid abrupt service interruption for customers with payment delays.
- Notify customers at 7, 3, and 1 day before expiry (already handled by the cron + email templates).

### Auto-Renewal

- Enable `auto_renewal` on plans that support it; connect Stripe/PayPal webhooks to trigger `action_renew()` on successful payment.
- Store the external `payment_reference` on the subscription for reconciliation.

### Scaling

- The `subscription_locked` flag check is a single boolean read — extremely fast at login.
- Cron runs once per day; increase frequency for high-churn environments.
- Use Odoo's standard `ir.rule` mechanism (already in place) to keep tenant data isolated.

### Monitoring

- Use **Reporting → Activity Logs** to audit all state changes with timestamps and user.
- Set up Odoo's built-in monitoring or integrate with external APM (Datadog, Sentry).
- Track MRR trends via **Reporting → Subscription Analytics** pivot view.

### Backup & Recovery

- Back up the database before running large migrations.
- Test expiry/lock logic in a staging environment before production deployment.
- Use `noupdate="1"` on cron jobs and email templates (already set) to protect customizations during module upgrades.
