# -*- coding: utf-8 -*-

from urllib.parse import quote, urlencode

from odoo import _, fields, models
from odoo.exceptions import UserError


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    qr_payment_state = fields.Selection(
        selection=[
            ('not_submitted', 'Not Submitted'),
            ('pending', 'Pending Verification'),
            ('verified', 'Verified'),
            ('rejected', 'Rejected'),
        ],
        string='QR Payment Status',
        default='not_submitted',
        copy=False,
        tracking=True,
    )
    qr_payment_proof = fields.Binary(
        string='Payment Screenshot',
        attachment=True,
        copy=False,
    )
    qr_payment_proof_filename = fields.Char(
        string='Screenshot Filename',
        copy=False,
    )
    qr_payment_customer_reference = fields.Char(
        string='Customer Payment Reference',
        copy=False,
    )
    qr_payment_submitted_at = fields.Datetime(
        string='Proof Submitted On',
        copy=False,
    )
    qr_payment_verified_by_id = fields.Many2one(
        'res.users',
        string='Verified By',
        copy=False,
        readonly=True,
    )
    qr_payment_verified_at = fields.Datetime(
        string='Verified On',
        copy=False,
        readonly=True,
    )
    qr_payment_rejection_reason = fields.Text(
        string='Rejection Reason',
        copy=False,
    )
    qr_payment_payload = fields.Char(
        string='QR Payload',
        compute='_compute_qr_payment_payload',
    )
    qr_payment_qr_url = fields.Char(
        string='QR Code URL',
        compute='_compute_qr_payment_payload',
    )
    is_cash_on_delivery = fields.Boolean(
        string='Cash on Delivery',
        copy=False,
        tracking=True,
    )

    def _compute_qr_payment_payload(self):
        for order in self:
            website = order.website_id
            payload = ''
            if website and website.qr_payment_upi_id:
                params = {
                    'pa': website.qr_payment_upi_id,
                    'pn': website.qr_payment_payee_name or order.company_id.name,
                    'am': '%.2f' % order.amount_total,
                    'cu': order.currency_id.name,
                    'tn': '%s - %s' % (website.qr_payment_note or _('Website order'), order.name),
                }
                payload = 'upi://pay?%s' % urlencode(params)
            elif website and website.qr_payment_bank_details:
                payload = '%s\n%s\nAmount: %.2f %s\nOrder: %s' % (
                    website.name,
                    website.qr_payment_bank_details,
                    order.amount_total,
                    order.currency_id.name,
                    order.name,
                )
            order.qr_payment_payload = payload
            order.qr_payment_qr_url = payload and (
                '/report/barcode/?barcode_type=QR&value=%s&width=260&height=260'
                '&humanreadable=0' % quote(payload)
            ) or False

    def action_qr_payment_verify(self):
        for order in self:
            if order.qr_payment_state != 'pending':
                raise UserError(_('Only payments pending verification can be verified.'))
            if not order.qr_payment_proof:
                raise UserError(_('Please add the customer payment screenshot before verifying.'))
            if order.state not in ('draft', 'sent'):
                raise UserError(_('Only draft or sent quotations can be confirmed from QR verification.'))
            order.write({
                'qr_payment_state': 'verified',
                'qr_payment_verified_by_id': self.env.user.id,
                'qr_payment_verified_at': fields.Datetime.now(),
                'qr_payment_rejection_reason': False,
            })
            order.message_post(body=_('QR payment proof verified. The order has been confirmed.'))
            order.action_confirm()
        return True

    def action_qr_payment_reject(self):
        for order in self:
            if order.qr_payment_state != 'pending':
                raise UserError(_('Only payments pending verification can be rejected.'))
            order.write({
                'qr_payment_state': 'rejected',
                'qr_payment_verified_by_id': False,
                'qr_payment_verified_at': False,
            })
            order.message_post(body=_('QR payment proof rejected.'))
        return True

    def action_qr_payment_reset(self):
        self.write({
            'qr_payment_state': 'not_submitted',
            'qr_payment_proof': False,
            'qr_payment_proof_filename': False,
            'qr_payment_customer_reference': False,
            'qr_payment_submitted_at': False,
            'qr_payment_verified_by_id': False,
            'qr_payment_verified_at': False,
            'qr_payment_rejection_reason': False,
        })
        return True
