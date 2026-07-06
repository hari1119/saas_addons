# -*- coding: utf-8 -*-

from odoo import fields, models


class SmartServiceCategory(models.Model):
    _name = "smart.service.category"
    _description = "Smart Service Category"
    _order = "request_type, sequence, name"

    name = fields.Char(required=True)
    sequence = fields.Integer(default=10)
    request_type = fields.Selection(
        [
            ("complaint", "Complaint"),
            ("service", "Service Request"),
        ],
        required=True,
        default="service",
    )
    default_team_id = fields.Many2one("smart.service.team", string="Default Team")
    active = fields.Boolean(default=True)
