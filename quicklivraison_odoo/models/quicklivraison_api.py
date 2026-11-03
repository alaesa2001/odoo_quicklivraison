import json
import logging

import requests

from odoo import _, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class QuickLivraisonAPI(models.AbstractModel):
    _name = "quicklivraison.api"
    _description = "Quick Livraison API Client"

    def _config(self):
        params = self.env["ir.config_parameter"].sudo()
        return {
            "base_url": (params.get_param("quicklivraison.base_url") or "https://clients.quicklivraison.ma/api").rstrip("/"),
            "api_key": params.get_param("quicklivraison.api_key") or "",
            "timeout": int(params.get_param("quicklivraison.timeout") or 30),
        }

    def _request(self, method, path, *, params=None, data=None, authenticated=False):
        config = self._config()
        if authenticated and not config["api_key"]:
            raise UserError(_("Configure the Quick Livraison API key first."))
        payload = dict(data or {})
        query = dict(params or {})
        if authenticated:
            if method.upper() == "GET":
                query["api_key"] = config["api_key"]
            else:
                payload["api_key"] = config["api_key"]
        try:
            response = requests.request(
                method.upper(), config["base_url"] + "/" + path.lstrip("/"),
                params=query, data=payload, timeout=config["timeout"],
                headers={"Accept": "application/json"},
            )
        except requests.RequestException as exc:
            _logger.exception("Quick Livraison request failed")
            raise UserError(_("Quick Livraison is unreachable: %s") % exc) from exc
        try:
            body = response.json()
        except (ValueError, json.JSONDecodeError):
            body = None
        if not response.ok:
            message = body.get("error") or body.get("message") if isinstance(body, dict) else response.text[:300]
            raise UserError(_("Quick Livraison error (HTTP %(code)s): %(message)s", code=response.status_code, message=message or _("Unknown error")))
        return body

    def get_cities(self):
        return self._request("GET", "/getCityIDs")

    def create_parcel(self, values):
        return self._request("POST", "/deliveries/store", data=values, authenticated=True)

    def track_parcel(self, tracking_number):
        return self._request("GET", "/getParcelDetails/%s" % tracking_number)

    def test_connection(self):
        data = self.get_cities()
        cities = data.get("cities", []) if isinstance(data, dict) else data
        if not isinstance(cities, list) or not cities:
            raise UserError(_("Connection succeeded, but no Quick Livraison cities were returned."))
        return len(cities)
