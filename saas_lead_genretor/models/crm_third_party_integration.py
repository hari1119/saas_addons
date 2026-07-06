# -*- coding: utf-8 -*-
import logging

import requests

from markupsafe import Markup, escape

from odoo import fields, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools import plaintext2html

_logger = logging.getLogger(__name__)


class CrmThirdPartyIntegration(models.Model):
    _name = 'crm.third.party.integration'
    _description = 'CRM Third Party Integration'
    _order = 'sequence, name'

    name = fields.Char(required=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    source = fields.Selection(
        [('indiamart', 'IndiaMart')],
        string='Source',
        required=True,
        default='indiamart',
    )
    url = fields.Char(string='URL', required=True)
    external_user_id = fields.Char(string='User ID')
    profile_id = fields.Char(string='Profile ID')
    key = fields.Char(string='Key', copy=False)
    company_id = fields.Many2one(
        'res.company',
        default=lambda self: self.env.company,
        required=True,
    )
    team_id = fields.Many2one('crm.team', string='Sales Team')
    salesperson_id = fields.Many2one('res.users', string='Salesperson')
    utm_source_id = fields.Many2one('utm.source', string='Lead Source')
    last_import_date = fields.Datetime(readonly=True, copy=False)

    def action_open_import_wizard(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Import Leads'),
            'res_model': 'crm.lead.import.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_integration_id': self.id,
            },
        }

    def import_leads(self, start_date, end_date):
        self.ensure_one()
        if self.source != 'indiamart':
            raise UserError(_('The selected source is not supported yet.'))
        if not self.key:
            raise ValidationError(_('Please configure the IndiaMart key before importing leads.'))
        if not self.url:
            raise ValidationError(_('Please configure the IndiaMart URL before importing leads.'))
        if start_date > end_date:
            raise ValidationError(_('Start Date cannot be after End Date.'))

        payload = self._fetch_indiamart_leads(start_date, end_date)
        leads = self._extract_indiamart_items(payload)
        message = self._extract_response_message(payload)

        result = {
            'success': 0,
            'failed': 0,
            'skipped': 0,
            'lines': [],
            'message': message,
        }
        if not leads and message:
            result['failed'] = 1
            result['lines'].append({
                'status': 'failed',
                'name': _('IndiaMart Response'),
                'message': message,
            })
            return result

        for item in leads:
            try:
                lead = self._create_indiamart_lead(item)
            except Exception as exc:
                _logger.exception('IndiaMart lead import failed.')
                result['failed'] += 1
                result['lines'].append({
                    'status': 'failed',
                    'name': self._get_value(item, 'SENDER_NAME', 'SUBJECT', 'QUERY_PRODUCT_NAME') or _('Unknown Lead'),
                    'message': str(exc),
                })
                continue

            if lead:
                result['success'] += 1
                result['lines'].append({
                    'status': 'success',
                    'name': lead.name,
                    'message': _('Lead imported successfully.'),
                    'lead_id': lead.id,
                })
            else:
                result['skipped'] += 1
                result['lines'].append({
                    'status': 'skipped',
                    'name': self._get_value(item, 'SUBJECT', 'QUERY_PRODUCT_NAME', 'SENDER_NAME') or _('Duplicate Lead'),
                    'message': _('Lead skipped because it already exists.'),
                })

        self.last_import_date = fields.Datetime.now()
        return result

    def _fetch_indiamart_leads(self, start_date, end_date):
        params = {
            'glusr_crm_key': self.key,
            'start_time': start_date.strftime('%d-%b-%Y'),
            'end_time': end_date.strftime('%d-%b-%Y'),
        }
        if self.external_user_id:
            params['user_id'] = self.external_user_id
        if self.profile_id:
            params['profile_id'] = self.profile_id

        try:
            response = requests.get(self.url, params=params, timeout=60)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as exc:
            raise UserError(_('Could not connect to IndiaMart: %s') % exc) from exc
        except ValueError as exc:
            raise UserError(_('IndiaMart returned an invalid JSON response.')) from exc

    def _extract_indiamart_items(self, payload):
        if isinstance(payload, list):
            return payload
        if not isinstance(payload, dict):
            return []

        for key in ('RESPONSE', 'response', 'DATA', 'data', 'LEADS', 'leads', 'ENQUIRY_LIST', 'enquiries'):
            value = payload.get(key)
            if isinstance(value, list):
                return value
            if isinstance(value, dict):
                nested = self._extract_indiamart_items(value)
                if nested:
                    return nested
        return []

    def _extract_response_message(self, payload):
        if not isinstance(payload, dict):
            return ''
        for key in ('MESSAGE', 'message', 'ERROR_MESSAGE', 'error_message', 'REASON', 'reason'):
            if payload.get(key):
                return str(payload[key])
        status = payload.get('STATUS') or payload.get('status')
        code = payload.get('CODE') or payload.get('code')
        if status and str(status).lower() not in ('success', 'ok', '200'):
            return '%s%s' % (status, ' (%s)' % code if code else '')
        for key in ('RESPONSE', 'response', 'DATA', 'data'):
            value = payload.get(key)
            if isinstance(value, dict):
                message = self._extract_response_message(value)
                if message:
                    return message
        return ''

    def _create_indiamart_lead(self, item):
        external_id = self._get_value(item, 'UNIQUE_QUERY_ID', 'QUERY_ID', 'QUERYID', 'ENQUIRY_ID')
        if external_id:
            existing = self.env['crm.lead'].search([
                ('third_party_source', '=', self.source),
                ('third_party_external_id', '=', external_id),
                ('company_id', '=', self.company_id.id),
            ], limit=1)
            if existing:
                return False

        lead_vals = self._prepare_indiamart_lead_vals(item, external_id)
        return self.env['crm.lead'].create(lead_vals)

    def _prepare_indiamart_lead_vals(self, item, external_id=False):
        sender_name = self._get_value(item, 'SENDER_NAME', 'CONTACT_PERSON', 'NAME')
        subject = self._get_value(item, 'SUBJECT', 'QUERY_SUBJECT', 'QUERY_PRODUCT_NAME')
        product = self._get_value(item, 'QUERY_PRODUCT_NAME', 'PRODUCT_NAME', 'PRODUCT')
        company = self._get_value(item, 'SENDER_COMPANY', 'COMPANY_NAME', 'ORGANIZATION')
        mobile = self._get_value(item, 'SENDER_MOBILE', 'MOBILE', 'PHONE')
        email = self._get_value(item, 'SENDER_EMAIL', 'EMAIL')
        query_message = self._get_value(item, 'QUERY_MESSAGE', 'MESSAGE', 'DESCRIPTION')

        title = subject or product or sender_name or _('IndiaMart Lead')
        description = self._build_indiamart_description(item, query_message)
        country = self._find_country(
            self._get_value(item, 'SENDER_COUNTRY_ISO', 'COUNTRY_ISO'),
            self._get_value(item, 'SENDER_COUNTRY', 'COUNTRY'),
        )

        vals = {
            'name': title,
            'type': 'lead',
            'contact_name': sender_name,
            'partner_name': company,
            'email_from': email,
            'phone': mobile,
            'mobile': mobile,
            'street': self._get_value(item, 'SENDER_ADDRESS', 'ADDRESS'),
            'city': self._get_value(item, 'SENDER_CITY', 'CITY'),
            'zip': self._get_value(item, 'SENDER_PINCODE', 'PINCODE', 'ZIP'),
            'description': description,
            'company_id': self.company_id.id,
            'third_party_integration_id': self.id,
            'third_party_source': self.source,
            'third_party_external_id': external_id,
        }
        if country:
            vals['country_id'] = country.id
        if self.team_id:
            vals['team_id'] = self.team_id.id
        if self.salesperson_id:
            vals['user_id'] = self.salesperson_id.id
        if self.utm_source_id:
            vals['source_id'] = self.utm_source_id.id
        return vals

    def _build_indiamart_description(self, item, query_message):
        safe_message = plaintext2html(query_message or _('Lead imported from IndiaMart.'))
        rows = [
            (_('Product'), self._get_value(item, 'QUERY_PRODUCT_NAME', 'PRODUCT_NAME')),
            (_('Query Time'), self._get_value(item, 'QUERY_TIME', 'DATE_TIME', 'ENQUIRY_DATE')),
            (_('Query Type'), self._get_value(item, 'QUERY_TYPE')),
            (_('Company'), self._get_value(item, 'SENDER_COMPANY', 'COMPANY_NAME')),
            (_('Mobile'), self._get_value(item, 'SENDER_MOBILE', 'MOBILE', 'PHONE')),
            (_('Email'), self._get_value(item, 'SENDER_EMAIL', 'EMAIL')),
            (_('Address'), self._get_value(item, 'SENDER_ADDRESS', 'ADDRESS')),
            (_('City'), self._get_value(item, 'SENDER_CITY', 'CITY')),
            (_('State'), self._get_value(item, 'SENDER_STATE', 'STATE')),
            (_('Country'), self._get_value(item, 'SENDER_COUNTRY', 'COUNTRY')),
            (_('IndiaMart Lead ID'), self._get_value(item, 'UNIQUE_QUERY_ID', 'QUERY_ID', 'QUERYID', 'ENQUIRY_ID')),
        ]
        detail_items = Markup('').join(
            Markup('<li><strong>{}</strong>: {}</li>').format(escape(label), escape(value))
            for label, value in rows
            if value
        )
        details = Markup('<h3>IndiaMart enquiry details</h3><ul>{}</ul>').format(detail_items)
        return str(Markup(safe_message) + details)

    def _find_country(self, iso_code=False, country_name=False):
        Country = self.env['res.country']
        if iso_code:
            country = Country.search([('code', '=', iso_code)], limit=1)
            if country:
                return country
        if country_name:
            return Country.search([('name', '=ilike', country_name)], limit=1)
        return Country

    def _get_value(self, item, *keys):
        if not isinstance(item, dict):
            return ''
        for key in keys:
            value = item.get(key)
            if value not in (None, False, ''):
                return str(value).strip()
        return ''
