# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class SaasSubscriptionType(models.Model):
    _name = 'saas.subscription.type'
    _description = 'SaaS Subscription Type'
    _order = 'sequence, name'

    # ─── Basic Info ──────────────────────────────────────────────────────────
    name = fields.Char(
        string='Plan Name', required=True, translate=True,
        help='e.g. Gold, Silver, Diamond'
    )
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    color = fields.Integer(string='Color Index', default=0)
    description = fields.Html(string='Description', translate=True)
    plan_code = fields.Char(
        string='Plan Code', required=True, copy=False,
        help='Unique internal code for this plan (e.g. GOLD, SILVER, DIAMOND)'
    )
    plan_level = fields.Selection([
        ('basic', 'Basic'),
        ('silver', 'Silver'),
        ('gold', 'Gold'),
        ('diamond', 'Diamond'),
        ('enterprise', 'Enterprise'),
    ], string='Plan Level', required=True, default='basic')

    # ─── Duration ────────────────────────────────────────────────────────────
    duration_unit = fields.Selection([
        ('days', 'Days'),
        ('months', 'Months'),
        ('years', 'Years'),
    ], string='Duration Unit', required=True, default='months')
    duration_value = fields.Integer(
        string='Duration Value', required=True, default=1,
        help='Number of days/months/years this plan lasts'
    )
    grace_period_days = fields.Integer(
        string='Grace Period (Days)', default=7,
        help='Extra days allowed after expiry before full lockout'
    )

    # ─── Pricing ─────────────────────────────────────────────────────────────
    currency_id = fields.Many2one(
        'res.currency', string='Currency',
        default=lambda self: self.env.company.currency_id
    )
    price = fields.Monetary(
        string='Price', currency_field='currency_id', required=True
    )
    setup_fee = fields.Monetary(
        string='Setup Fee', currency_field='currency_id', default=0.0
    )
    trial_days = fields.Integer(
        string='Trial Period (Days)', default=0,
        help='Free trial before billing begins; 0 = no trial'
    )

    # ─── Feature Limits ───────────────────────────────────────────────────────
    max_users = fields.Integer(
        string='Max Users', default=5,
        help='Maximum number of internal users allowed. 0 = unlimited'
    )
    max_storage_gb = fields.Float(
        string='Max Storage (GB)', default=10.0,
        help='Storage quota in GB. 0 = unlimited'
    )
    max_companies = fields.Integer(
        string='Max Companies', default=1,
        help='Number of sub-companies allowed. 0 = unlimited'
    )
    allowed_modules = fields.Many2many(
        'ir.module.module', string='Allowed Modules',
        help='Leave empty to allow all installed modules'
    )
    custom_domain = fields.Boolean(
        string='Custom Domain Allowed', default=False
    )
    api_access = fields.Boolean(
        string='API Access', default=False
    )
    priority_support = fields.Boolean(
        string='Priority Support', default=False
    )

    # ─── Payment / Billing ───────────────────────────────────────────────────
    auto_renewal = fields.Boolean(
        string='Auto-Renewal', default=False,
        help='Automatically renew this plan when it expires'
    )
    payment_gateway = fields.Selection([
        ('none', 'Manual / Invoice'),
        ('stripe', 'Stripe'),
        ('paypal', 'PayPal'),
    ], string='Default Payment Gateway', default='none')

    # ─── Computed ────────────────────────────────────────────────────────────
    subscription_count = fields.Integer(
        string='Subscriptions', compute='_compute_subscription_count'
    )
    active_subscription_count = fields.Integer(
        string='Active Subscriptions', compute='_compute_subscription_count'
    )
    monthly_revenue = fields.Monetary(
        string='Monthly Revenue', currency_field='currency_id',
        compute='_compute_revenue'
    )

    # ─── SQL Constraints ─────────────────────────────────────────────────────
    _sql_constraints = [
        ('plan_code_unique', 'UNIQUE(plan_code)', 'Plan Code must be unique.'),
        ('duration_positive', 'CHECK(duration_value > 0)',
         'Duration must be greater than zero.'),
        ('price_positive', 'CHECK(price >= 0)', 'Price cannot be negative.'),
    ]

    # ─── Compute Methods ──────────────────────────────────────────────────────
    def _compute_subscription_count(self):
        Subscription = self.env['saas.subscription']
        for rec in self:
            all_subs = Subscription.search([('type_id', '=', rec.id)])
            rec.subscription_count = len(all_subs)
            rec.active_subscription_count = len(
                all_subs.filtered(lambda s: s.state == 'active')
            )

    def _compute_revenue(self):
        Subscription = self.env['saas.subscription']
        for rec in self:
            active = Subscription.search([
                ('type_id', '=', rec.id),
                ('state', '=', 'active'),
            ])
            # Normalise to monthly revenue
            monthly = 0.0
            for sub in active:
                if rec.duration_unit == 'days':
                    months = rec.duration_value / 30.0 or 1
                elif rec.duration_unit == 'years':
                    months = rec.duration_value * 12
                else:
                    months = rec.duration_value or 1
                monthly += rec.price / months
            rec.monthly_revenue = monthly

    # ─── Onchange ────────────────────────────────────────────────────────────
    @api.onchange('plan_level')
    def _onchange_plan_level(self):
        defaults = {
            'basic':      {'max_users': 3,  'max_storage_gb': 5,   'price': 0},
            'silver':     {'max_users': 10, 'max_storage_gb': 25,  'price': 29},
            'gold':       {'max_users': 50, 'max_storage_gb': 100, 'price': 99},
            'diamond':    {'max_users': 200,'max_storage_gb': 500, 'price': 299},
            'enterprise': {'max_users': 0,  'max_storage_gb': 0,   'price': 999},
        }
        vals = defaults.get(self.plan_level, {})
        for k, v in vals.items():
            setattr(self, k, v)

    # ─── Actions ─────────────────────────────────────────────────────────────
    def action_view_subscriptions(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Subscriptions – %s') % self.name,
            'res_model': 'saas.subscription',
            'view_mode': 'list,form',
            'domain': [('type_id', '=', self.id)],
            'context': {'default_type_id': self.id},
        }
