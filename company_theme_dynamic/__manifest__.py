# -*- coding: utf-8 -*-
{
    'name': 'Dynamic Company Theme',
    'version': '19.0.1.0.0',
    'summary': 'Per-company dynamic UI theming with animated transitions',
    'description': """
        Applies a fully customizable color theme to the Odoo interface
        based on the currently active company. Each company can define:
          - Primary / Secondary / Accent colors
          - Menu background & text colors
          - Button styles
          - Theme preset (Modern, Minimal, Bold, Glass)
          - Animated transitions between company switches
    """,
    'category': 'Customization/Themes',
    'author': 'Your Company',
    'website': 'https://yourcompany.com',
    'license': 'LGPL-3',
    'depends': ['base', 'web', 'base_setup'],
    'data': [
        'security/ir.model.access.csv',
        'views/res_company_theme_views.xml',
        'views/company_theme_templates.xml',
        'data/default_theme_data.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'company_theme_dynamic/static/src/css/company_theme.css',
            'company_theme_dynamic/static/src/css/theme_preview.css',
            'company_theme_dynamic/static/src/xml/company_theme_templates.xml',
            'company_theme_dynamic/static/src/js/company_theme_service.js',
            'company_theme_dynamic/static/src/js/company_theme_widget.js',
            'company_theme_dynamic/static/src/js/theme_preview_widget.js',
        ],
    },
    'images': ['static/description/banner.png'],
    'installable': True,
    'application': False,
    'auto_install': False,
}
