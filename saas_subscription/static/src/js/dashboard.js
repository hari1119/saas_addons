/** @odoo-module **/
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, onMounted, useState } from "@odoo/owl";
import { rpc } from "@web/core/network/rpc";

class SaasDashboard extends Component {
    static template = "saas_subscription.Dashboard";

    setup() {
        this.rpc = rpc;
        this.action = useService("action");
        this.state = useState({
            loading: true,
            data: null,
            error: null,
        });
        onMounted(() => this._loadData());
    }

    async _loadData() {
        try {
            const data = await this.rpc("/saas/dashboard/data", {});
            if (data.error) {
                this.state.error = data.error;
            } else {
                this.state.data = data;
            }
        } catch (e) {
            this.state.error = "Failed to load dashboard data.";
        } finally {
            this.state.loading = false;
        }
    }

    openSubscriptions(domain) {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Subscriptions",
            res_model: "saas.subscription",
            views: [[false, 'list']],
            domain: domain || [],
            target: 'self',
        });
    }

    openExpiring() {
        this.openSubscriptions([
            ["state", "=", "active"],
            ["is_near_expiry", "=", true],
        ]);
    }

    openByState(state) {
        this.openSubscriptions([["state", "=", state]]);
    }
}

registry.category("actions").add("saas_subscription.Dashboard", SaasDashboard);

export { SaasDashboard };
