# -*- coding: utf-8 -*-

from odoo import fields, models


class SmartServiceTeam(models.Model):
    _name = "smart.service.team"
    _description = "Smart Service Team"
    _order = "sequence, name"

    name = fields.Char(required=True)
    sequence = fields.Integer(default=10)
    manager_id = fields.Many2one("res.users", string="Manager")
    member_ids = fields.Many2many(
        "res.users",
        "smart_service_team_user_rel",
        "team_id",
        "user_id",
        string="Members",
    )
    active = fields.Boolean(default=True)
