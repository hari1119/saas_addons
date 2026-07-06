# -*- coding: utf-8 -*-

import base64

from odoo import _, fields, http
from odoo.addons.website_sale.controllers.main import WebsiteSale
from odoo.http import request


class WebsiteSaleQRPayment(WebsiteSale):

    def _get_shop_payment_values(self, order, **kwargs):
        values = super()._get_shop_payment_values(order, **kwargs)
        values['qr_payment_error'] = kwargs.get('qr_payment_error')
        return values

    def _get_mandatory_billing_address_fields(self, country_sudo):
        return {'name', 'phone'} | self._get_mandatory_address_fields(country_sudo)

    def _get_mandatory_delivery_address_fields(self, country_sudo):
        return {'name', 'phone'} | self._get_mandatory_address_fields(country_sudo)


class QRPaymentProofController(WebsiteSaleQRPayment):

    @http.route(
        '/shop/cod/confirm',
        type='http',
        auth='public',
        website=True,
        methods=['POST'],
        csrf=True,
    )
    def confirm_cash_on_delivery(self, **post):
        order_sudo = request.cart.sudo() if request.cart else request.env['sale.order']
        if not order_sudo or not order_sudo.order_line:
            return request.redirect('/shop/cart')

        if redirection := self._check_cart_and_addresses(order_sudo):
            return redirection

        if not request.website.cod_payment_enabled:
            return request.redirect('/shop/payment')

        if order_sudo.state not in ('draft', 'sent'):
            return request.redirect('/shop/payment')

        order_sudo.write({'is_cash_on_delivery': True})
        order_sudo.message_post(body=_('Customer selected Cash on Delivery from the website checkout.'))
        order_sudo.action_confirm()

        request.session['sale_last_order_id'] = order_sudo.id
        request.website.sale_reset()
        return request.redirect('/shop/confirmation')

    @http.route(
        '/shop/qr_payment/submit',
        type='http',
        auth='public',
        website=True,
        methods=['POST'],
        csrf=True,
    )
    def submit_qr_payment_proof(self, **post):
        order_sudo = request.cart.sudo() if request.cart else request.env['sale.order']
        if not order_sudo or not order_sudo.order_line:
            return request.redirect('/shop/cart')

        website = request.website
        if not website.qr_payment_enabled:
            return request.redirect('/shop/payment')

        proof_file = request.httprequest.files.get('qr_payment_proof')
        if not proof_file:
            return request.redirect('/shop/payment?qr_payment_error=missing_proof')

        proof_data = proof_file.read()
        if not proof_data:
            return request.redirect('/shop/payment?qr_payment_error=missing_proof')

        if len(proof_data) > 8 * 1024 * 1024:
            return request.redirect('/shop/payment?qr_payment_error=file_too_large')

        if order_sudo.state == 'draft':
            order_sudo.action_quotation_sent()

        order_sudo.write({
            'qr_payment_state': 'pending',
            'qr_payment_proof': base64.b64encode(proof_data),
            'qr_payment_proof_filename': proof_file.filename,
            'qr_payment_customer_reference': post.get('qr_payment_customer_reference'),
            'qr_payment_submitted_at': fields.Datetime.now(),
            'qr_payment_rejection_reason': False,
        })
        order_sudo.message_post(body=_('Customer uploaded QR payment proof from the website.'))

        request.session['sale_last_order_id'] = order_sudo.id
        request.website.sale_reset()
        return request.redirect('/shop/confirmation')
