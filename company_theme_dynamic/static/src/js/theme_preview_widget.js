/** @odoo-module **/
/**
 * Company Theme Dynamic – Live Preview Widget
 *
 * Renders a mini mock-up of the Odoo UI inside the company settings form
 * so admins can see how their colour choices look before saving.
 */

import { Component, useState, onWillUpdateProps } from "@odoo/owl";
import { registry }    from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

export class CompanyThemePreview extends Component {
    static template = 'company_theme_dynamic.ThemePreview';
    static props = { ...standardFieldProps };

    setup({orm}) {
        this.state = useState({
            primary:   '#1A73E8',
            secondary: '#34A853',
            accent:    '#FBBC04',
            menuBg:    '#1C2333',
            menuText:  '#FFFFFF',
            topbarBg:  '#FFFFFF',
            topbarText:'#1C2333',
            btnRadius: '8px',
            cardRadius:'12px',
            darkMode:  false,
        });
	this.orm = orm;
    }

    async fetchPreview() {
        try {
            const data = await this.orm.call('res.company', 'get_current_company_theme', [], {});
            if (data?.css_variables) {
                const v = data.css_variables;
                this.state.primary    = v['--ct-primary']    || this.state.primary;
                this.state.secondary  = v['--ct-secondary']  || this.state.secondary;
                this.state.accent     = v['--ct-accent']     || this.state.accent;
                this.state.menuBg     = v['--ct-menu-bg']    || this.state.menuBg;
                this.state.menuText   = v['--ct-menu-text']  || this.state.menuText;
                this.state.topbarBg   = v['--ct-topbar-bg']  || this.state.topbarBg;
                this.state.topbarText = v['--ct-topbar-text']|| this.state.topbarText;
                this.state.btnRadius  = v['--ct-btn-radius'] || this.state.btnRadius;
                this.state.cardRadius = v['--ct-card-radius']|| this.state.cardRadius;
                this.state.darkMode   = data.dark_mode || false;
            }
        } catch (_) {}
    }

    get previewStyle() {
        const s = this.state;
        return `
            --p-primary: ${s.primary};
            --p-secondary: ${s.secondary};
            --p-accent: ${s.accent};
            --p-menu-bg: ${s.menuBg};
            --p-menu-text: ${s.menuText};
            --p-topbar-bg: ${s.topbarBg};
            --p-topbar-text: ${s.topbarText};
            --p-btn-r: ${s.btnRadius};
            --p-card-r: ${s.cardRadius};
        `;
    }
}

registry.category('fields').add('company_theme_preview', {
    component: CompanyThemePreview,
    displayName: 'Company Theme Preview',
    supportedTypes: ['integer'],
});
