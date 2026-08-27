#!/usr/bin/env bash
set -euo pipefail
ODOO_CONTAINER="${ODOO_CONTAINER:-$(docker ps --filter 'ancestor=odoo:19.0' --format '{{.Names}}' | head -1)}"
: "${ODOO_CONTAINER:?Could not detect Odoo 19 container. Set ODOO_CONTAINER.}"
DB="${ODOO_DB:-finance_demo}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
docker cp "$ROOT/odoo_tools/seed_customer001.py" "$ODOO_CONTAINER:/tmp/seed_customer001.py"
docker exec -i \
  -e DEMO_AS_OF="${DEMO_AS_OF:-$(date +%F)}" \
  -e DEMO_COMPANY_NAME="${DEMO_COMPANY_NAME:-Finance AI Demo SL}" \
  -e DEMO_SEED="${DEMO_SEED:-42001}" \
  "$ODOO_CONTAINER" bash -lc "odoo shell -d '$DB' --db_host=\"\$HOST\" --db_user=\"\$USER\" --db_password=\"\$PASSWORD\" < /tmp/seed_customer001.py"
