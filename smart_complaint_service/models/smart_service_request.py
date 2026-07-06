# -*- coding: utf-8 -*-

from datetime import timedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class SmartServiceRequest(models.Model):
    _name = "smart.service.request"
    _description = "Smart Complaint and Service Request"
    _inherit = ["mail.thread", "mail.activity.mixin", "portal.mixin"]
    _order = "priority desc, sla_deadline asc, id desc"

    name = fields.Char(default="New", copy=False, readonly=True, tracking=True)
    subject = fields.Char(required=True, tracking=True)
    partner_id = fields.Many2one("res.partner", string="Customer", required=True, tracking=True)
    email = fields.Char()
    phone = fields.Char()
    request_type = fields.Selection(
        [
            ("complaint", "Complaint"),
            ("service", "Service Request"),
        ],
        required=True,
        default="service",
        tracking=True,
    )
    category_id = fields.Many2one("smart.service.category", required=True, tracking=True)
    priority = fields.Selection(
        [
            ("0", "Low"),
            ("1", "Normal"),
            ("2", "High"),
            ("3", "Critical"),
        ],
        default="1",
        required=True,
        tracking=True,
    )
    description = fields.Text(required=True)
    team_id = fields.Many2one("smart.service.team", tracking=True)
    assigned_user_id = fields.Many2one("res.users", string="Assigned To", tracking=True)
    manager_id = fields.Many2one("res.users", related="team_id.manager_id", store=True, readonly=True)
    state = fields.Selection(
        [
            ("new", "New"),
            ("triage", "Triage"),
            ("assigned", "Assigned"),
            ("in_progress", "In Progress"),
            ("waiting_customer", "Waiting Customer"),
            ("resolved", "Resolved"),
            ("closed", "Closed"),
            ("cancelled", "Cancelled"),
        ],
        default="new",
        tracking=True,
        required=True,
    )
    sla_policy_id = fields.Many2one("smart.service.sla", string="SLA Policy", readonly=True)
    sla_deadline = fields.Datetime(readonly=True, tracking=True)
    sla_status = fields.Selection(
        [
            ("on_track", "On Track"),
            ("warning", "Warning"),
            ("breached", "Breached"),
            ("no_sla", "No SLA"),
        ],
        default="on_track",
        tracking=True,
    )
    submitted_date = fields.Datetime(default=fields.Datetime.now, readonly=True)
    assigned_date = fields.Datetime(readonly=True)
    resolved_date = fields.Datetime(readonly=True)
    closed_date = fields.Datetime(readonly=True)
    resolution_note = fields.Text()
    customer_feedback = fields.Text()
    rating = fields.Selection(
        [
            ("1", "Poor"),
            ("2", "Average"),
            ("3", "Good"),
            ("4", "Excellent"),
        ],
        string="Customer Rating",
    )
    attachment_ids = fields.Many2many(
        "ir.attachment",
        "smart_service_request_attachment_rel",
        "request_id",
        "attachment_id",
        string="Attachments",
    )

    def _compute_access_url(self):
        super()._compute_access_url()
        for request in self:
            request.access_url = "/my/service-requests/%s" % request.id

    @api.onchange("category_id")
    def _onchange_category_id(self):
        for record in self:
            if record.category_id:
                record.request_type = record.category_id.request_type
                record.team_id = record.category_id.default_team_id

    @api.model
    def _next_request_name(self):
        sequence = self.env["ir.sequence"].sudo().search([
            ("code", "=", "smart.service.request"),
            ("company_id", "=", False),
        ], limit=1)
        if not sequence:
            sequence = self.env["ir.sequence"].sudo().create({
                "name": "Smart Service Request",
                "code": "smart.service.request",
                "prefix": "SR%(y)s",
                "padding": 5,
                "number_next": 1,
                "number_increment": 1,
                "company_id": False,
            })
        return sequence.next_by_id() or _("New")

    def _ensure_request_name(self):
        for record in self:
            if record.name in (False, None, "", "New", _("New")):
                record.sudo().name = record._next_request_name()

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name") in (False, None, "", "New", _("New")):
                vals["name"] = self._next_request_name()
            category = self.env["smart.service.category"].browse(vals.get("category_id"))
            if category:
                vals.setdefault("request_type", category.request_type)
                vals.setdefault("team_id", category.default_team_id.id)
            vals.setdefault("submitted_date", fields.Datetime.now())
        records = super().create(vals_list)
        records._apply_sla_policy()
        records._compute_sla_status()
        for record in records:
            record.message_subscribe(partner_ids=record.partner_id.ids)
        return records

    def write(self, vals):
        res = super().write(vals)
        if {"category_id", "priority", "submitted_date"} & set(vals):
            self._apply_sla_policy()
        if {"sla_deadline", "state"} & set(vals):
            self._compute_sla_status()
        return res

    def _find_sla_policy(self):
        self.ensure_one()
        domain = [
            ("active", "=", True),
            ("priority", "=", self.priority),
            "|",
            ("category_id", "=", self.category_id.id),
            ("category_id", "=", False),
        ]
        return self.env["smart.service.sla"].search(domain, order="category_id desc, resolution_hours", limit=1)

    def _apply_sla_policy(self):
        for record in self:
            policy = record._find_sla_policy()
            start = record.submitted_date or fields.Datetime.now()
            if policy:
                deadline = fields.Datetime.to_datetime(start) + timedelta(hours=policy.resolution_hours)
                record.sudo().write({
                    "sla_policy_id": policy.id,
                    "sla_deadline": deadline,
                    "sla_status": "on_track",
                })
            else:
                record.sudo().write({
                    "sla_policy_id": False,
                    "sla_deadline": fields.Datetime.to_datetime(start) + timedelta(hours=24),
                    "sla_status": "on_track",
                })

    def _compute_sla_status(self):
        now = fields.Datetime.now()
        for record in self:
            if record.state in ("resolved", "closed", "cancelled"):
                continue
            if not record.sla_deadline:
                record.sla_status = "no_sla"
                continue
            deadline = fields.Datetime.to_datetime(record.sla_deadline)
            submitted = fields.Datetime.to_datetime(record.submitted_date or record.create_date or now)
            total_seconds = max((deadline - submitted).total_seconds(), 1)
            remaining_seconds = (deadline - now).total_seconds()
            if remaining_seconds < 0:
                record.sla_status = "breached"
            elif remaining_seconds <= total_seconds * 0.2:
                record.sla_status = "warning"
            else:
                record.sla_status = "on_track"

    @api.model
    def _cron_update_sla_status(self):
        open_requests = self.search([("state", "not in", ["resolved", "closed", "cancelled"])])
        breached_before = open_requests.filtered(lambda request: request.sla_status != "breached")
        open_requests._compute_sla_status()
        breached_now = breached_before.filtered(lambda request: request.sla_status == "breached")
        for record in breached_now:
            manager = record.manager_id or record.team_id.manager_id
            if manager:
                record.activity_schedule(
                    "mail.mail_activity_data_todo",
                    user_id=manager.id,
                    summary=_("SLA breached"),
                    note=_("The SLA deadline has passed for %s.") % record.display_name,
                )

    def action_triage(self):
        self.write({"state": "triage"})

    def action_assign(self):
        for record in self:
            if not record.assigned_user_id:
                raise UserError(_("Please assign a user before moving this request to Assigned."))
        self.write({"state": "assigned", "assigned_date": fields.Datetime.now()})

    def action_start(self):
        self.write({"state": "in_progress"})

    def action_waiting_customer(self):
        self.write({"state": "waiting_customer"})

    def action_resolve(self):
        for record in self:
            if not record.resolution_note:
                raise UserError(_("Please add a resolution note before resolving."))
        self.write({"state": "resolved", "resolved_date": fields.Datetime.now()})

    def action_close(self):
        self.write({"state": "closed", "closed_date": fields.Datetime.now()})

    def action_reopen(self):
        self.write({
            "state": "in_progress",
            "resolved_date": False,
            "closed_date": False,
        })

    def action_cancel(self):
        self.write({"state": "cancelled"})
