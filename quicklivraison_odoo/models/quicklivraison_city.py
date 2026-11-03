from odoo import _, api, fields, models
from odoo.exceptions import UserError


class QuickLivraisonCity(models.Model):
    _name = "quicklivraison.city"
    _description = "Quick Livraison City"
    _order = "name"

    name = fields.Char(required=True, index=True)
    external_id = fields.Integer(required=True, index=True)
    active = fields.Boolean(default=True)
    fee = fields.Float()
    delivery_time = fields.Char()
    _sql_constraints = [("external_id_unique", "UNIQUE(external_id)", "Quick Livraison city ID must be unique.")]

    @api.model
    def action_sync_cities(self):
        result = self.env["quicklivraison.api"].get_cities()
        rows = result.get("cities", []) if isinstance(result, dict) else result
        if not isinstance(rows, list):
            raise UserError(_("Unexpected cities response from Quick Livraison."))
        seen = set()
        for row in rows:
            external_id = int(row.get("city_id") or row.get("id") or 0)
            name = row.get("city_name") or row.get("name")
            if not external_id or not name:
                continue
            seen.add(external_id)
            values = {
                "name": name,
                "external_id": external_id,
                "active": True,
                "fee": float(row.get("fee") or row.get("price") or 0),
                "delivery_time": str(row.get("delivery_time") or row.get("delay") or ""),
            }
            city = self.search([("external_id", "=", external_id)], limit=1)
            city.write(values) if city else self.create(values)
        if seen:
            self.search([("external_id", "not in", list(seen))]).write({"active": False})
        return {
            "type": "ir.actions.client", "tag": "display_notification",
            "params": {"title": _("Quick Livraison"), "message": _("%s cities synchronized.") % len(seen), "type": "success"},
        }
