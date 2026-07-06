# -*- coding: utf-8 -*-
from odoo import fields, models, _
from odoo.exceptions import AccessError


class CrmLeadImportWizard(models.TransientModel):
    _name = 'crm.lead.import.wizard'
    _description = 'CRM Lead Import Wizard'

    integration_id = fields.Many2one(
        'crm.third.party.integration',
        string='Third Party Integration',
        required=True,
        domain="[('active', '=', True)]",
    )
    start_date = fields.Date(required=True, default=fields.Date.today)
    end_date = fields.Date(required=True, default=fields.Date.today)
    state = fields.Selection(
        [('draft', 'Draft'), ('done', 'Done')],
        default='draft',
        required=True,
    )
    success_count = fields.Integer(readonly=True)
    failed_count = fields.Integer(readonly=True)
    skipped_count = fields.Integer(readonly=True)
    message = fields.Char(readonly=True)
    result_line_ids = fields.One2many(
        'crm.lead.import.result.line',
        'wizard_id',
        string='Results',
        readonly=True,
    )

    def action_import(self):
        self.ensure_one()
        if not self.env.user.has_group('saas_lead_genretor.group_saas_lead_generator_user'):
            raise AccessError(_('You are not allowed to import leads.'))

        result = self.integration_id.import_leads(self.start_date, self.end_date)
        self.result_line_ids.unlink()
        line_commands = [
            (0, 0, {
                'status': line.get('status'),
                'name': line.get('name'),
                'message': line.get('message'),
                'lead_id': line.get('lead_id'),
            })
            for line in result.get('lines', [])
        ]
        self.write({
            'state': 'done',
            'success_count': result.get('success', 0),
            'failed_count': result.get('failed', 0),
            'skipped_count': result.get('skipped', 0),
            'message': result.get('message'),
            'result_line_ids': line_commands,
        })
        return {
            'type': 'ir.actions.act_window',
            'name': _('Import Leads'),
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }


class CrmLeadImportResultLine(models.TransientModel):
    _name = 'crm.lead.import.result.line'
    _description = 'CRM Lead Import Result Line'

    wizard_id = fields.Many2one('crm.lead.import.wizard', required=True, ondelete='cascade')
    status = fields.Selection(
        [('success', 'Success'), ('failed', 'Failed'), ('skipped', 'Skipped')],
        required=True,
        default='success',
    )
    name = fields.Char(required=True)
    message = fields.Char()
    lead_id = fields.Many2one('crm.lead', string='Lead', readonly=True)
