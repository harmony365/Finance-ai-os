# Odoo connector

CUSTOMER #001's deployed Odoo 19 instance currently works through XML-RPC. Finance Core uses it only for read operations (`search_read`, `fields_get`) during the pilot.

Odoo 19 deprecates XML-RPC/JSON-RPC in favor of JSON-2. Keep the connector boundary isolated so the transport can be replaced without changing Finance Core/MCP contracts.
