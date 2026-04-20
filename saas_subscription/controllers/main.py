# -*- coding: utf-8 -*-
import logging

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class SaasSubscriptionController(http.Controller):

    # ─── Lock-status JSON endpoint ────────────────────────────────────────────
    @http.route('/saas/subscription/lock_status', type='json', auth='user')
    def lock_status(self, **kwargs):
        """
        Returns whether the current user's active company is subscription-locked.
        Admins and is_saas_admin users are never reported as locked.
        """
        user = request.env.user

        # Never lock admins
        if user._is_admin() or user.is_saas_admin:
            return {'locked': False, 'reason': 'admin'}

        company = user.company_id

        if not company.subscription_locked:
            sub = request.env['saas.subscription'].sudo().search([
                ('company_id', '=', company.id),
                ('state', 'in', ('active', 'trial', 'grace')),
            ], limit=1, order='start_date desc')
            return {
                'locked': False,
                'company_name': company.name,
                'plan': sub.type_id.name if sub else None,
                'end_date': sub.end_date.strftime('%Y-%m-%d') if sub and sub.end_date else None,
                'state': sub.state if sub else None,
                'days_remaining': sub.days_remaining if sub else None,
            }

        # Locked — gather info for the UI
        last_sub = request.env['saas.subscription'].sudo().search([
            ('company_id', '=', company.id),
        ], limit=1, order='end_date desc')

        return {
            'locked': True,
            'company_name': company.name,
            'plan': last_sub.type_id.name if last_sub else None,
            'end_date': (last_sub.end_date.strftime('%Y-%m-%d')
                         if last_sub and last_sub.end_date else None),
            'state': last_sub.state if last_sub else 'none',
            'reason': 'subscription_expired',
            'support_email': request.env['ir.config_parameter'].sudo().get_param(
                'saas_subscription.support_email', 'support@yourcompany.com'
            ),
        }

    # ─── Portal status page ───────────────────────────────────────────────────
    @http.route('/saas/subscription/status', type='http', auth='user', website=True)
    def subscription_status(self, **kwargs):
        company = request.env.company
        sub = request.env['saas.subscription'].sudo().search([
            ('company_id', '=', company.id),
            ('state', 'in', ('active', 'trial', 'grace', 'expired')),
        ], limit=1, order='start_date desc')
        return request.render('saas_subscription.portal_subscription_status', {
            'subscription': sub,
            'company': company,
        })

    # ─── Stripe Webhook ───────────────────────────────────────────────────────
    @http.route('/saas/webhook/stripe', type='json', auth='public', csrf=False)
    def stripe_webhook(self, **kwargs):
        payload = request.jsonrequest
        event_type = payload.get('type', '')
        _logger.info('Stripe webhook received: %s', event_type)
        if event_type == 'invoice.payment_succeeded':
            data = payload.get('data', {}).get('object', {})
            sub_ref = data.get('metadata', {}).get('subscription_reference')
            if sub_ref:
                sub = request.env['saas.subscription'].sudo().search([
                    ('reference', '=', sub_ref)
                ], limit=1)
                if sub:
                    sub.action_renew()
        elif event_type == 'invoice.payment_failed':
            _logger.warning('Stripe payment failed for: %s', payload)
        return {'status': 'ok'}

    # ─── PayPal Webhook ───────────────────────────────────────────────────────
    @http.route('/saas/webhook/paypal', type='json', auth='public', csrf=False)
    def paypal_webhook(self, **kwargs):
        payload = request.jsonrequest
        event_type = payload.get('event_type', '')
        if event_type == 'PAYMENT.SALE.COMPLETED':
            sub_ref = payload.get('resource', {}).get('custom', '')
            if sub_ref:
                sub = request.env['saas.subscription'].sudo().search([
                    ('reference', '=', sub_ref)
                ], limit=1)
                if sub:
                    sub.action_renew()
        return {'status': 'ok'}

    # ─── Dashboard JSON API ───────────────────────────────────────────────────
    @http.route('/saas/dashboard/data', type='json', auth='user')
    def dashboard_data(self, **kwargs):
        if not request.env.user.has_group('saas_subscription.group_saas_manager'):
            return {'error': 'Access denied'}
        return request.env['saas.subscription'].get_dashboard_data()
