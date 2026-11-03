# Quick Livraison Connector for Odoo 18

Connects Odoo Sales to Quick Livraison using the official REST API.

## Features

- Synchronize Quick Livraison cities.
- Select the delivery city on a quotation/sales order.
- Create a parcel manually after confirmation.
- Optionally create the parcel automatically when confirming the quotation.
- Prevent duplicate exports by storing the tracking number.
- Track primary and secondary parcel statuses.
- Receive signed Quick Livraison webhooks.
- Poll active parcel statuses every 15 minutes as a fallback.
- Log parcel creation and status changes in the Odoo chatter.

## Installation

1. Copy `quicklivraison_odoo` into an Odoo addons directory.
2. Restart Odoo and update the Apps list.
3. Install **Quick Livraison Connector**.
4. Open **Settings → Quick Livraison**.
5. Enter the API key from **Quick Livraison → Profile → API**.
6. Test the connection and synchronize cities.
7. Optional: configure the displayed webhook URL and secret in the Quick Livraison client profile.

## Workflow

On a quotation, select a Quick Livraison city. Confirm the quotation, then click **Send to Quick Livraison** (or enable automatic export). The connector sends the shipping partner, order total, products, quantity and Odoo order reference to `/deliveries/store`. The returned tracking number is saved on the order.

Status updates arrive by signed webhook when configured. The scheduled synchronization remains available as a fallback.

## Important

- Designed for Odoo 18 Community and Enterprise.
- The order total is sent as the cash-on-delivery amount. Adjust `_quicklivraison_payload()` if your accounting flow uses a different COD amount.
- Never expose the Quick Livraison API key or webhook secret to portal/public users.
