# -*- coding: utf-8 -*-
from datetime import date
from dateutil.relativedelta import relativedelta
from datetime import timedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class SubscriptionRenewalWizard(models.TransientModel):
    _name = 'saas.subscription.renewal.wizard'
    _description = 'Subscription Renewal Wizard'

    subscription_id = fields.Many2one(
        'saas.subscription', string='Subscription', required=True,
        default=lambda self: self.env.context.get('active_id')
    )
    company_id = fields.Many2one(
        related='subscription_id.company_id', readonly=True
    )
    current_plan_id = fields.Many2one(
        related='subscription_id.type_id', readonly=True
    )
    current_end_date = fields.Date(
        related='subscription_id.end_date', readonly=True
    )
    new_plan_id = fields.Many2one(
        'saas.subscription.type', string='New Plan', required=True,
        default=lambda self: self._default_plan()
    )
    new_start_date = fields.Date(
        string='New Start Date', required=True,
        default=fields.Date.today
    )
    new_end_date = fields.Date(
        string='New End Date', compute='_compute_new_end_date', store=True
    )
    create_invoice = fields.Boolean(
        string='Create Invoice', default=True
    )
    renewal_notes = fields.Text(string='Notes')

    def _default_plan(self):
        sub_id = self.env.context.get('active_id')
        if sub_id:
            sub = self.env['saas.subscription'].browse(sub_id)
            return sub.type_id
        return False

    @api.depends('new_plan_id', 'new_start_date')
    def _compute_new_end_date(self):
        for rec in self:
            if not rec.new_plan_id or not rec.new_start_date:
                rec.new_end_date = False
                continue
            unit = rec.new_plan_id.duration_unit
            value = rec.new_plan_id.duration_value
            if unit == 'days':
                rec.new_end_date = rec.new_start_date + timedelta(days=value)
            elif unit == 'months':
                rec.new_end_date = rec.new_start_date + relativedelta(months=value)
            else:
                rec.new_end_date = rec.new_start_date + relativedelta(years=value)

    def action_renew(self):
        self.ensure_one()
        sub = self.subscription_id
        sub.write({
            'type_id': self.new_plan_id.id,
            'start_date': self.new_start_date,
            'end_date': self.new_end_date,
            'state': 'active',
            'notified_7days': False,
            'notified_3days': False,
            'notified_1day': False,
            'notified_expired': False,
        })
        sub._log_state_change(
            f'Renewed to {self.new_plan_id.name} until '
            f'{self.new_end_date.strftime("%Y-%m-%d")}'
        )
        if self.create_invoice:
            sub.action_create_invoice()

        return {'type': 'ir.actions.act_window_close'}
