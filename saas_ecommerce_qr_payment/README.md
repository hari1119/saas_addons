# SaaS eCommerce QR Payment Proof

This module adds a manual QR payment proof flow for small-business eCommerce sites in Odoo 19.

## What It Adds

- Uses standard Odoo eCommerce product listing in `/shop`.
- Adds QR/manual payment settings per Website, so each business/domain can use its own UPI ID or bank instructions.
- Shows a QR payment block on the checkout payment page.
- Lets the customer upload a payment screenshot or PDF.
- Keeps the order as an unpaid quotation until an internal user verifies the proof.
- Adds a `QR Payment Proofs` menu under eCommerce orders.
- Confirms the sale order only after internal verification.

## Setup

1. Install `website_sale` and this module.
2. Go to `Website > Configuration > Settings`.
3. Select the Website/domain at the top.
4. Set the Website domain, for example `https://shop.example.com`.
5. Enable `QR Payment Proof`.
6. Enter UPI ID and payee name, or enter manual bank instructions.
7. Publish products from the product master by enabling `Can be Sold` and `Published`.

## Order Flow

1. Customer adds products to cart and checks out.
2. Customer scans the QR code, pays, and uploads the screenshot.
3. The order moves to `QR Payment Status = Pending Verification`.
4. Internal user opens `eCommerce > Orders > QR Payment Proofs`.
5. Internal user verifies the screenshot.
6. Odoo confirms the sale order.
