# -*- coding: utf-8 -*-
{
    'name': 'SaaS Subscription Manager',
    'version': '19.0.1.0.0',
    'category': 'Administration',
    'summary': 'Manage SaaS subscriptions, restrict company access based on plan duration and type.',
    'description': """
SaaS Subscription Manager
==========================
A comprehensive subscription management module for Odoo 19 SaaS deployments.

Features:
---------
* Subscription types (Gold, Silver, Diamond) with pricing and feature limits
* Automatic access lock after subscription expiry
* Grace period configuration
* Email notifications for upcoming expiry
* Dashboard analytics and revenue tracking
* Company activity logs
* Optional Stripe/PayPal payment integration hooks
* Full unit test suite
    """,
    'author': 'Hari',
    'website': 'https://www.yourcompany.com',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'mail',
        'web',
        'account',
        'portal',
    ],
    'data': [
        # Security
        'security/security.xml',
        'security/ir.model.access.csv',
        # Data
        'data/sequence_data.xml',
        'data/email_templates.xml',
        'data/cron_jobs.xml',
        # Views
        'views/subscription_type_views.xml',
        'views/subscription_views.xml',
        'views/res_company_views.xml',
        'views/dashboard_views.xml',
        'views/report_views.xml',
        'views/menu_views.xml',
        # Wizards
        'wizards/subscription_renewal_wizard_views.xml',
        # Reports
        'report/subscription_report.xml',
    ],
    'demo': [
        'data/demo_data.xml',
    ],
    'assets': {
        'web.assets_backend': [
            # Dashboard
            'saas_subscription/static/src/css/dashboard.css',
            'saas_subscription/static/src/xml/dashboard.xml',
            'saas_subscription/static/src/js/dashboard.js',
            # Subscription lock screen — MUST load at boot, before any view
            'saas_subscription/static/src/css/subscription_lock.css',
            'saas_subscription/static/src/xml/subscription_lock.xml',
            'saas_subscription/static/src/js/subscription_lock.js',
        ],
    },
    'images': ['static/description/icon.png'],
    'installable': True,
    'auto_install': False,
    'application': True,
}
