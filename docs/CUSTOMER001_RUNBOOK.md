# CUSTOMER #001 — 30-day pilot runbook

## Day 0 — Installation and access
1. Back up the Odoo database.
2. Verify Odoo, Finance Core and Finance MCP containers.
3. Repair/create the internal Odoo web user with `scripts/fix-odoo-web-user.sh`.
4. Confirm `/web` login and Settings access.
5. Keep `FINANCE_MODE=SHADOW` and `READ_ONLY=true`.

Acceptance:
- Odoo `/web` works for the internal finance administrator.
- Finance Core `/health` returns `ok=true`.
- Finance MCP `/health` returns `ok=true`.

## Day 1 — Demo data or production read-only mapping
For the sales demo database, run `scripts/seed-customer001.sh`.
For the customer's production ERP, DO NOT run the seed; map real posted invoices in read-only mode.

Acceptance:
- 120 demo customers and ~750 demo invoices in the demo database, OR production data mapped without writes.
- Finance Core invoice count matches Odoo.

## Days 2–7 — Baseline / SHADOW
Measure:
- sales last 365 days
- AR open
- DSO
- overdue
- aging buckets
- 61+ and 90+
- top-5 concentration
- dispute exposure
- cash-recovery candidate pool

No operational action is executed.

Data-quality gates:
- invoice coverage >= 98%
- AR difference vs ERP <= 0.5%
- due-date coverage >= 99%
- no unexplained source mismatch

## Days 8–14 — CFO insights
Daily/weekly CFO brief from MCP:
1. `get_ar_summary`
2. `get_dso`
3. `get_aging`
4. `get_cash_risk`
5. `get_top_overdue_customers`
6. `finance_alerts`

Deliver:
- what changed
- why it matters
- top 3 risks
- top 3 recommended actions
- clear human-approval label

## Days 15–21 — ASSISTED preparation
Only after CFO acceptance:
- draft collection priorities
- draft internal escalation notes
- draft customer outreach, but do not send
- simulate credit-review recommendations

No ERP mutation and no outbound action without explicit approval.

## Days 22–30 — ROI and go/no-go
Measure:
- DSO movement
- overdue movement
- 61+/90+ movement
- cash collected from prioritized accounts
- manual hours saved
- dispute resolution cycle time

Decision:
- GO: recurring subscription + production connector hardening
- NO-GO: document data, process or adoption blockers

## Production hardening after pilot
- dedicated read-only Odoo integration user
- API key rotation / secret manager
- JSON-2 adapter migration roadmap
- SSO/RBAC if required
- audit trail and approval workflow
- monitoring and backups
