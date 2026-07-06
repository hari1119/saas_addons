# -*- coding: utf-8 -*-
{
    'name': 'Odoo Freelance Website',
    'version': '19.0.1.0.0',
    'category': 'Website/Website',
    'summary': 'Modern Odoo development service website with CRM lead capture.',
    'description': """
Modern Odoo development and implementation website
==================================================

Creates a polished public website page for Odoo Community implementation,
customization, migration, support, and integration services. The contact
form creates CRM leads directly from website visitors.
    """,
    'author': 'Hari',
    'website': 'https://www.yourcompany.com',
    'license': 'LGPL-3',
    'depends': [
        'website',
        'crm',
    ],
    'data': [
        'data/utm_source_data.xml',
        'views/website_templates.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'odoo_freelance_website/static/src/css/odoo_freelance_website.css',
            'odoo_freelance_website/static/src/js/odoo_freelance_website.js',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
}
