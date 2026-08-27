# Fix Odoo `/web` access

Observed state on CUSTOMER #001:

```text
admin                             share=false  -> internal
movimientocolibrilatam@gmail.com  share=true   -> portal
```

That is why the email account lands in `/my`.

## Safe fix
Do not edit Odoo access-control tables directly in PostgreSQL. Use the Odoo ORM:

```bash
cd finance-ai-os-v2.5-customer001
export ODOO_DB=finance_demo
export ODOO_WEB_LOGIN='movimientocolibrilatam@gmail.com'
read -s ODOO_WEB_PASSWORD; export ODOO_WEB_PASSWORD
./scripts/fix-odoo-web-user.sh
```

The script:
- finds the existing account by login
- removes Portal membership
- adds Internal User
- sets `share=false`
- resets the web password
- optionally grants Settings administrator access

Then open:

```text
https://odoo.colibrilatam.io/web
```

For a real customer production system, grant only the minimum permissions required; do not use Settings administrator for the Finance AI integration service account.
