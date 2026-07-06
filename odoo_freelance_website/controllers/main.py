# -*- coding: utf-8 -*-

from markupsafe import Markup, escape

from odoo import http, tools
from odoo.http import request
from odoo.tools import plaintext2html


class OdooFreelanceWebsite(http.Controller):

    @http.route('/odoo-services/lead', type='http', auth='public', website=True, methods=['POST'])
    def create_odoo_service_lead(self, **post):
        name = (post.get('contact_name') or '').strip()
        email = (post.get('email_from') or '').strip()
        project_type = (post.get('project_type') or 'Odoo Consultation').strip()

        if not name or not email or not tools.email_normalize(email):
            return request.redirect('/odoo-services?lead_error=1#connect')

        company = (post.get('partner_name') or '').strip()
        phone = (post.get('phone') or '').strip()
        message = (post.get('description') or '').strip()

        detail_rows = [
            ('Project type', project_type),
            ('Odoo version', post.get('odoo_version')),
            ('Budget range', post.get('budget_range')),
            ('Timeline', post.get('timeline')),
            ('Company', company),
            ('Submitted from', request.httprequest.referrer or request.httprequest.host_url),
        ]
        detail_items = Markup('').join(
            Markup('<li><strong>{}</strong>: {}</li>').format(escape(label), escape(value))
            for label, value in detail_rows
            if value
        )
        details = Markup('<h3>Website enquiry details</h3><ul>{}</ul>').format(detail_items)
        description = plaintext2html(message or 'The visitor requested a consultation from the Odoo services website.') + details

        source = request.env.ref('odoo_freelance_website.utm_source_odoo_services_website', raise_if_not_found=False)
        crm_team = request.env['crm.team'].sudo().search([], limit=1)
        lead_vals = {
            'name': 'Website enquiry: %s' % project_type,
            'type': 'lead',
            'contact_name': name,
            'email_from': email,
            'phone': phone,
            'partner_name': company,
            'description': description,
            'company_id': request.website.company_id.id,
        }
        if source:
            lead_vals['source_id'] = source.id
        if crm_team:
            lead_vals['team_id'] = crm_team.id

        lead = request.env['crm.lead'].sudo().create(lead_vals)
        request.session['odoo_freelance_lead_id'] = lead.id
        return request.redirect('/odoo-services/thank-you')
