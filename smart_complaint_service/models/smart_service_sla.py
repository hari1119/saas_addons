# -*- coding: utf-8 -*-

from odoo import fields, models


class SmartServiceSla(models.Model):
    _name = "smart.service.sla"
    _description = "Smart Service SLA Policy"
    _order = "priority desc, resolution_hours, name"

    name = fields.Char(required=True)
    category_id = fields.Many2one("smart.service.category", string="Category")
    priority = fields.Selection(
        [
            ("0", "Low"),
            ("1", "Normal"),
            ("2", "High"),
            ("3", "Critical"),
        ],
        required=True,
        default="1",
    )
    response_hours = fields.Float(default=4.0, required=True)
    resolution_hours = fields.Float(default=24.0, required=True)
    active = fields.Boolean(default=True)
