# -*- coding: utf-8 -*-
import json
import logging

from odoo import http, _
from odoo.http import request

_logger = logging.getLogger(__name__)


class SaasSubscriptionController(http.Controller):

    # ─── Portal: Subscription Status Page ─────────────────────────────────
    @http.route('/saas/subscription/status', type='http',
                auth='user', website=True)
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

    # ─── Stripe Webhook ───────────────────────────────────────────────────
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
                    _logger.info('Auto-renewed subscription %s via Stripe', sub_ref)

        elif event_type == 'invoice.payment_failed':
            data = payload.get('data', {}).get('object', {})
            sub_ref = data.get('metadata', {}).get('subscription_reference')
            if sub_ref:
                _logger.warning('Stripe payment failed for subscription %s', sub_ref)

        return {'status': 'ok'}

    # ─── PayPal Webhook ───────────────────────────────────────────────────
    @http.route('/saas/webhook/paypal', type='json', auth='public', csrf=False)
    def paypal_webhook(self, **kwargs):
        payload = request.jsonrequest
        event_type = payload.get('event_type', '')
        _logger.info('PayPal webhook received: %s', event_type)

        if event_type == 'PAYMENT.SALE.COMPLETED':
            resource = payload.get('resource', {})
            sub_ref = resource.get('custom', '')
            if sub_ref:
                sub = request.env['saas.subscription'].sudo().search([
                    ('reference', '=', sub_ref)
                ], limit=1)
                if sub:
                    sub.action_renew()
                    _logger.info('Auto-renewed subscription %s via PayPal', sub_ref)
        return {'status': 'ok'}

    # ─── Dashboard JSON API ───────────────────────────────────────────────
    @http.route('/saas/dashboard/data', type='json', auth='user')
    def dashboard_data(self, **kwargs):
        if not request.env.user.has_group('saas_subscription.group_saas_manager'):
            return {'error': 'Access denied'}
        return request.env['saas.subscription'].get_dashboard_data()
