# Finance AI OS v2.5 — CUSTOMER #001

Pilot stack for a real first customer: Odoo 19 + Finance Core + Finance MCP + OpenClaw/Hermes adapters + CFO Command Center.

## What is included

### v2.4.2 — Real Odoo seed
- 120 B2B customers
- 750 posted customer invoices
- invoice lines and due dates
- fully paid and partially paid invoices
- real residual balances after Odoo payment registration
- synthetic dispute tags on invoice `ref` for demo diagnostics

### v2.4.3 — Real Finance Core
- AR open
- DSO from Odoo
- aging current / 1-30 / 31-60 / 61-90 / 90+
- overdue amount
- top customer concentration
- cash-recovery candidate pool
- dispute exposure

### v2.4.4 — Finance MCP
Tools:
- `get_ar_summary`
- `get_dso`
- `get_aging`
- `get_top_overdue_customers`
- `get_cash_risk`
- `explain_dso_change`

### v2.4.5 — OpenClaw / Hermes
Runtime configs are in `runtimes/`. Keep the pilot in **SHADOW** and **READ ONLY**.

### v2.5 — CFO Command Center
`http://SERVER:8088`

## IMPORTANT: existing Odoo web user
The current `movimientocolibrilatam@gmail.com` account is a Portal user (`share=true`). Do not change it with SQL. Use the included Odoo ORM repair script:

```bash
export ODOO_WEB_LOGIN='movimientocolibrilatam@gmail.com'
read -s ODOO_WEB_PASSWORD; export ODOO_WEB_PASSWORD
./scripts/fix-odoo-web-user.sh
```

Then log in at `/web`, not `/my`.

The script removes the Portal group, makes the account an Internal User and, by default, grants Settings administration for this demo environment. Set `ODOO_WEB_GRANT_SETTINGS=false` if you only want internal access.

## Seed the real Odoo demo
**Do this only on the demo database, never over a customer's accounting database containing production entries.**

```bash
export ODOO_DB=finance_demo
./scripts/seed-customer001.sh
```

The seed is deterministic and rerunnable; individual demo invoices use `FINANCEAI-DEMO-001-####` markers.

## Rebuild Finance Core / MCP after deploying v2.5

```bash
docker compose up -d --build finance-core finance-mcp
./scripts/verify-full-stack.sh
```

## Connect existing OpenClaw and Hermes containers

```bash
./scripts/connect-runtimes.sh
```

Then load the runtime configuration from:
- `runtimes/openclaw/`
- `runtimes/hermes/`

## Pilot safety
- `FINANCE_MODE=SHADOW`
- `READ_ONLY=true`
- no outbound email
- no credit-limit changes
- no payment execution
- no posting/modification of production ERP data
- human approval required for every proposed action

See `docs/CUSTOMER001_RUNBOOK.md` for the 30-day rollout.
