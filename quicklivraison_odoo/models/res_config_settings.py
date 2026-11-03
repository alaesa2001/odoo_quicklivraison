import secrets

from odoo import _, api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    quicklivraison_base_url = fields.Char(config_parameter="quicklivraison.base_url", default="https://clients.quicklivraison.ma/api")
    quicklivraison_api_key = fields.Char(config_parameter="quicklivraison.api_key")
    quicklivraison_timeout = fields.Integer(config_parameter="quicklivraison.timeout", default=30)
    quicklivraison_auto_export = fields.Boolean(config_parameter="quicklivraison.auto_export")
    quicklivraison_auto_sync = fields.Boolean(config_parameter="quicklivraison.auto_sync", default=True)
    quicklivraison_webhook_secret = fields.Char(config_parameter="quicklivraison.webhook_secret")
    quicklivraison_webhook_token = fields.Char(config_parameter="quicklivraison.webhook_token", readonly=True)
    quicklivraison_webhook_url = fields.Char(compute="_compute_quicklivraison_webhook_url")

    @api.depends("quicklivraison_webhook_token")
    def _compute_quicklivraison_webhook_url(self):
        base = self.env["ir.config_parameter"].sudo().get_param("web.base.url", "")
        for record in self:
            record.quicklivraison_webhook_url = "%s/quicklivraison/webhook/%s" % (base.rstrip("/"), record.quicklivraison_webhook_token or "TOKEN")

    @api.model
    def get_values(self):
        values = super().get_values()
        params = self.env["ir.config_parameter"].sudo()
        if not params.get_param("quicklivraison.webhook_token"):
            params.set_param("quicklivraison.webhook_token", secrets.token_urlsafe(24))
        return values

    def action_quicklivraison_test(self):
        count = self.env["quicklivraison.api"].test_connection()
        return {"type": "ir.actions.client", "tag": "display_notification", "params": {
            "title": _("Quick Livraison"), "message": _("Connection successful: %s cities available.") % count, "type": "success"}}

    def action_quicklivraison_sync_cities(self):
        return self.env["quicklivraison.city"].action_sync_cities()
