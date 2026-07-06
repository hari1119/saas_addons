# -*- coding: utf-8 -*-

from odoo import fields, models


class Website(models.Model):
    _inherit = 'website'

    qr_payment_enabled = fields.Boolean(
        string='Enable QR Payment Proof',
        help='Show a QR/manual payment option on this website checkout.',
    )
    qr_payment_upi_id = fields.Char(
        string='UPI ID',
        help='UPI ID used to build the checkout QR code.',
    )
    qr_payment_payee_name = fields.Char(
        string='Payee Name',
        help='Name displayed in the payment app when scanning the QR code.',
    )
    qr_payment_note = fields.Char(
        string='Payment Note',
        default='Website order payment',
        help='Default note included in the QR payment payload.',
    )
    qr_payment_bank_details = fields.Text(
        string='Manual Payment Instructions',
        help='Optional bank/account details shown below the QR code.',
    )
    cod_payment_enabled = fields.Boolean(
        string='Enable Cash on Delivery',
        help='Show a Cash on Delivery option on this website checkout.',
    )
