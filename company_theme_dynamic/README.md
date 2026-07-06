# 🎨 Company Theme Dynamic — Odoo 19 Module

Per-company dynamic UI theming with animated transitions, dark mode, particle backgrounds, and a live preview widget.

---

## 📁 Module Structure

```
company_theme_dynamic/
├── __manifest__.py                         # Module declaration
├── __init__.py
├── models/
│   ├── __init__.py
│   └── res_company.py                      # ★ Core: extends res.company with 18 theme fields
├── views/
│   ├── res_company_theme_views.xml         # Company form – Theme tab + admin menu
│   └── company_theme_templates.xml         # QWeb head injection (fonts, CSS var placeholder)
├── static/src/
│   ├── css/
│   │   ├── company_theme.css               # ★ 600-line themed CSS (all Odoo views)
│   │   └── theme_preview.css               # Preview widget + systray dot styles
│   ├── js/
│   │   ├── company_theme_service.js        # ★ OWL service: fetches & applies CSS vars
│   │   ├── company_theme_widget.js         # Company-switch watcher + toast + ripple
│   │   └── theme_preview_widget.js         # Field widget: live preview in settings form
│   └── xml/
│       └── company_theme_templates.xml     # OWL templates (watcher, systray, preview UI)
├── security/
│   └── ir.model.access.csv
└── data/
    └── default_theme_data.xml
```

---

## ⚙️ Installation

### 1. Copy the module
```bash
cp -r company_theme_dynamic/ /path/to/odoo/addons/
```
Or place it in a custom addons path defined in `odoo.conf`:
```ini
addons_path = /opt/odoo/addons,/opt/odoo/custom_addons
```

### 2. Restart Odoo & update app list
```bash
sudo systemctl restart odoo
# Then: Settings → Apps → Update Apps List
```

### 3. Install
Search for **"Dynamic Company Theme"** in Apps and click Install.

---

## 🎭 How It Works

### Architecture

```
Browser Load
     │
     ▼
company_theme_service.js (OWL Service)
     │  calls  res.company.get_current_company_theme()
     ▼
Python: res_company.py
     │  reads theme fields from env.company
     ▼
Returns dict of CSS variables + config flags
     │
     ▼
JS injects vars into :root { --ct-primary: ...; }
     │
     ▼
company_theme.css reads vars → all Odoo UI elements themed
```

### Company Switch Flow

```
User switches company (Odoo multi-company)
     │
     ▼
companyThemeWatcher polls session every 1.5s
     │  detects company id change
     ▼
playThemeTransitionRipple(newPrimaryColor)  → full-screen radial ripple
     │
     ▼
applyCompanyTheme() → new CSS vars injected
     │
     ▼
showThemeToast("CompanyName theme activated")
     │
     ▼
Animation class applied: ct-anim-{style}
```

---

## 🎨 Theme Fields (res.company)

| Field | Type | Description |
|-------|------|-------------|
| `theme_preset` | Selection | Quick preset picker (6 presets + Custom) |
| `theme_primary_color` | Char | Main brand colour (buttons, links) |
| `theme_secondary_color` | Char | Secondary/success colour |
| `theme_accent_color` | Char | Accent/warning colour |
| `theme_menu_bg` | Char | Sidebar background |
| `theme_menu_text` | Char | Sidebar text colour |
| `theme_menu_highlight` | Char | Active sidebar item highlight |
| `theme_topbar_bg` | Char | Top navigation bar background |
| `theme_topbar_text` | Char | Top bar text/icon colour |
| `theme_button_radius` | Char | Button border radius (e.g. `8px`, `24px`) |
| `theme_card_radius` | Char | Card/modal border radius |
| `theme_font_family` | Char | Google Font stack |
| `theme_sidebar_width` | Char | Sidebar width (e.g. `240px`) |
| `theme_animation_style` | Selection | Page transition: slide/fade/zoom/blur |
| `theme_dark_mode` | Boolean | Dark mode toggle |
| `theme_enable_particle` | Boolean | Particle canvas background |
| `theme_enable_gradient_menu` | Boolean | Gradient on sidebar |
| `theme_enable_glow_buttons` | Boolean | Glow effect on primary buttons |
| `theme_show_watermark` | Boolean | Company logo watermark overlay |

---

## 🎭 Built-In Presets

| Preset | Primary | Menu BG | Style |
|--------|---------|---------|-------|
| 🔵 Modern Blue | `#1A73E8` | `#1C2333` | `Inter`, 8px radius |
| ⚫ Minimal Slate | `#2D3748` | `#F7FAFC` | `DM Sans`, 4px radius |
| 🟣 Bold Purple | `#6C3CE1` | `#1A0B3B` | `Syne`, 24px pill radius |
| 🔷 Glass Sky | `#0EA5E9` | Dark glass | `Outfit`, blur effects |
| 🏢 Corporate Navy | `#003087` | `#001F5B` | `Source Sans 3`, conservative |
| 🟢 Nature Green | `#2E7D32` | `#1B5E20` | `Nunito`, organic feel |

---

## ✨ Animations

### Page Transitions
Applied via CSS class `ct-anim-{style}` on `.o_web_client`:

- **`ct-anim-slide`** — content slides in from left (default)
- **`ct-anim-fade`** — soft opacity fade
- **`ct-anim-zoom`** — subtle scale-up reveal
- **`ct-anim-blur`** — defocus-to-focus effect

### Micro-interactions
- **Button ripple** — click primary buttons to see a radial ripple wave
- **Sidebar hover** — items slide 4px right with highlight
- **Active sidebar pill** — animated left-border indicator
- **App icons (home menu)** — staggered zoom-in on load, float up on hover
- **Stat cards** — lift + shadow on hover
- **Kanban cards** — scale + shadow on hover
- **Company switch** — full-screen radial ripple in brand colour + toast notification
- **Notifications** — slide in from left with semantic left border
- **Modals** — zoom-in entrance animation

### Particle Engine
When `theme_enable_particle = True`:
- Renders a `<canvas>` behind the Odoo UI
- Animated floating dots with connection lines in brand colour
- Auto-resizes on window resize
- Auto-stops on company switch (re-initialises with new colour)

---

## 🌙 Dark Mode

Toggle `theme_dark_mode` per company. Dark overrides:

| Element | Dark value |
|---------|-----------|
| Page background | `#0F1117` |
| Surfaces (cards, forms) | `#1A1F2E` |
| Text | `#E2E8F0` |
| Borders | `#2D3748` |

---

## 🖥️ Live Preview Widget

When editing a company's Theme tab, a miniature mock-up of the Odoo interface renders in real-time showing how the topbar, sidebar, stat cards, table, and buttons will look with the chosen colours.

Click **↻ Refresh** after changing colour fields to update the preview.

---

## 🔌 Extending / Customising

### Adding a new preset
In `res_company.py`, add to the `THEME_PRESETS` dict:
```python
'ocean': {
    'primary_color': '#0077B6',
    'secondary_color': '#00B4D8',
    'accent_color': '#90E0EF',
    'menu_bg': '#03045E',
    'menu_text': '#CAF0F8',
    'menu_highlight': '#0077B6',
    # ...
}
```
Then add the selection option to `theme_preset`.

### Theming a custom module's views
Use the CSS variables in your module's SCSS/CSS:
```css
.my_module .my_card {
    border-color: var(--ct-primary);
    border-radius: var(--ct-card-radius);
    font-family: var(--ct-font);
}
.my_module .my_btn {
    background: var(--ct-primary);
    border-radius: var(--ct-btn-radius);
}
```

### Calling the theme from JS
```javascript
import { useService } from "@web/core/utils/hooks";
// inside setup():
const companyTheme = useService('company_theme');
// re-apply manually if needed:
await companyTheme.applyTheme();
```

---

## 🔐 Access Rights

| Group | Read | Write |
|-------|------|-------|
| Internal User | ✅ | ❌ |
| Administrator | ✅ | ✅ |

---

## 📦 Dependencies

- `base` — res.company model
- `web` — OWL framework, service registry
- `base_setup` — Settings menu parent

No external Python packages required.

---

## 🚀 Quick Start After Install

1. Go to **Settings → General Settings → 🎨 Company Themes**
2. Open a company record
3. Click the **🎨 Theme** tab
4. Pick a preset (colours auto-fill)
5. Toggle Dark Mode, Particle BG, Animations as desired
6. Click **Save**
7. Switch to that company — the theme activates instantly with a ripple animation

---

## 📝 Notes

- Theme is applied client-side via CSS custom properties — zero server round-trips after initial load.
- The `get_current_company_theme()` RPC is called once on page load and once on each company switch.
- CSS variables transition smoothly (`transition: 0.3s`) so colour changes feel fluid.
- The module is safe for multi-company setups: each company's theme is fully independent.
