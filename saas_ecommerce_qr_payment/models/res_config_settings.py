# -*- coding: utf-8 -*-

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    qr_payment_enabled = fields.Boolean(
        related='website_id.qr_payment_enabled',
        readonly=False,
    )
    qr_payment_upi_id = fields.Char(
        related='website_id.qr_payment_upi_id',
        readonly=False,
    )
    qr_payment_payee_name = fields.Char(
        related='website_id.qr_payment_payee_name',
        readonly=False,
    )
    qr_payment_note = fields.Char(
        related='website_id.qr_payment_note',
        readonly=False,
    )
    qr_payment_bank_details = fields.Text(
        related='website_id.qr_payment_bank_details',
        readonly=False,
    )
    cod_payment_enabled = fields.Boolean(
        related='website_id.cod_payment_enabled',
        readonly=False,
    )
