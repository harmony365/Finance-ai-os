#!/usr/bin/env bash
set -euo pipefail
ODOO_CONTAINER="${ODOO_CONTAINER:-$(docker ps --filter 'ancestor=odoo:19.0' --format '{{.Names}}' | head -1)}"
: "${ODOO_CONTAINER:?Could not detect Odoo 19 container. Set ODOO_CONTAINER.}"
: "${ODOO_WEB_LOGIN:=movimientocolibrilatam@gmail.com}"
if [[ -z "${ODOO_WEB_PASSWORD:-}" ]]; then
  read -rsp "New Odoo web password for ${ODOO_WEB_LOGIN}: " ODOO_WEB_PASSWORD; echo
  export ODOO_WEB_PASSWORD
fi
DB="${ODOO_DB:-finance_demo}"
POSTGRES_USER="${POSTGRES_USER:-odoo}"
POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-}"
if [[ -z "$POSTGRES_PASSWORD" ]]; then
  POSTGRES_PASSWORD="$(docker inspect "$ODOO_CONTAINER" --format '{{range .Config.Env}}{{println .}}{{end}}' | sed -n 's/^PASSWORD=//p' | head -1)"
fi
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
docker cp "$SCRIPT_DIR/odoo_tools/fix_web_user.py" "$ODOO_CONTAINER:/tmp/fix_web_user.py"
docker exec -i \
  -e WEB_LOGIN="$ODOO_WEB_LOGIN" \
  -e WEB_PASSWORD="$ODOO_WEB_PASSWORD" \
  -e WEB_NAME="${ODOO_WEB_NAME:-Finance AI Admin}" \
  -e WEB_GRANT_SETTINGS="${ODOO_WEB_GRANT_SETTINGS:-true}" \
  "$ODOO_CONTAINER" bash -lc "odoo shell -d '$DB' --db_host=\"\$HOST\" --db_user=\"\$USER\" --db_password=\"\$PASSWORD\" < /tmp/fix_web_user.py"
echo "Open: https://odoo.colibrilatam.io/web"
echo "Login: $ODOO_WEB_LOGIN"
