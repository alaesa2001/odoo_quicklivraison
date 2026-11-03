from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class SaleOrder(models.Model):
    _inherit = "sale.order"

    quicklivraison_city_id = fields.Many2one("quicklivraison.city", string="Quick Livraison City", tracking=True)
    quicklivraison_tracking = fields.Char(copy=False, readonly=True, tracking=True, index=True)
    quicklivraison_status = fields.Char(copy=False, readonly=True, tracking=True)
    quicklivraison_status_second = fields.Char(copy=False, readonly=True)
    quicklivraison_exported_at = fields.Datetime(copy=False, readonly=True)
    quicklivraison_last_sync = fields.Datetime(copy=False, readonly=True)
    quicklivraison_tracking_url = fields.Char(compute="_compute_quicklivraison_tracking_url")

    def _compute_quicklivraison_tracking_url(self):
        for order in self:
            order.quicklivraison_tracking_url = order.quicklivraison_tracking and "https://clients.quicklivraison.ma/parcel/suivi/%s" % order.quicklivraison_tracking or False

    def _quicklivraison_payload(self):
        self.ensure_one()
        partner = self.partner_shipping_id or self.partner_id
        missing = []
        if not self.quicklivraison_city_id: missing.append(_("Quick Livraison city"))
        if not partner.name: missing.append(_("recipient name"))
        if not (partner.mobile or partner.phone): missing.append(_("phone"))
        if not (partner.street or partner.contact_address): missing.append(_("address"))
        if missing:
            raise ValidationError(_("Missing required delivery data: %s") % ", ".join(missing))
        product_lines = self.order_line.filtered(lambda line: not line.display_type and line.product_id.type != "service")
        return {
            "district_id": self.quicklivraison_city_id.external_id,
            "name": partner.name,
            "phone": partner.mobile or partner.phone,
            "address": ", ".join(filter(None, [partner.street, partner.street2, partner.city])) or partner.contact_address,
            "amount": self.amount_total,
            "note": self.note or _("Odoo order %s") % self.name,
            "prd_name": ", ".join(product_lines.mapped("product_id.display_name")) or _("Order %s") % self.name,
            "qte_prd": int(sum(product_lines.mapped("product_uom_qty"))) or 1,
            "code": "ODOO-%s" % self.id,
        }

    def action_quicklivraison_export(self):
        api = self.env["quicklivraison.api"]
        for order in self:
            if order.quicklivraison_tracking:
                raise UserError(_("Order %s was already exported as %s.") % (order.name, order.quicklivraison_tracking))
            result = api.create_parcel(order._quicklivraison_payload())
            tracking = result.get("tracking_number") if isinstance(result, dict) else None
            if not tracking:
                raise UserError(_("Quick Livraison did not return a tracking number."))
            order.write({"quicklivraison_tracking": tracking, "quicklivraison_status": "NEW_PARCEL", "quicklivraison_exported_at": fields.Datetime.now()})
            order.message_post(body=_("Quick Livraison parcel created: %s") % tracking)
        return True

    def action_confirm(self):
        result = super().action_confirm()
        enabled = self.env["ir.config_parameter"].sudo().get_param("quicklivraison.auto_export") == "True"
        if enabled:
            for order in self.filtered(lambda record: not record.quicklivraison_tracking and record.quicklivraison_city_id):
                try:
                    order.action_quicklivraison_export()
                except (UserError, ValidationError) as exc:
                    order.message_post(body=_("Quick Livraison automatic export skipped: %s") % exc)
        return result

    def action_quicklivraison_sync(self):
        api = self.env["quicklivraison.api"]
        for order in self.filtered("quicklivraison_tracking"):
            result = api.track_parcel(order.quicklivraison_tracking)
            values = {"quicklivraison_status": result.get("status"), "quicklivraison_status_second": result.get("status_second"), "quicklivraison_last_sync": fields.Datetime.now()}
            changed = values["quicklivraison_status"] != order.quicklivraison_status or values["quicklivraison_status_second"] != order.quicklivraison_status_second
            order.write(values)
            if changed:
                order.message_post(body=_("Quick Livraison status: %(status)s %(secondary)s", status=values["quicklivraison_status"] or "-", secondary=values["quicklivraison_status_second"] or ""))
        return True

    def action_open_quicklivraison_tracking(self):
        self.ensure_one()
        if not self.quicklivraison_tracking_url: raise UserError(_("This order has no Quick Livraison tracking number."))
        return {"type": "ir.actions.act_url", "url": self.quicklivraison_tracking_url, "target": "new"}

    @api.model
    def _cron_quicklivraison_sync(self):
        if self.env["ir.config_parameter"].sudo().get_param("quicklivraison.auto_sync") != "True": return
        orders = self.search([("quicklivraison_tracking", "!=", False), ("quicklivraison_status", "not in", ["DELIVERED", "RETURNED_CLIENT"])], limit=100)
        for order in orders:
            try: order.action_quicklivraison_sync()
            except UserError as exc: order.message_post(body=_("Quick Livraison synchronization failed: %s") % exc)
