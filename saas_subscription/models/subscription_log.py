# -*- coding: utf-8 -*-
from odoo import fields, models


class SaasSubscriptionLog(models.Model):
    _name = 'saas.subscription.log'
    _description = 'SaaS Subscription Activity Log'
    _order = 'create_date desc'

    subscription_id = fields.Many2one(
        'saas.subscription', string='Subscription',
        ondelete='cascade', required=True, index=True
    )
    company_id = fields.Many2one(
        'res.company', string='Company', ondelete='cascade', index=True
    )
    message = fields.Char(string='Event', required=True)
    state = fields.Char(string='Subscription State')
    user_id = fields.Many2one(
        'res.users', string='User', default=lambda self: self.env.user
    )
    create_date = fields.Datetime(string='Date', readonly=True)
