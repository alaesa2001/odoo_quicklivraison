import hashlib
import hmac
import json

from odoo import http
from odoo.http import request


class QuickLivraisonWebhook(http.Controller):
    @http.route("/quicklivraison/webhook/<string:token>", type="http", auth="public", methods=["POST"], csrf=False)
    def webhook(self, token, **kwargs):
        params = request.env["ir.config_parameter"].sudo()
        expected_token = params.get_param("quicklivraison.webhook_token") or ""
        secret = params.get_param("quicklivraison.webhook_secret") or ""
        if not expected_token or not hmac.compare_digest(token, expected_token):
            return request.make_json_response({"error": "not found"}, status=404)
        raw = request.httprequest.get_data()
        signature = request.httprequest.headers.get("X-Webhook-Signature", "")
        expected = "sha256=" + hmac.new(secret.encode(), raw, hashlib.sha256).hexdigest()
        if not secret or not hmac.compare_digest(signature, expected):
            return request.make_json_response({"error": "invalid signature"}, status=401)
        try:
            payload = json.loads(raw.decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            return request.make_json_response({"error": "invalid json"}, status=400)
        data = payload.get("data") or {}
        tracking = data.get("tracking_number")
        order = request.env["sale.order"].sudo().search([("quicklivraison_tracking", "=", tracking)], limit=1)
        if order:
            status = data.get("status")
            secondary = data.get("status_second")
            changed = status != order.quicklivraison_status or secondary != order.quicklivraison_status_second
            order.write({"quicklivraison_status": status, "quicklivraison_status_second": secondary})
            if changed: order.message_post(body="Quick Livraison: %s %s" % (status or "-", secondary or ""))
        return request.make_json_response({"received": True})
