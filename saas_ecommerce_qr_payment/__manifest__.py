# -*- coding: utf-8 -*-
{
    'name': 'SaaS eCommerce QR Payment Proof',
    'version': '19.0.1.0.0',
    'category': 'Website/eCommerce',
    'summary': 'Small-business eCommerce with QR payment proof verification.',
    'description': """
SaaS eCommerce QR Payment Proof
===============================

Adds a lightweight SaaS eCommerce workflow for small-business shops:

* Website/domain-based eCommerce project setup
* Website/domain-specific QR payment configuration
* QR code and payment instructions on the eCommerce payment page
* Customer screenshot upload after payment
* Back-office payment verification and sale order confirmation
* Pending payment proof menu for internal users
    """,
    'author': 'Hari',
    'website': 'https://www.linkedin.com/in/hari-prasath-b4266718b/',
    'license': 'LGPL-3',
    'maintainer': 'Hari',
    'depends': [
        'website_sale',
        'sale_management',
    ],
    'data': [
        'views/res_config_settings_views.xml',
        'views/sale_order_views.xml',
        'views/checkout_address_templates.xml',
        'views/website_sale_templates.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
