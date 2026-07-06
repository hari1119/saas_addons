# -*- coding: utf-8 -*-
import json
from odoo import api, fields, models


THEME_PRESETS = {
    'modern': {
        'primary_color': '#1A73E8',
        'secondary_color': '#34A853',
        'accent_color': '#FBBC04',
        'menu_bg': '#1C2333',
        'menu_text': '#FFFFFF',
        'menu_highlight': '#1A73E8',
        'topbar_bg': '#FFFFFF',
        'topbar_text': '#1C2333',
        'button_radius': '8px',
        'card_radius': '12px',
        'font_family': "'Inter', sans-serif",
        'sidebar_width': '240px',
        'animation_style': 'slide',
    },
    'minimal': {
        'primary_color': '#2D3748',
        'secondary_color': '#4A5568',
        'accent_color': '#ED8936',
        'menu_bg': '#F7FAFC',
        'menu_text': '#2D3748',
        'menu_highlight': '#EBF8FF',
        'topbar_bg': '#2D3748',
        'topbar_text': '#FFFFFF',
        'button_radius': '4px',
        'card_radius': '6px',
        'font_family': "'DM Sans', sans-serif",
        'sidebar_width': '220px',
        'animation_style': 'fade',
    },
    'bold': {
        'primary_color': '#6C3CE1',
        'secondary_color': '#E13C8E',
        'accent_color': '#F5A623',
        'menu_bg': '#1A0B3B',
        'menu_text': '#E8D5FF',
        'menu_highlight': '#6C3CE1',
        'topbar_bg': '#6C3CE1',
        'topbar_text': '#FFFFFF',
        'button_radius': '24px',
        'card_radius': '16px',
        'font_family': "'Syne', sans-serif",
        'sidebar_width': '260px',
        'animation_style': 'zoom',
    },
    'glass': {
        'primary_color': '#0EA5E9',
        'secondary_color': '#06B6D4',
        'accent_color': '#F59E0B',
        'menu_bg': 'rgba(15, 23, 42, 0.85)',
        'menu_text': '#E2E8F0',
        'menu_highlight': 'rgba(14, 165, 233, 0.3)',
        'topbar_bg': 'rgba(255,255,255,0.85)',
        'topbar_text': '#0F172A',
        'button_radius': '10px',
        'card_radius': '14px',
        'font_family': "'Outfit', sans-serif",
        'sidebar_width': '250px',
        'animation_style': 'blur',
    },
    'corporate': {
        'primary_color': '#003087',
        'secondary_color': '#005BBB',
        'accent_color': '#FFD700',
        'menu_bg': '#001F5B',
        'menu_text': '#FFFFFF',
        'menu_highlight': '#003087',
        'topbar_bg': '#003087',
        'topbar_text': '#FFFFFF',
        'button_radius': '6px',
        'card_radius': '8px',
        'font_family': "'Source Sans 3', sans-serif",
        'sidebar_width': '240px',
        'animation_style': 'slide',
    },
    'nature': {
        'primary_color': '#2E7D32',
        'secondary_color': '#43A047',
        'accent_color': '#FF8F00',
        'menu_bg': '#1B5E20',
        'menu_text': '#F1F8E9',
        'menu_highlight': '#2E7D32',
        'topbar_bg': '#FFFFFF',
        'topbar_text': '#1B5E20',
        'button_radius': '10px',
        'card_radius': '12px',
        'font_family': "'Nunito', sans-serif",
        'sidebar_width': '240px',
        'animation_style': 'fade',
    },
}


class ResCompany(models.Model):
    _inherit = 'res.company'

    # ── Theme Preset ──────────────────────────────────────────────────────────
    theme_preset = fields.Selection([
        ('modern', '🔵 Modern Blue'),
        ('minimal', '⚫ Minimal Slate'),
        ('bold', '🟣 Bold Purple'),
        ('glass', '🔷 Glass Sky'),
        ('corporate', '🏢 Corporate Navy'),
        ('nature', '🟢 Nature Green'),
        ('custom', '🎨 Custom'),
    ], string='Theme Preset', default='modern',
       help='Choose a preset or select Custom to define your own colors.')

    # ── Custom Colors ─────────────────────────────────────────────────────────
    theme_primary_color = fields.Char(
        string='Primary Color', default='#1A73E8',
        help='Main brand color used for buttons, links, highlights.')
    theme_secondary_color = fields.Char(
        string='Secondary Color', default='#34A853')
    theme_accent_color = fields.Char(
        string='Accent / Warning Color', default='#FBBC04')

    # ── Menu / Sidebar ────────────────────────────────────────────────────────
    theme_menu_bg = fields.Char(
        string='Sidebar Background', default='#1C2333')
    theme_menu_text = fields.Char(
        string='Sidebar Text Color', default='#FFFFFF')
    theme_menu_highlight = fields.Char(
        string='Sidebar Active Highlight', default='#1A73E8')

    # ── Top Bar ───────────────────────────────────────────────────────────────
    theme_topbar_bg = fields.Char(
        string='Top Bar Background', default='#FFFFFF')
    theme_topbar_text = fields.Char(
        string='Top Bar Text Color', default='#1C2333')

    # ── Shape & Typography ────────────────────────────────────────────────────
    theme_button_radius = fields.Char(
        string='Button Border Radius', default='8px')
    theme_card_radius = fields.Char(
        string='Card Border Radius', default='12px')
    theme_font_family = fields.Char(
        string='Font Family', default="'Inter', sans-serif")
    theme_sidebar_width = fields.Char(
        string='Sidebar Width', default='240px')

    # ── Animation ─────────────────────────────────────────────────────────────
    theme_animation_style = fields.Selection([
        ('slide', 'Slide In'),
        ('fade', 'Fade In'),
        ('zoom', 'Zoom In'),
        ('blur', 'Blur Reveal'),
        ('none', 'No Animation'),
    ], string='Page Transition Animation', default='slide')

    theme_enable_particle = fields.Boolean(
        string='Enable Particle Background', default=False)
    theme_enable_gradient_menu = fields.Boolean(
        string='Gradient Sidebar', default=True)
    theme_enable_glow_buttons = fields.Boolean(
        string='Glow on Buttons', default=True)

    # ── Dark Mode ─────────────────────────────────────────────────────────────
    theme_dark_mode = fields.Boolean(
        string='Dark Mode', default=False)

    # ── Logo watermark ────────────────────────────────────────────────────────
    theme_show_watermark = fields.Boolean(
        string='Show Company Watermark', default=False)

    @api.onchange('theme_preset')
    def _onchange_theme_preset(self):
        """Auto-fill color fields when a preset is chosen."""
        if self.theme_preset and self.theme_preset != 'custom':
            preset = THEME_PRESETS.get(self.theme_preset, {})
            self.theme_primary_color = preset.get('primary_color', self.theme_primary_color)
            self.theme_secondary_color = preset.get('secondary_color', self.theme_secondary_color)
            self.theme_accent_color = preset.get('accent_color', self.theme_accent_color)
            self.theme_menu_bg = preset.get('menu_bg', self.theme_menu_bg)
            self.theme_menu_text = preset.get('menu_text', self.theme_menu_text)
            self.theme_menu_highlight = preset.get('menu_highlight', self.theme_menu_highlight)
            self.theme_topbar_bg = preset.get('topbar_bg', self.theme_topbar_bg)
            self.theme_topbar_text = preset.get('topbar_text', self.theme_topbar_text)
            self.theme_button_radius = preset.get('button_radius', self.theme_button_radius)
            self.theme_card_radius = preset.get('card_radius', self.theme_card_radius)
            self.theme_font_family = preset.get('font_family', self.theme_font_family)
            self.theme_sidebar_width = preset.get('sidebar_width', self.theme_sidebar_width)
            self.theme_animation_style = preset.get('animation_style', self.theme_animation_style)

    def get_theme_css_variables(self):
        """Return a dict of CSS variables for the current company theme."""
        self.ensure_one()

        def hex_to_rgb(hex_color):
            """Convert #RRGGBB to 'R, G, B' string for rgba() usage."""
            try:
                h = hex_color.lstrip('#')
                if len(h) == 6:
                    return ', '.join(str(int(h[i:i+2], 16)) for i in (0, 2, 4))
            except Exception:
                pass
            return '0, 0, 0'

        primary = self.theme_primary_color or '#1A73E8'
        secondary = self.theme_secondary_color or '#34A853'
        accent = self.theme_accent_color or '#FBBC04'
        menu_bg = self.theme_menu_bg or '#1C2333'
        menu_text = self.theme_menu_text or '#FFFFFF'
        menu_hl = self.theme_menu_highlight or primary
        topbar_bg = self.theme_topbar_bg or '#FFFFFF'
        topbar_text = self.theme_topbar_text or '#1C2333'
        btn_radius = self.theme_button_radius or '8px'
        card_radius = self.theme_card_radius or '12px'
        font = self.theme_font_family or "'Inter', sans-serif"
        sidebar_w = self.theme_sidebar_width or '240px'
        dark = self.theme_dark_mode

        return {
            '--ct-primary': primary,
            '--ct-primary-rgb': hex_to_rgb(primary),
            '--ct-secondary': secondary,
            '--ct-accent': accent,
            '--ct-menu-bg': menu_bg,
            '--ct-menu-text': menu_text,
            '--ct-menu-highlight': menu_hl,
            '--ct-menu-highlight-rgb': hex_to_rgb(menu_hl),
            '--ct-topbar-bg': topbar_bg,
            '--ct-topbar-text': topbar_text,
            '--ct-btn-radius': btn_radius,
            '--ct-card-radius': card_radius,
            '--ct-font': font,
            '--ct-sidebar-width': sidebar_w,
            '--ct-dark': '1' if dark else '0',
            '--ct-page-bg': '#0F1117' if dark else '#F4F6FA',
            '--ct-surface': '#1A1F2E' if dark else '#FFFFFF',
            '--ct-text': '#E2E8F0' if dark else '#1C2333',
            '--ct-border': '#2D3748' if dark else '#E2E8F0',
            '--ct-shadow': f'0 4px 24px rgba({hex_to_rgb(primary)}, 0.18)',
            '--ct-glow': f'0 0 20px rgba({hex_to_rgb(primary)}, 0.35)',
            '--ct-gradient': f'linear-gradient(135deg, {primary} 0%, {secondary} 100%)',
            '--ct-animation': self.theme_animation_style or 'slide',
            '--ct-enable-glow': '1' if self.theme_enable_glow_buttons else '0',
            '--ct-enable-gradient-menu': '1' if self.theme_enable_gradient_menu else '0',
        }

    @api.model
    def get_current_company_theme(self):
        """Called from JS to fetch CSS variables for the current company."""
        company = self.env.company
        css_vars = company.get_theme_css_variables()
        return {
            'company_id': company.id,
            'company_name': company.name,
            'css_variables': css_vars,
            'animation_style': company.theme_animation_style or 'slide',
            'enable_particle': company.theme_enable_particle,
            'dark_mode': company.theme_dark_mode,
            'show_watermark': company.theme_show_watermark,
            'logo': company.logo.decode('utf-8') if company.logo else False,
        }
