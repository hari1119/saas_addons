/** @odoo-module **/

import { Component } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

export class MusicSystray extends Component {
    static template = "music_player.MusicSystray";

    setup() {
        this.action = useService("action");
        this.player = useService("music_player");
    }

    openStudio() {
        this.action.doAction("music_player.action_music_studio");
    }
}

registry.category("systray").add("music_player.systray", { Component: MusicSystray }, { sequence: 15 });
