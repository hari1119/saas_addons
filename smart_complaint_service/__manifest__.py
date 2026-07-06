# -*- coding: utf-8 -*-
{
    "name": "Smart Complaint & Service Request",
    "version": "19.0.1.0.0",
    "category": "Services",
    "summary": "Hackathon-ready complaint and service request management with portal and SLA tracking.",
    "description": """
Smart Complaint & Service Request Management
============================================
Manage customer complaints and service requests with assignment, portal intake,
simple SLA tracking, feedback, and demo data.
    """,
    "author": "Hari",
    "website": "https://www.yourcompany.com",
    "license": "LGPL-3",
    "depends": [
        "base",
        "mail",
        "portal",
        "website",
    ],
    "data": [
        "security/security.xml",
        "security/ir.model.access.csv",
        "data/sequence_data.xml",
        "data/cron_data.xml",
        "views/smart_service_category_views.xml",
        "views/smart_service_team_views.xml",
        "views/smart_service_sla_views.xml",
        "views/smart_service_request_views.xml",
        "views/portal_templates.xml",
        "views/menu_views.xml",
    ],
    "demo": [
        "data/demo_data.xml",
    ],
    "installable": True,
    "auto_install": False,
    "application": True,
}
