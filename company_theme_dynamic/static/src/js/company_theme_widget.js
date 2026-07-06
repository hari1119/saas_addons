/** @odoo-module **/
/**
 * Company Theme Dynamic – Theme Widget
 *
 * An OWL widget that:
 *   1. Detects when the active company changes inside the Odoo session.
 *   2. Triggers a smooth CSS transition (overlay ripple from the company logo).
 *   3. Re-fetches and applies the new company's theme variables.
 *
 * Also exposes a "Theme Applied" toast notification so users know a new
 * theme has been activated after a company switch.
 */

import { Component, useState, onMounted, onWillUnmount, useService } from "@odoo/owl";
import { registry }       from "@web/core/registry";
import { session }        from "@web/session";

// ── Theme Transition Overlay ─────────────────────────────────────────────────

/**
 * Creates a brief full-screen ripple that radiates from the top-right
 * (where the company switcher lives) to signal a theme change.
 *
 * @param {string} color  CSS color for the ripple (the new company's primary)
 */
function playThemeTransitionRipple(color = '#1A73E8') {
    const overlay = document.createElement('div');

    Object.assign(overlay.style, {
        position:        'fixed',
        top:             '0',
        right:           '0',
        width:           '1px',
        height:          '1px',
        borderRadius:    '50%',
        background:      color,
        transform:       'scale(0)',
        transformOrigin: 'top right',
        zIndex:          '99999',
        pointerEvents:   'none',
        transition:      'transform 0.65s cubic-bezier(0.4, 0, 0.2, 1), opacity 0.65s ease',
        opacity:         '0.35',
    });

    document.body.appendChild(overlay);

    // Trigger reflow then animate
    requestAnimationFrame(() => {
        overlay.style.transform = 'scale(4000)';
        overlay.style.opacity   = '0';
    });

    setTimeout(() => {
        if (overlay.parentNode) overlay.parentNode.removeChild(overlay);
    }, 700);
}

// ── Toast Notification ───────────────────────────────────────────────────────

function showThemeToast(companyName, primaryColor) {
    const existing = document.getElementById('ct-theme-toast');
    if (existing) existing.remove();

    const toast = document.createElement('div');
    toast.id = 'ct-theme-toast';

    Object.assign(toast.style, {
        position:     'fixed',
        bottom:       '24px',
        left:         '50%',
        transform:    'translateX(-50%) translateY(20px)',
        background:   primaryColor,
        color:        '#fff',
        padding:      '10px 22px',
        borderRadius: '30px',
        fontSize:     '13px',
        fontWeight:   '600',
        boxShadow:    `0 6px 24px rgba(0,0,0,0.18)`,
        zIndex:       '99998',
        opacity:      '0',
        transition:   'opacity 0.3s ease, transform 0.3s ease',
        pointerEvents:'none',
        letterSpacing:'0.3px',
        whiteSpace:   'nowrap',
    });

    toast.textContent = `✨ ${companyName} theme activated`;
    document.body.appendChild(toast);

    requestAnimationFrame(() => {
        toast.style.opacity   = '1';
        toast.style.transform = 'translateX(-50%) translateY(0)';
    });

    setTimeout(() => {
        toast.style.opacity   = '0';
        toast.style.transform = 'translateX(-50%) translateY(10px)';
        setTimeout(() => toast.remove(), 350);
    }, 3000);
}

// ── OWL Component: Company Theme Watcher ────────────────────────────────────

export class CompanyThemeWatcher extends Component {
    static template = 'company_theme_dynamic.CompanyThemeWatcher';
    static props = {};

    setup() {
        this.config = this.models["pos.config"].getFirst();
        this.company = this.config.company_id;
        this.orm            = useService('orm');
        this.companyService = this.config.company_id; //useService('company');
        this._prevCompanyId = null;
        this._intervalId    = null;
    }

    async _checkAndApplyTheme() {
        const currentId = this.companyService.currentCompany?.id;
        if (!currentId || currentId === this._prevCompanyId) return;

        // Fetch theme for new company
        let themeData;
        try {
            themeData = await this.orm.call('res.company', 'get_current_company_theme', [], {});
        } catch (e) {
            return;
        }

        if (!themeData) return;

        const { css_variables, company_name } = themeData;
        const primary = css_variables['--ct-primary'] || '#1A73E8';

        // Play transition
        if (this._prevCompanyId !== null) {
            playThemeTransitionRipple(primary);
            showThemeToast(company_name, primary);
        }

        this._prevCompanyId = currentId;

        // Apply CSS variables
        for (const [k, v] of Object.entries(css_variables)) {
            document.documentElement.style.setProperty(k, v);
        }
    }

    onMounted() {
        this._prevCompanyId = this.companyService.currentCompany?.id;
        this._intervalId = setInterval(() => this._checkAndApplyTheme(), 1500);
    }

    onWillUnmount() {
        if (this._intervalId) clearInterval(this._intervalId);
    }
}

// ── Systray icon: "Themes" quick indicator ───────────────────────────────────

export class ThemeSystrayIcon extends Component {
    static template = 'company_theme_dynamic.ThemeSystrayIcon';
    static props = {};

    setup() {
        this.state = useState({ primary: '#1A73E8' });
        this.orm   = useService('orm');
    }

    async fetchPrimary() {
        try {
            const data = await this.orm.call('res.company', 'get_current_company_theme', [], {});
            if (data?.css_variables?.['--ct-primary']) {
                this.state.primary = data.css_variables['--ct-primary'];
            }
        } catch (_) {}
    }
}

// Register systray item
registry.category('systray').add('company_theme_indicator', {
    Component: ThemeSystrayIcon,
    sequence: 50,
});
