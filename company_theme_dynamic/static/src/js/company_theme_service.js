/** @odoo-module **/
/**
 * Company Theme Dynamic – Theme Service
 *
 * Fetches the current company's theme settings from the server and
 * injects CSS custom properties into :root so that all theme-aware
 * CSS rules pick them up.  Also handles:
 *   - Company-switch transition animation
 *   - Dark-mode class toggling
 *   - Animation-style class on the web client root
 *   - Optional particle background
 *   - Company watermark overlay
 *   - Button ripple micro-interaction
 */

import { registry }        from "@web/core/registry";
import { session }         from "@web/session";
import { Component, onMounted, onWillUnmount } from "@odoo/owl";
import { user } from "@web/core/user";

// ── Helpers ─────────────────────────────────────────────────────────────────

/**
 * Write a set of CSS variable key/value pairs onto a given element's style.
 * @param {Object} vars  Plain object of { '--ct-foo': 'bar', … }
 * @param {Element} [el] Defaults to document.documentElement (:root)
 */
function applyCSSVars(vars, el = document.documentElement) {
    for (const [key, value] of Object.entries(vars)) {
        el.style.setProperty(key, value);
    }
}

/**
 * Toggle a CSS class on the web-client root element.
 */
function setBodyClass(className, active) {
    const root = document.querySelector('.o_web_client') || document.body;
    root.classList.toggle(className, active);
}

// ── Particle Engine ──────────────────────────────────────────────────────────

class ParticleEngine {
    constructor(primaryRgb) {
        this.primaryRgb = primaryRgb || '26, 115, 232';
        this.canvas     = null;
        this.ctx        = null;
        this.particles  = [];
        this.raf        = null;
        this._running   = false;
    }

    start() {
        if (this._running) return;
        this._running = true;

        this.canvas = document.createElement('canvas');
        this.canvas.id = 'ct-particle-canvas';
        document.body.appendChild(this.canvas);
        this.ctx = this.canvas.getContext('2d');

        this._resize();
        window.addEventListener('resize', this._resize.bind(this));
        this._initParticles();
        this._loop();
    }

    stop() {
        this._running = false;
        if (this.raf) cancelAnimationFrame(this.raf);
        if (this.canvas && this.canvas.parentNode) {
            this.canvas.parentNode.removeChild(this.canvas);
        }
        window.removeEventListener('resize', this._resize.bind(this));
    }

    _resize() {
        if (!this.canvas) return;
        this.canvas.width  = window.innerWidth;
        this.canvas.height = window.innerHeight;
    }

    _initParticles() {
        this.particles = [];
        const count = Math.min(60, Math.floor((window.innerWidth * window.innerHeight) / 14000));
        for (let i = 0; i < count; i++) {
            this.particles.push({
                x:     Math.random() * window.innerWidth,
                y:     Math.random() * window.innerHeight,
                r:     Math.random() * 2.5 + 0.5,
                dx:    (Math.random() - 0.5) * 0.5,
                dy:    (Math.random() - 0.5) * 0.5,
                alpha: Math.random() * 0.5 + 0.1,
            });
        }
    }

    _loop() {
        if (!this._running) return;
        const { ctx, canvas, particles, primaryRgb } = this;

        ctx.clearRect(0, 0, canvas.width, canvas.height);

        for (const p of particles) {
            p.x += p.dx;
            p.y += p.dy;
            if (p.x < 0) p.x = canvas.width;
            if (p.x > canvas.width) p.x = 0;
            if (p.y < 0) p.y = canvas.height;
            if (p.y > canvas.height) p.y = 0;

            ctx.beginPath();
            ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
            ctx.fillStyle = `rgba(${primaryRgb}, ${p.alpha})`;
            ctx.fill();
        }

        // Draw connecting lines
        for (let i = 0; i < particles.length; i++) {
            for (let j = i + 1; j < particles.length; j++) {
                const dx = particles[i].x - particles[j].x;
                const dy = particles[i].y - particles[j].y;
                const dist = Math.sqrt(dx * dx + dy * dy);
                if (dist < 110) {
                    ctx.beginPath();
                    ctx.moveTo(particles[i].x, particles[i].y);
                    ctx.lineTo(particles[j].x, particles[j].y);
                    ctx.strokeStyle = `rgba(${primaryRgb}, ${0.12 * (1 - dist / 110)})`;
                    ctx.lineWidth = 0.8;
                    ctx.stroke();
                }
            }
        }

        this.raf = requestAnimationFrame(this._loop.bind(this));
    }
}

// ── Main Theme Service ───────────────────────────────────────────────────────

const _particleEngine = { instance: null };

async function applyCompanyTheme(orm, companyId) {
    try {
        // Fetch theme data from Python model
        const themeData = await orm.call(
            'res.company',
            'get_current_company_theme',
            [],
            {}
        );

        if (!themeData) return;

        const {
            css_variables,
            animation_style,
            dark_mode,
            enable_particle,
            show_watermark,
            logo,
        } = themeData;

        // ── 1. CSS Variable Injection ──────────────────────────────────
        applyCSSVars(css_variables);

        // ── 2. Animation class on web client root ──────────────────────
        const root = document.querySelector('.o_web_client') || document.body;
        ['ct-anim-slide','ct-anim-fade','ct-anim-zoom','ct-anim-blur'].forEach(c => {
            root.classList.remove(c);
        });
        if (animation_style && animation_style !== 'none') {
            root.classList.add(`ct-anim-${animation_style}`);
        }

        // ── 3. Dark mode ───────────────────────────────────────────────
        setBodyClass('ct-dark-mode', !!dark_mode);

        // ── 4. Gradient menu ───────────────────────────────────────────
        const gradientMenu = css_variables['--ct-enable-gradient-menu'] === '1';
        setBodyClass('ct-gradient-menu', gradientMenu);

        // ── 5. Particle background ─────────────────────────────────────
        if (enable_particle) {
            const primaryRgb = css_variables['--ct-primary-rgb'] || '26, 115, 232';
            if (_particleEngine.instance) {
                _particleEngine.instance.stop();
            }
            _particleEngine.instance = new ParticleEngine(primaryRgb);
            _particleEngine.instance.start();
        } else {
            if (_particleEngine.instance) {
                _particleEngine.instance.stop();
                _particleEngine.instance = null;
            }
        }

        // ── 6. Company watermark ───────────────────────────────────────
        const existingWM = document.getElementById('ct-company-watermark');
        if (existingWM) existingWM.remove();

        if (show_watermark && logo) {
            const img = document.createElement('img');
            img.id  = 'ct-company-watermark';
            img.src = `data:image/png;base64,${logo}`;
            img.className = 'ct-watermark';
            document.body.appendChild(img);
        }

        // ── 7. Update the <style id="ct-css-vars"> placeholder ─────────
        // (Ensures SSR fallback is correct on next hard reload)
        const styleEl = document.getElementById('ct-css-vars');
        if (styleEl) {
            const varLines = Object.entries(css_variables)
                .map(([k, v]) => `  ${k}: ${v};`)
                .join('\n');
            styleEl.textContent = `:root {\n${varLines}\n}`;
        }

    } catch (error) {
        console.warn('[CompanyTheme] Failed to apply theme:', error);
    }
}

// ── Button Ripple Effect ─────────────────────────────────────────────────────

function attachRippleEffect() {
    document.addEventListener('click', (e) => {
        const btn = e.target.closest('.btn-primary');
        if (!btn) return;

        const rect = btn.getBoundingClientRect();
        btn.style.setProperty('--x', `${e.clientX - rect.left}px`);
        btn.style.setProperty('--y', `${e.clientY - rect.top}px`);
        btn.classList.add('ct-ripple-active');
        setTimeout(() => btn.classList.remove('ct-ripple-active'), 600);
    }, { passive: true });
}

// ── Company Switch Transition ────────────────────────────────────────────────

let _lastCompanyId = null;

function attachCompanySwitchObserver(orm) {
    // Watch for company changes via session
    setInterval(async () => {
        const currentId = session.user_companies?.current_company?.[0];
        if (currentId && currentId !== _lastCompanyId) {
            if (_lastCompanyId !== null) {
                // Animate the switch
                const root = document.querySelector('.o_web_client') || document.body;
                root.classList.add('ct-switching-company');
                setTimeout(() => root.classList.remove('ct-switching-company'), 700);
            }
            _lastCompanyId = currentId;
            await applyCompanyTheme(orm, currentId);
        }
    }, 1500);
}

// ── Service Registration ─────────────────────────────────────────────────────

export const companyThemeService = {
    name: 'company_theme',
    dependencies: ['orm'],

    async start(env, { orm }) {
        // Initial application
	this.defaultCurrency = user.activeCompany.currency_id;
        await applyCompanyTheme(orm, this.defaultCurrency?.id);
        _lastCompanyId = this.defaultCurrency?.id;

        // Attach helpers
        attachRippleEffect();
        attachCompanySwitchObserver(orm);

        // Re-apply on company switch events
        env.bus.addEventListener('COMPANY_UPDATED', async () => {
            const root = document.querySelector('.o_web_client') || document.body;
            root.classList.add('ct-switching-company');
            setTimeout(() => root.classList.remove('ct-switching-company'), 700);
            await applyCompanyTheme(orm, this.defaultCurrency?.id);
        });

        return {
            applyTheme: () => applyCompanyTheme(orm, this.defaultCurrency?.id),
        };
    },
};

registry.category('services').add('company_theme', companyThemeService);
