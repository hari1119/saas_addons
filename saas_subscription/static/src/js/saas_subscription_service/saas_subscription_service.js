import { registry } from "@web/core/registry";
import { session } from "@web/session";
import { browser } from "@web/core/browser/browser";
import { deserializeDateTime, serializeDate, formatDate } from "@web/core/l10n/dates";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { ExpirationPanel } from "./expiration_panel";
import { cookie } from "@web/core/browser/cookie";
import { rpc } from "@web/core/network/rpc";

const { DateTime } = luxon;
import { Component, reactive, xml } from "@odoo/owl";

function daysUntil(datetime) {
    const duration = datetime.diff(DateTime.utc(), "days");
    return Math.round(duration.values.days);
}

export class SubscriptionManager {
    constructor(env, { orm, notification }) {
        this.env = env;
        this.orm = orm;
        this.notification = notification;
        if (session.expiration_date) {
            this.expirationDate = deserializeDateTime(session.expiration_date);
        } else {
            // If no date found, assume 1 month and hope for the best
            this.expirationDate = DateTime.utc().plus({ days: 30 });
        }
        this.expirationReason = session.expiration_reason;
        // Hack: we need to know if there is at least one app installed (except from App and
        // Settings). We use mail to do that, as it is a dependency of almost every addon. To
        // determine whether mail is installed or not, we check for the presence of the key
        // "storeData" in session_info, as it is added in mail.
        this.hasInstalledApps = "storeData" in session;
        // "user" or "admin"
        this.warningType = session.warning;
        this.lastRequestStatus = null;
        this.isWarningHidden = cookie.get("oe_instance_hide_panel");
    }

    get formattedExpirationDate() {
        return formatDate(this.expirationDate, { format: "DDD" });
    }

    get daysLeft() {
        return daysUntil(this.expirationDate);
    }

    get unregistered() {
        return ["trial", "demo", false].includes(this.expirationReason);
    }

    hideWarning() {
        // Hide warning for 24 hours.
        cookie.set("oe_instance_hide_panel", true, 24 * 60 * 60);
        this.isWarningHidden = true;
    }

    async buy() {
        const limitDate = serializeDate(DateTime.utc().minus({ days: 15 }));
        const args = [
            [
                ["share", "=", false],
                ["login_date", ">=", limitDate],
            ],
        ];
        const nbUsers = await this.orm.call("res.users", "search_count", args);
        browser.location = `https://www.odoo.com/odoo-enterprise/upgrade?num_users=${nbUsers}`;
    }


}