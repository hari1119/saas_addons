# -*- coding: utf-8 -*-

import base64

from odoo import _, http
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager
from odoo.http import request


class SmartServicePortal(CustomerPortal):

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        if "service_request_count" in counters:
            values["service_request_count"] = request.env["smart.service.request"].search_count(
                self._get_service_request_domain()
            )
        return values

    def _get_service_request_domain(self):
        return [("partner_id", "child_of", request.env.user.partner_id.commercial_partner_id.id)]

    def _get_service_request_from_tracking_number(self, tracking_number):
        tracking_number = (tracking_number or "").strip()
        if not tracking_number:
            return request.env["smart.service.request"]
        domain = self._get_service_request_domain() + [("name", "=ilike", tracking_number)]
        return request.env["smart.service.request"].sudo().search(domain, limit=1)

    @http.route(["/my/service-requests", "/my/service-requests/page/<int:page>"], type="http", auth="user", website=True)
    def portal_service_requests(self, page=1, sortby="date", filterby="open", **kw):
        values = self._prepare_portal_layout_values()
        request_obj = request.env["smart.service.request"]
        domain = self._get_service_request_domain()

        if filterby == "closed":
            domain += [("state", "in", ["resolved", "closed", "cancelled"])]
        elif filterby == "breached":
            domain += [("sla_status", "=", "breached")]
        else:
            domain += [("state", "not in", ["closed", "cancelled"])]

        searchbar_sortings = {
            "date": {"label": _("Newest"), "order": "submitted_date desc, id desc"},
            "priority": {"label": _("Priority"), "order": "priority desc, submitted_date desc"},
            "deadline": {"label": _("SLA Deadline"), "order": "sla_deadline asc, submitted_date desc"},
        }
        order = searchbar_sortings.get(sortby, searchbar_sortings["date"])["order"]
        request_count = request_obj.search_count(domain)
        pager = portal_pager(
            url="/my/service-requests",
            total=request_count,
            page=page,
            step=self._items_per_page,
            url_args={"sortby": sortby, "filterby": filterby},
        )
        requests = request_obj.search(domain, order=order, limit=self._items_per_page, offset=pager["offset"])

        values.update({
            "requests": requests,
            "page_name": "service_requests",
            "pager": pager,
            "default_url": "/my/service-requests",
            "sortby": sortby,
            "filterby": filterby,
            "searchbar_sortings": searchbar_sortings,
        })
        return request.render("smart_complaint_service.portal_service_request_list", values)

    @http.route("/my/service-requests/track", type="http", auth="user", website=True, methods=["GET", "POST"], csrf=True)
    def portal_service_request_track(self, **post):
        tracking_number = (post.get("tracking_number") or "").strip()
        service_request = self._get_service_request_from_tracking_number(tracking_number)
        service_request._ensure_request_name()
        return request.render("smart_complaint_service.portal_service_request_track", {
            "service_request": service_request,
            "tracking_number": tracking_number,
            "not_found": bool(tracking_number and not service_request),
            "page_name": "service_requests",
        })

    @http.route("/my/service-requests/create", type="http", auth="user", website=True, methods=["GET", "POST"], csrf=True)
    def portal_service_request_create(self, **post):
        categories = request.env["smart.service.category"].sudo().search([("active", "=", True)], order="request_type, name")
        if request.httprequest.method == "POST":
            try:
                category_id = int(post.get("category_id") or 0)
            except ValueError:
                category_id = 0
            category = request.env["smart.service.category"].sudo().browse(category_id).exists()
            if not category:
                return request.redirect("/my/service-requests/create?error=category")

            customer = request.env.user.partner_id.commercial_partner_id
            values = {
                "subject": post.get("subject", "").strip(),
                "partner_id": customer.id,
                "email": post.get("email") or customer.email,
                "phone": post.get("phone") or customer.phone,
                "request_type": category.request_type,
                "category_id": category.id,
                "priority": post.get("priority") or "1",
                "description": post.get("description", "").strip(),
            }
            service_request = request.env["smart.service.request"].sudo().create(values)

            upload = request.httprequest.files.get("attachment")
            if upload and upload.filename:
                attachment = request.env["ir.attachment"].sudo().create({
                    "name": upload.filename,
                    "datas": base64.b64encode(upload.read()),
                    "res_model": "smart.service.request",
                    "res_id": service_request.id,
                    "type": "binary",
                })
                service_request.attachment_ids = [(4, attachment.id)]

            service_request.message_post(body=_("Request submitted from the customer portal."))
            return request.redirect("/my/service-requests/%s/submitted" % service_request.id)

        return request.render("smart_complaint_service.portal_service_request_create", {
            "categories": categories,
            "page_name": "service_requests",
            "error": post.get("error"),
        })

    @http.route("/my/service-requests/<int:request_id>/submitted", type="http", auth="user", website=True)
    def portal_service_request_submitted(self, request_id, access_token=None, **kw):
        try:
            service_request = self._document_check_access("smart.service.request", request_id, access_token=access_token)
        except Exception:
            return request.redirect("/my")
        service_request._ensure_request_name()
        return request.render("smart_complaint_service.portal_service_request_submitted", {
            "service_request": service_request,
            "page_name": "service_requests",
        })

    @http.route("/my/service-requests/<int:request_id>", type="http", auth="user", website=True)
    def portal_service_request_detail(self, request_id, access_token=None, **kw):
        try:
            service_request = self._document_check_access("smart.service.request", request_id, access_token=access_token)
        except Exception:
            return request.redirect("/my")
        service_request._ensure_request_name()
        messages = service_request.sudo().message_ids.filtered(
            lambda message: message.message_type == "comment"
        ).sorted("date")
        return request.render("smart_complaint_service.portal_service_request_detail", {
            "service_request": service_request,
            "messages": messages,
            "page_name": "service_requests",
        })

    @http.route("/my/service-requests/<int:request_id>/message", type="http", auth="user", website=True, methods=["POST"], csrf=True)
    def portal_service_request_message(self, request_id, access_token=None, **post):
        service_request = self._document_check_access("smart.service.request", request_id, access_token=access_token)
        message = post.get("message")
        if message:
            service_request.sudo().message_post(
                body=message,
                author_id=request.env.user.partner_id.id,
                message_type="comment",
                subtype_xmlid="mail.mt_comment",
            )
        return request.redirect(service_request.access_url)

    @http.route("/my/service-requests/<int:request_id>/reopen", type="http", auth="user", website=True, methods=["POST"], csrf=True)
    def portal_service_request_reopen(self, request_id, access_token=None, **post):
        service_request = self._document_check_access("smart.service.request", request_id, access_token=access_token)
        if service_request.state in ("resolved", "closed"):
            service_request.sudo().action_reopen()
            service_request.sudo().message_post(
                body=_("Customer reopened this request from the portal."),
                author_id=request.env.user.partner_id.id,
            )
        return request.redirect(service_request.access_url)

    @http.route("/my/service-requests/<int:request_id>/feedback", type="http", auth="user", website=True, methods=["POST"], csrf=True)
    def portal_service_request_feedback(self, request_id, access_token=None, **post):
        service_request = self._document_check_access("smart.service.request", request_id, access_token=access_token)
        service_request.sudo().write({
            "rating": post.get("rating"),
            "customer_feedback": post.get("customer_feedback"),
        })
        service_request.sudo().message_post(
            body=_("Customer submitted feedback from the portal."),
            author_id=request.env.user.partner_id.id,
        )
        return request.redirect(service_request.access_url)
