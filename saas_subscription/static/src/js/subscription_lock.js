/** @odoo-module **/

/**
 * SaaS Subscription Lock Screen
 * ==============================
 * Registers a global OWL component via the `main_components` registry.
 * It sits at z-index 10000, covers the entire viewport, and intercepts
 * ALL pointer/keyboard events — making the UI completely non-interactive
 * when the company's subscription_locked flag is True on the server.
 *
 * Flow:
 *   1. On mount  → call /saas/subscription/lock_status
 *   2. If locked → render full-screen overlay (nothing underneath is clickable)
 *   3. Poll every 60 s (in case admin renews remotely)
 *   4. Also re-check on window focus and on Odoo company switch events
 */

import { Component, onMounted, onWillUnmount, useState, useRef } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { browser } from "@web/core/browser/browser";
import { rpc } from "@web/core/network/rpc";

const POLL_INTERVAL_MS = 60_000; // re-check every 60 seconds

class SubscriptionLockScreen extends Component {
    static template = "saas_subscription.SubscriptionLockScreen";
    static props = {};

    setup() {
        this.rpc = rpc;
        this.orm = useService("orm");

        this.state = useState({
            /** null = still loading (show nothing), true = locked, false = open */
            locked: null,
            loading: true,
            companyName: "",
            plan: "",
            endDate: "",
            subState: "",
            supportEmail: "support@yourcompany.com",
            retryIn: 60,
        });

        this._pollTimer = null;
        this._countdownTimer = null;
        this._boundOnFocus = this._onWindowFocus.bind(this);
        this._boundOnCompanyChange = this._onCompanyChange.bind(this);

        onMounted(() => {
            this._checkLock();
            this._startPolling();
            browser.addEventListener("focus", this._boundOnFocus);
            // Listen for Odoo's internal company-switch bus event if available
            window.addEventListener(
                "saas_company_changed",
                this._boundOnCompanyChange
            );
        });

        onWillUnmount(() => {
            this._stopPolling();
            browser.removeEventListener("focus", this._boundOnFocus);
            window.removeEventListener(
                "saas_company_changed",
                this._boundOnCompanyChange
            );
        });
    }

    // ──────────────────────────────────────────────────────────────────────────
    // Server communication
    // ──────────────────────────────────────────────────────────────────────────

    async _checkLock() {
        try {
            const result = await this.rpc("/saas/subscription/lock_status", {});
            this.state.locked = !!result.locked;
            this.state.companyName = result.company_name || "";
            this.state.plan = result.plan || "";
            this.state.endDate = result.end_date || "";
            this.state.subState = result.state || "";
            this.state.supportEmail =
                result.support_email || "support@yourcompany.com";
        } catch (e) {
            // Network error — keep whatever state we have; don't unlock on error
            console.warn("[SaaS Lock] Could not reach lock_status endpoint:", e);
        } finally {
            this.state.loading = false;
        }
    }

    // ──────────────────────────────────────────────────────────────────────────
    // Polling
    // ──────────────────────────────────────────────────────────────────────────

    _startPolling() {
        this._pollTimer = setInterval(() => this._checkLock(), POLL_INTERVAL_MS);
        // Countdown display
        this.state.retryIn = POLL_INTERVAL_MS / 1000;
        this._countdownTimer = setInterval(() => {
            this.state.retryIn = Math.max(0, this.state.retryIn - 1);
            if (this.state.retryIn === 0) {
                this.state.retryIn = POLL_INTERVAL_MS / 1000;
            }
        }, 1000);
    }

    _stopPolling() {
        clearInterval(this._pollTimer);
        clearInterval(this._countdownTimer);
    }

    _onWindowFocus() {
        // Re-check immediately when user switches back to this tab
        this._checkLock();
    }

    _onCompanyChange() {
        this.state.loading = true;
        this._checkLock();
    }

    // ──────────────────────────────────────────────────────────────────────────
    // UI helpers
    // ──────────────────────────────────────────────────────────────────────────

    get stateLabel() {
        const labels = {
            expired: "Expired",
            cancelled: "Cancelled",
            grace: "Grace Period Ended",
            none: "No Active Subscription",
        };
        return labels[this.state.subState] || "Inactive";
    }

    onContactSupport() {
        window.location.href = `mailto:${this.state.supportEmail}?subject=Subscription%20Renewal%20Request%20-%20${encodeURIComponent(this.state.companyName)}`;
    }

    /** Manual refresh triggered by the user clicking "Check Again" */
    async onRefresh() {
        this.state.loading = true;
        await this._checkLock();
        this.state.retryIn = POLL_INTERVAL_MS / 1000;
    }
}

// Register as a main component — this makes Odoo mount it at the root of the
// WebClient, above all views, dialogs, and systray items.
registry.category("main_components").add("SubscriptionLockScreen", {
    Component: SubscriptionLockScreen,
    props: {},
});

export { SubscriptionLockScreen };
