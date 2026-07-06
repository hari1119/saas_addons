# -*- coding: utf-8 -*-
from odoo import fields, models


class CrmLead(models.Model):
    _inherit = 'crm.lead'

    third_party_integration_id = fields.Many2one(
        'crm.third.party.integration',
        string='Third Party Integration',
        readonly=True,
        copy=False,
        index='btree_not_null',
    )
    third_party_source = fields.Char(
        string='Third Party Source',
        readonly=True,
        copy=False,
        index='btree_not_null',
    )
    third_party_external_id = fields.Char(
        string='Third Party Lead ID',
        readonly=True,
        copy=False,
        index='btree_not_null',
    )
