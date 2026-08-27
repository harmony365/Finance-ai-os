import os
from odoo import Command

login = os.environ.get("WEB_LOGIN", "movimientocolibrilatam@gmail.com").strip()
password = os.environ.get("WEB_PASSWORD", "").strip()
name = os.environ.get("WEB_NAME", "Finance AI Admin").strip()
grant_settings = os.environ.get("WEB_GRANT_SETTINGS", "true").lower() in {"1","true","yes","y"}

if not password:
    raise SystemExit("WEB_PASSWORD is required. Export it securely before running this script.")

Users = env["res.users"].sudo()
users = Users.search([("login", "=", login)], limit=1)
internal = env.ref("base.group_user")
portal = env.ref("base.group_portal")
system = env.ref("base.group_system")

group_field = "groups_id" if "groups_id" in Users._fields else "group_ids"
commands = [Command.unlink(portal.id), Command.link(internal.id)]
if grant_settings:
    commands.append(Command.link(system.id))

vals = {
    "active": True,
    "share": False,
    "password": password,
    group_field: commands,
}

if users:
    user = users
    user.write(vals)
    if user.partner_id:
        user.partner_id.write({"name": name, "email": login})
    action = "updated"
else:
    vals.update({"login": login, "name": name})
    user = Users.create(vals)
    action = "created"

env.cr.commit()
print(f"WEB_USER_{action.upper()}: id={user.id} login={user.login} share={user.share}")
print(f"INTERNAL_GROUP={internal in user[group_field]}")
print(f"SETTINGS_ADMIN={system in user[group_field]}")
print("LOGIN_URL=/web")
