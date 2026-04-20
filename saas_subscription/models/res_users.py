# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import AccessError


class ResUsers(models.Model):
    _inherit = 'res.users'

    is_saas_admin = fields.Boolean(
        string='SaaS Admin', default=False,
        help='SaaS Admins bypass all subscription restrictions.'
    )

    @api.model
    def _check_subscription_access(self):
        """
        Called at login / session validation.
        Raises AccessError if the user's company subscription is expired/locked
        and the user is not a SaaS admin or Odoo admin.
        """
        user = self.env.user
        # Odoo base admins are never blocked
        if user._is_admin():
            return True
        # SaaS admins bypass restrictions
        if user.is_saas_admin:
            return True

        company = user.company_id
        if company.subscription_locked:
            # Check whether a grace or trial sub still exists
            sub = self.env['saas.subscription'].sudo().search([
                ('company_id', '=', company.id),
                ('state', 'in', ('active', 'trial', 'grace')),
            ], limit=1)
            if not sub:
                raise AccessError(_(
                    'Your company subscription has expired or is not active. '
                    'Please contact your administrator to renew the subscription.'
                ))
        return True

    def _check_user_limit(self):
        """Verify the company hasn't exceeded its user quota."""
        company = self.env.company
        sub = self.env['saas.subscription'].sudo().search([
            ('company_id', '=', company.id),
            ('state', 'in', ('active', 'trial', 'grace')),
        ], limit=1)
        if not sub:
            return True
        if sub.max_users == 0:
            return True  # unlimited
        internal_users = self.env['res.users'].search_count([
            ('company_id', '=', company.id),
            ('share', '=', False),
            ('active', '=', True),
        ])
        return internal_users <= sub.max_users
