# -*- coding: utf-8 -*-
from odoo import api, fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    # ─── Subscription state ───────────────────────────────────────────────────
    subscription_locked = fields.Boolean(
        string='Subscription Locked', default=False,
        help='Automatically set to True when no active subscription exists.'
    )
    current_subscription_id = fields.Many2one(
        'saas.subscription', string='Active Subscription',
        compute='_compute_current_subscription', store=False
    )
    subscription_state = fields.Char(
        string='Subscription Status', compute='_compute_current_subscription'
    )

    def _compute_current_subscription(self):
        Subscription = self.env['saas.subscription']
        for company in self:
            sub = Subscription.search([
                ('company_id', '=', company.id),
                ('state', 'in', ('active', 'trial', 'grace')),
            ], limit=1, order='start_date desc')
            company.current_subscription_id = sub
            company.subscription_state = sub.state if sub else 'none'
