# -*- coding: utf-8 -*-
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class SaasSubscription(models.Model):
    _name = 'saas.subscription'
    _description = 'SaaS Subscription'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'start_date desc, id desc'
    _rec_name = 'reference'

    # ─── Identification ──────────────────────────────────────────────────────
    reference = fields.Char(
        string='Reference', required=True, copy=False, readonly=True,
        default=lambda self: _('New')
    )
    type_id = fields.Many2one(
        'saas.subscription.type', string='Plan', required=True,
        ondelete='restrict', tracking=True
    )
    company_id = fields.Many2one(
        'res.company', string='Company', required=True,
        ondelete='cascade', tracking=True
    )

    # ─── Dates ───────────────────────────────────────────────────────────────
    start_date = fields.Date(
        string='Start Date', required=True, default=fields.Date.today,
        tracking=True
    )
    end_date = fields.Date(
        string='End Date', required=True, tracking=True,
        compute='_compute_end_date', store=True, readonly=False
    )
    grace_end_date = fields.Date(
        string='Grace Period End', compute='_compute_grace_end_date',
        store=True
    )
    trial_end_date = fields.Date(
        string='Trial End Date', compute='_compute_trial_end_date', store=True
    )

    # ─── State ───────────────────────────────────────────────────────────────
    state = fields.Selection([
        ('draft', 'Draft'),
        ('trial', 'Trial'),
        ('active', 'Active'),
        ('grace', 'Grace Period'),
        ('expired', 'Expired'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', required=True, tracking=True,
        copy=False
    )

    # ─── Billing ─────────────────────────────────────────────────────────────
    currency_id = fields.Many2one(
        related='type_id.currency_id', store=True
    )
    amount = fields.Monetary(
        string='Amount Paid', currency_field='currency_id', tracking=True
    )
    invoice_id = fields.Many2one(
        'account.move', string='Invoice', copy=False, readonly=True
    )
    payment_gateway = fields.Selection(
        related='type_id.payment_gateway', string='Payment Gateway'
    )
    payment_reference = fields.Char(
        string='Payment Reference', copy=False,
        help='External gateway transaction ID (Stripe charge ID, PayPal order ID, etc.)'
    )
    auto_renewal = fields.Boolean(
        string='Auto-Renewal', related='type_id.auto_renewal', store=True
    )

    # ─── Feature snapshot (at time of subscription) ──────────────────────────
    max_users = fields.Integer(
        related='type_id.max_users', store=True, string='Max Users'
    )
    max_storage_gb = fields.Float(
        related='type_id.max_storage_gb', store=True, string='Max Storage (GB)'
    )
    grace_period_days = fields.Integer(
        related='type_id.grace_period_days', store=True, string='Grace Period Days'
    )

    # ─── Notification tracking ────────────────────────────────────────────────
    notified_7days = fields.Boolean(default=False, copy=False)
    notified_3days = fields.Boolean(default=False, copy=False)
    notified_1day = fields.Boolean(default=False, copy=False)
    notified_expired = fields.Boolean(default=False, copy=False)

    # ─── Notes ───────────────────────────────────────────────────────────────
    note = fields.Text(string='Internal Notes')

    # ─── Computed helpers ────────────────────────────────────────────────────
    days_remaining = fields.Integer(
        string='Days Remaining', compute='_compute_days_remaining'
    )
    is_expired = fields.Boolean(
        string='Is Expired', compute='_compute_is_expired', store=True
    )
    is_near_expiry = fields.Boolean(
        string='Near Expiry (≤7 days)', compute='_compute_days_remaining'
    )

    # ─── SQL Constraints ─────────────────────────────────────────────────────
    _sql_constraints = [
        ('company_active_unique',
         "EXCLUDE USING gist (company_id WITH =) WHERE (state IN ('trial','active','grace'))",
         'A company may only have one active/trial/grace subscription at a time.'),
    ]

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # ORM Overrides
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('reference', _('New')) == _('New'):
                vals['reference'] = self.env['ir.sequence'].next_by_code(
                    'saas.subscription') or _('New')
        records = super().create(vals_list)
        return records

    def write(self, vals):
        result = super().write(vals)
        if 'state' in vals:
            self._sync_company_lock()
        return result

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # Compute Methods
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    @api.depends('start_date', 'type_id', 'type_id.duration_value',
                 'type_id.duration_unit')
    def _compute_end_date(self):
        for rec in self:
            if not rec.start_date or not rec.type_id:
                rec.end_date = False
                continue
            unit = rec.type_id.duration_unit
            value = rec.type_id.duration_value
            if unit == 'days':
                rec.end_date = rec.start_date + timedelta(days=value)
            elif unit == 'months':
                rec.end_date = rec.start_date + relativedelta(months=value)
            elif unit == 'years':
                rec.end_date = rec.start_date + relativedelta(years=value)
            else:
                rec.end_date = rec.start_date

    @api.depends('end_date', 'grace_period_days')
    def _compute_grace_end_date(self):
        for rec in self:
            if rec.end_date:
                rec.grace_end_date = rec.end_date + timedelta(
                    days=rec.grace_period_days or 0)
            else:
                rec.grace_end_date = False

    @api.depends('start_date', 'type_id.trial_days')
    def _compute_trial_end_date(self):
        for rec in self:
            trial_days = rec.type_id.trial_days if rec.type_id else 0
            if rec.start_date and trial_days:
                rec.trial_end_date = rec.start_date + timedelta(days=trial_days)
            else:
                rec.trial_end_date = False

    @api.depends('end_date', 'grace_end_date', 'state')
    def _compute_days_remaining(self):
        today = date.today()
        for rec in self:
            if rec.end_date:
                rec.days_remaining = (rec.end_date - today).days
                rec.is_near_expiry = 0 <= rec.days_remaining <= 7
            else:
                rec.days_remaining = 0
                rec.is_near_expiry = False

    @api.depends('end_date', 'grace_end_date', 'state')
    def _compute_is_expired(self):
        today = date.today()
        for rec in self:
            if rec.state in ('cancelled', 'expired'):
                rec.is_expired = True
            elif rec.grace_end_date:
                rec.is_expired = today > rec.grace_end_date
            elif rec.end_date:
                rec.is_expired = today > rec.end_date
            else:
                rec.is_expired = False

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # State Machine Actions
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    def action_confirm(self):
        """Move from draft → trial (if trial days > 0) or active."""
        for rec in self:
            if rec.state != 'draft':
                raise UserError(_('Only draft subscriptions can be confirmed.'))
            if rec.type_id.trial_days:
                rec.state = 'trial'
            else:
                rec.state = 'active'
            rec._log_state_change('Subscription confirmed')
        self._sync_company_lock()

    def action_activate(self):
        """Move trial → active (after trial period ends or manual)."""
        for rec in self:
            if rec.state not in ('draft', 'trial'):
                raise UserError(_('Subscription is not in trial/draft state.'))
            rec.state = 'active'
            rec._log_state_change('Subscription activated')
        self._sync_company_lock()

    def action_renew(self):
        """Renew: extend end_date from today and set active."""
        for rec in self:
            today = date.today()
            unit = rec.type_id.duration_unit
            value = rec.type_id.duration_value
            if unit == 'days':
                new_end = today + timedelta(days=value)
            elif unit == 'months':
                new_end = today + relativedelta(months=value)
            else:
                new_end = today + relativedelta(years=value)
            rec.write({
                'end_date': new_end,
                'state': 'active',
                'notified_7days': False,
                'notified_3days': False,
                'notified_1day': False,
                'notified_expired': False,
            })
            rec._log_state_change(
                f'Subscription renewed until {new_end.strftime("%Y-%m-%d")}'
            )
        self._sync_company_lock()

    def action_cancel(self):
        for rec in self:
            if rec.state == 'cancelled':
                raise UserError(_('Already cancelled.'))
            rec.state = 'cancelled'
            rec._log_state_change('Subscription cancelled')
        self._sync_company_lock()

    def action_expire(self):
        """Manually expire a subscription."""
        for rec in self:
            rec.state = 'expired'
            rec._log_state_change('Subscription expired (manual)')
        self._sync_company_lock()

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # Scheduled Actions (called by cron)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    @api.model
    def cron_check_expiry(self):
        """Daily cron: update states and fire notifications."""
        today = date.today()

        # 1. Trial → Active (trial ended)
        trial_subs = self.search([
            ('state', '=', 'trial'),
            ('trial_end_date', '!=', False),
            ('trial_end_date', '<', today),
        ])
        for sub in trial_subs:
            sub.state = 'active'
            sub._log_state_change('Trial period ended – now active')

        # 2. Active → Grace (end_date passed)
        active_subs = self.search([
            ('state', '=', 'active'),
            ('end_date', '<', today),
        ])
        for sub in active_subs:
            sub.state = 'grace'
            sub._log_state_change('Subscription in grace period')

        # 3. Grace → Expired (grace_end_date passed)
        grace_subs = self.search([
            ('state', '=', 'grace'),
            ('grace_end_date', '<', today),
        ])
        for sub in grace_subs:
            sub.state = 'expired'
            sub._log_state_change('Subscription expired')

        self._sync_company_lock()

        # 4. Send notification emails
        self._send_expiry_notifications()

    @api.model
    def _send_expiry_notifications(self):
        today = date.today()
        template_7 = self.env.ref(
            'saas_subscription.email_template_expiry_7days', raise_if_not_found=False)
        template_3 = self.env.ref(
            'saas_subscription.email_template_expiry_3days', raise_if_not_found=False)
        template_1 = self.env.ref(
            'saas_subscription.email_template_expiry_1day', raise_if_not_found=False)
        template_exp = self.env.ref(
            'saas_subscription.email_template_expired', raise_if_not_found=False)

        active_subs = self.search([('state', 'in', ('active', 'grace', 'trial'))])
        for sub in active_subs:
            days_left = (sub.end_date - today).days if sub.end_date else 999
            if days_left <= 7 and not sub.notified_7days and template_7:
                template_7.send_mail(sub.id, force_send=True)
                sub.notified_7days = True
            if days_left <= 3 and not sub.notified_3days and template_3:
                template_3.send_mail(sub.id, force_send=True)
                sub.notified_3days = True
            if days_left <= 1 and not sub.notified_1day and template_1:
                template_1.send_mail(sub.id, force_send=True)
                sub.notified_1day = True

        expired_subs = self.search([
            ('state', '=', 'expired'),
            ('notified_expired', '=', False),
        ])
        for sub in expired_subs:
            if template_exp:
                template_exp.send_mail(sub.id, force_send=True)
            sub.notified_expired = True

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # Helpers
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    def _sync_company_lock(self):
        """Set subscription_locked flag on each company based on subscription state."""
        companies = self.mapped('company_id')
        for company in companies:
            subs = self.search([
                ('company_id', '=', company.id),
                ('state', 'in', ('active', 'trial', 'grace')),
            ])
            company.sudo().subscription_locked = not bool(subs)

    def _log_state_change(self, message):
        self.ensure_one()
        self.env['saas.subscription.log'].create({
            'subscription_id': self.id,
            'company_id': self.company_id.id,
            'message': message,
            'state': self.state,
        })

    def action_create_invoice(self):
        """Create an account.move (invoice) for this subscription."""
        self.ensure_one()
        if not self.company_id.partner_id:
            raise UserError(_('The subscribed company has no linked partner.'))
        if self.invoice_id:
            raise UserError(_('An invoice already exists for this subscription.'))

        move = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.company_id.partner_id.id,
            'invoice_date': fields.Date.today(),
            'invoice_line_ids': [(0, 0, {
                'name': f'[{self.type_id.plan_code}] {self.type_id.name} — {self.reference}',
                'quantity': 1,
                'price_unit': self.type_id.price,
            })],
        })
        self.invoice_id = move
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'res_id': move.id,
            'view_mode': 'form',
        }

    # ─── Dashboard stats ─────────────────────────────────────────────────────
    @api.model
    def get_dashboard_data(self):
        """Return aggregated data for the JS dashboard widget."""
        today = date.today()
        Subscription = self.env['saas.subscription']

        active_count = Subscription.search_count([('state', '=', 'active')])
        trial_count = Subscription.search_count([('state', '=', 'trial')])
        grace_count = Subscription.search_count([('state', '=', 'grace')])
        expired_count = Subscription.search_count([('state', '=', 'expired')])
        expiring_soon = Subscription.search_count([
            ('state', '=', 'active'),
            ('end_date', '<=', today + timedelta(days=7)),
            ('end_date', '>=', today),
        ])

        # Monthly Revenue
        active_subs = Subscription.search([('state', '=', 'active')])
        monthly_revenue = sum(
            sub.type_id.price / (sub.type_id.duration_value or 1)
            * (1 if sub.type_id.duration_unit == 'months' else
               (1 / 12 if sub.type_id.duration_unit == 'years' else 1 / 30))
            for sub in active_subs
        )

        # Revenue by plan
        plans = self.env['saas.subscription.type'].search([])
        plan_revenue = []
        for plan in plans:
            plan_subs = Subscription.search([
                ('type_id', '=', plan.id),
                ('state', '=', 'active'),
            ])
            plan_revenue.append({
                'name': plan.name,
                'count': len(plan_subs),
                'revenue': plan.price * len(plan_subs),
                'color': plan.color,
            })

        return {
            'active': active_count,
            'trial': trial_count,
            'grace': grace_count,
            'expired': expired_count,
            'expiring_soon': expiring_soon,
            'monthly_revenue': round(monthly_revenue, 2),
            'plan_revenue': plan_revenue,
            'currency_symbol': self.env.company.currency_id.symbol,
        }
