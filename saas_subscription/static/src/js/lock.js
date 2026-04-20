/** lock.js **/
import { Component, mount, useState, onWillStart } from "@odoo/owl";

export class SubscriptionLock extends Component {
    static template = "saas_subscription.SubscriptionLock";
    mounted() {
        console.log("Hello World");
    }

}
// SubscriptionLock.template = "saas_subscription.SubscriptionLock";

mount(SubscriptionLock, document.body);
