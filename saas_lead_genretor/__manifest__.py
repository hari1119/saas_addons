# -*- coding: utf-8 -*-
{
    'name': 'SaaS Lead Generator',
    'version': '19.0.1.0.0',
    'category': 'Sales/CRM',
    'summary': 'Import CRM leads from IndiaMart and other third-party providers.',
    'description': """
SaaS Lead Generator
===================
Configure third-party CRM lead providers and import leads into Odoo CRM.

Features:
---------
* CRM access groups for lead import users and integration managers
* Third Party Integration configuration under CRM Configuration
* Default IndiaMart configuration created on install
* Import Leads wizard with success, skipped, and failed result summary
* Duplicate protection using third-party external lead IDs
    """,
    'author': 'Hari',
    'website': 'https://www.yourcompany.com',
    'license': 'LGPL-3',
    'depends': [
        'crm',
        'utm',
    ],
    'external_dependencies': {
        'python': ['requests'],
    },
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/integration_data.xml',
        'views/crm_third_party_integration_views.xml',
        'views/crm_lead_views.xml',
        'wizards/crm_lead_import_wizard_views.xml',
        'views/menu_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
}
