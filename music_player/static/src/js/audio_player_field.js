/** @odoo-module **/

import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

import { Component } from "@odoo/owl";

export class AudioPlayerField extends Component {
    static template = "music_player.AudioPlayerField";
    static props = {
        ...standardFieldProps,
    };

    get audioUrl() {
        return this.props.record.data[this.props.name] || "";
    }
}

export const audioPlayerField = {
    component: AudioPlayerField,
    displayName: _t("Audio Player"),
    supportedTypes: ["char"],
};

registry.category("fields").add("music_audio_player", audioPlayerField);
