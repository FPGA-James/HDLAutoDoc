# Furo Theme Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace `sphinx-rtd-theme` with `furo` to gain a built-in Ctrl+K search modal and native dark/light toggle.

**Architecture:** Five files change — `requirements.txt`, `conf.py`, `layout.html`, `custom.css`, and two file deletions (`breadcrumbs.html`, `theme.js`). All RST content, extractors, Makefile, and register maps are untouched. Work on a feature branch so `main` is untouched until approved.

**Tech Stack:** Furo (Sphinx theme), Python, CSS custom properties (Catppuccin).

## Global Constraints

- Branch name: `feat/furo-theme`
- Do not modify any `.rst` files, extractor scripts, `Makefile`, or `registers/`
- Furo uses `[data-theme="dark"]` on `<html>` — same selector as our existing dark mode CSS, so Catppuccin Mocha activates automatically
- `html_static_path`, `html_templates_path`, `html_css_files`, `html_logo`, `html_favicon`, `html_show_sphinx`, `html_title`, `html_short_title` stay unchanged in `conf.py`
- PDF build uses LaTeX regardless of `html_theme` — Furo does not affect PDF output

---

## File Map

| File | Action |
|---|---|
| `requirements.txt` | Replace `sphinx-rtd-theme>=2.0` with `furo` |
| `docs/hdl_autodoc/conf.py` | Set `html_theme = "furo"`, replace `html_theme_options`, remove `html_js_files` line |
| `docs/hdl_autodoc/_templates/layout.html` | Rewrite — drop RTD-specific blocks, keep `extrahead` and `page_footer` |
| `docs/hdl_autodoc/_templates/breadcrumbs.html` | **Delete** — Furo renders its own breadcrumbs |
| `docs/hdl_autodoc/_static/theme.js` | **Delete** — Furo ships its own dark/light toggle |
| `docs/hdl_autodoc/_static/custom.css` | Strip all `.wy-*`, `.rst-content`-prefixed, sidebar-brand, and toggle CSS; keep Catppuccin variables and component rules |

---

## Task 1: Branch + config + templates

**Files:**
- `requirements.txt`
- `docs/hdl_autodoc/conf.py`
- `docs/hdl_autodoc/_templates/layout.html`
- Delete: `docs/hdl_autodoc/_templates/breadcrumbs.html`
- Delete: `docs/hdl_autodoc/_static/theme.js`

### Context

Furo block names differ from RTD. The current `layout.html` uses `sidebartitle` (RTD) and `footer` (RTD). Furo provides sidebar branding natively from `html_logo` and `html_title` in conf.py, and uses `page_footer` for the footer slot.

The current `conf.py` has:
- `html_theme = "sphinx_rtd_theme"` — change to `"furo"`
- `html_js_files = ["theme.js"]` — remove entirely (Furo ships its own toggle)
- `html_theme_options` — replace with Furo options dict

- [ ] **Step 1: Create feature branch**

```bash
git checkout -b feat/furo-theme
```

Expected: `Switched to a new branch 'feat/furo-theme'`

- [ ] **Step 2: Swap the theme dependency in `requirements.txt`**

In `requirements.txt`, replace:
```
sphinx-rtd-theme>=2.0
```
with:
```
furo
```

Full file after change:
```
# Core Sphinx
sphinx>=7.0,<9.0

# Pin docutils — sphinxvhdl 0.2.2 has a transition node bug with docutils 0.21+
docutils>=0.18,<0.21

# Theme
furo

# WaveDrom — multiple diagrams per file via .. wavedrom:: directive
sphinxcontrib-wavedrom>=3.0

# VHDL domain — auto-doc from annotated VHDL source
sphinx-vhdl>=0.1

# Offline WaveDrom rendering (no Node.js needed for PDF builds)
wavedrom
```

- [ ] **Step 3: Install the new dependency**

```bash
pip install furo
```

Expected: `Successfully installed furo-...`

- [ ] **Step 4: Update `conf.py`**

Replace the entire `# ── HTML output ───` section (lines 39–58):

Old:
```python
# ── HTML output ──────────────────────────────────────────────────────────────
html_theme         = "sphinx_rtd_theme"
html_static_path   = ["_static"]
html_templates_path = ["_templates"]
html_js_files  = ["theme.js"]
html_css_files     = ["custom.css"]
html_logo          = "_static/logo.svg"
html_favicon       = "_static/logo.svg"
html_show_sphinx   = False          # remove "Built with Sphinx" footer clutter
html_title         = project
html_short_title   = project

html_theme_options = {
    "logo_only":           True,    # show logo instead of project name in sidebar
    "navigation_depth":    6,
    "collapse_navigation": False,
    "sticky_navigation":   True,
    "includehidden":       True,
    "titles_only":         False,
}
```

New:
```python
# ── HTML output ──────────────────────────────────────────────────────────────
html_theme          = "furo"
html_static_path    = ["_static"]
html_templates_path = ["_templates"]
html_css_files      = ["custom.css"]
html_logo           = "_static/logo.svg"
html_favicon        = "_static/logo.svg"
html_show_sphinx    = False
html_title          = project
html_short_title    = project

html_theme_options = {
    "navigation_with_keys": True,   # j/k keyboard nav between pages
    "top_of_page_buttons":  [],     # remove "view source" / "edit" clutter
    "light_css_variables":  {},     # reserved — Catppuccin Latte port goes here
    "dark_css_variables":   {},     # reserved — Catppuccin Mocha port goes here
}
```

- [ ] **Step 5: Rewrite `layout.html`**

Replace the entire content of `docs/hdl_autodoc/_templates/layout.html`:

```jinja
{# layout.html — HDL AutoDoc theme override for Furo #}
{% extends "!layout.html" %}

{% block extrahead %}
  {{ super() }}
  <meta name="author" content="{{ author }}"/>
  <meta name="description" content="{{ project }} HDL documentation"/>
{% endblock %}

{% block page_footer %}
  <div class="hdl-footer">
    Built with <a href="https://www.sphinx-doc.org" target="_blank">Sphinx</a>
    &nbsp;&middot;&nbsp;
    <a href="https://wavedrom.com" target="_blank">WaveDrom</a>
    &nbsp;&middot;&nbsp;
    <a href="https://graphviz.org" target="_blank">Graphviz</a>
  </div>
{% endblock %}
```

- [ ] **Step 6: Delete `breadcrumbs.html` and `theme.js`**

```bash
git rm docs/hdl_autodoc/_templates/breadcrumbs.html
git rm docs/hdl_autodoc/_static/theme.js
```

Expected: both files staged for deletion.

- [ ] **Step 7: Commit**

```bash
git add requirements.txt docs/hdl_autodoc/conf.py docs/hdl_autodoc/_templates/layout.html
git commit -m "feat: migrate to Furo theme — update requirements, conf.py, and templates"
```

---

## Task 2: CSS cleanup

**Files:**
- Modify: `docs/hdl_autodoc/_static/custom.css`

### Context

The current CSS has large RTD-specific blocks that must go:
- `.wy-nav-content-wrap`, `.wy-nav-content`, `.wy-nav-content > .rst-content` — RTD layout wrappers
- `.rst-content, .document, .section, .body` — RTD content class
- The entire Sidebar section (`.wy-nav-side`, `.wy-side-nav-search`, `.wy-menu-vertical`) — RTD sidebar
- `.hdl-sidebar-brand`, `.hdl-logo`, `.hdl-project-name`, `.hdl-project-version` — RTD sidebar brand overrides (Furo handles logo/title natively)
- `.wy-breadcrumbs` — RTD breadcrumbs
- `#hdl-toggle` and all `.hdl-toggle-*` rules — custom dark/light toggle replaced by Furo's native toggle

The `.rst-content` prefix on the table `td`/`tr` rules (lines 421–441) added RTD specificity — drop the prefix, the rules still apply to `table.docutils`.

**Keep unchanged:** `:root` Latte variables, `[data-theme="dark"]` Mocha variables (Furo sets `data-theme="dark"` on `<html>`, so these activate automatically), base styles, headings, links, code blocks, admonitions, WaveDrom, Graphviz, rubric, badge, footer CSS class, coverage table, bus-group port table, register map tables.

- [ ] **Step 1: Replace `custom.css` with the cleaned version**

Write the following as the complete new `docs/hdl_autodoc/_static/custom.css`:

```css
/* =============================================================================
   HDL AutoDoc — Catppuccin Theme

   Light mode: Catppuccin Latte
   Dark mode:  Catppuccin Mocha

   Style guide: https://github.com/catppuccin/catppuccin/blob/main/docs/style-guide.md

   Mapping (applied to both flavours per style guide):
     Background pane      → Base
     Secondary panes      → Mantle, Crust
     Surface elements     → Surface 0, Surface 1, Surface 2
     Body copy            → Text
     Headlines            → Text
     Sub-headlines/labels → Subtext 1, Subtext 0
     Subtle text          → Overlay 1
     On-accent text       → Base
     Links / URLs         → Blue
     Success              → Green
     Warnings             → Yellow
     Errors               → Red
     Tags / pills         → Blue
     Selection bg         → Overlay 2 @ 20–30% opacity
   ============================================================================= */

/* ── Google Fonts ─────────────────────────────────────────────────────────── */
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600&family=IBM+Plex+Sans:wght@400;500;600;700&display=swap');


/* ── Catppuccin Latte — Light mode ───────────────────────────────────────── */
:root {
  /* Full Latte palette */
  --ctp-rosewater:  #dc8a78;
  --ctp-flamingo:   #dd7878;
  --ctp-pink:       #ea76cb;
  --ctp-mauve:      #8839ef;
  --ctp-red:        #d20f39;
  --ctp-maroon:     #e64553;
  --ctp-peach:      #fe640b;
  --ctp-yellow:     #df8e1d;
  --ctp-green:      #40a02b;
  --ctp-teal:       #179299;
  --ctp-sky:        #04a5e5;
  --ctp-sapphire:   #209fb5;
  --ctp-blue:       #1e66f5;
  --ctp-lavender:   #7287fd;
  --ctp-text:       #4c4f69;
  --ctp-subtext1:   #5c5f77;
  --ctp-subtext0:   #6c6f85;
  --ctp-overlay2:   #7c7f93;
  --ctp-overlay1:   #8c8fa1;
  --ctp-overlay0:   #9ca0b0;
  --ctp-surface2:   #acb0be;
  --ctp-surface1:   #bcc0cc;
  --ctp-surface0:   #ccd0da;
  --ctp-base:       #eff1f5;
  --ctp-mantle:     #e6e9ef;
  --ctp-crust:      #dce0e8;

  /* Style guide semantic mappings */
  --bg:             var(--ctp-base);       /* Background pane         */
  --bg-secondary:   var(--ctp-mantle);     /* Secondary panes         */
  --bg-tertiary:    var(--ctp-crust);      /* Tertiary / deep bg      */
  --surface-0:      var(--ctp-surface0);   /* Surface elements        */
  --surface-1:      var(--ctp-surface1);   /* Raised surfaces         */
  --surface-2:      var(--ctp-surface2);   /* Highest surfaces        */
  --overlay-0:      var(--ctp-overlay0);   /* Overlays                */
  --overlay-1:      var(--ctp-overlay1);   /* Subtle text             */
  --overlay-2:      var(--ctp-overlay2);   /* Selection bg base       */
  --text:           var(--ctp-text);       /* Body copy + headlines   */
  --subtext-1:      var(--ctp-subtext1);   /* Sub-headlines / labels  */
  --subtext-0:      var(--ctp-subtext0);   /* Labels                  */
  --accent:         var(--ctp-blue);       /* Links / URLs / tags     */
  --on-accent:      var(--ctp-base);       /* Text on accent bg       */
  --success:        var(--ctp-green);      /* Success                 */
  --warning:        var(--ctp-yellow);     /* Warnings                */
  --error:          var(--ctp-red);        /* Errors                  */
  --note:           var(--ctp-mauve);      /* Notes (extra)           */
  --tip:            var(--ctp-teal);       /* Tips / hints            */
  --selection-bg:   rgba(148, 156, 187, 0.25); /* Overlay2 @ 25%     */

  /* Code block uses deepest surface */
  --code-bg:        var(--ctp-mantle);
  --code-text:      var(--ctp-text);

  --f-body:  'IBM Plex Sans', system-ui, sans-serif;
  --f-mono:  'IBM Plex Mono', 'Fira Code', monospace;
  --f-size:  15px;
  --radius:  6px;
  --shadow:  0 1px 3px rgba(0,0,0,0.2), 0 4px 12px rgba(0,0,0,0.1);
  --content-max: clamp(640px, calc(100vw - 300px), 1800px);
  --transition: 0.2s ease;
}


/* ── Catppuccin Mocha — Dark mode ────────────────────────────────────────── */
/* Furo sets data-theme="dark" on <html> — same selector, activates automatically */
[data-theme="dark"] {
  /* Full Mocha palette */
  --ctp-rosewater:  #f5e0dc;
  --ctp-flamingo:   #f2cdcd;
  --ctp-pink:       #f5c2e7;
  --ctp-mauve:      #cba6f7;
  --ctp-red:        #f38ba8;
  --ctp-maroon:     #eba0ac;
  --ctp-peach:      #fab387;
  --ctp-yellow:     #f9e2af;
  --ctp-green:      #a6e3a1;
  --ctp-teal:       #94e2d5;
  --ctp-sky:        #89dceb;
  --ctp-sapphire:   #74c7ec;
  --ctp-blue:       #89b4fa;
  --ctp-lavender:   #b4befe;
  --ctp-text:       #cdd6f4;
  --ctp-subtext1:   #bac2de;
  --ctp-subtext0:   #a6adc8;
  --ctp-overlay2:   #9399b2;
  --ctp-overlay1:   #7f849c;
  --ctp-overlay0:   #6c7086;
  --ctp-surface2:   #585b70;
  --ctp-surface1:   #45475a;
  --ctp-surface0:   #313244;
  --ctp-base:       #1e1e2e;
  --ctp-mantle:     #181825;
  --ctp-crust:      #11111b;

  /* Same semantic mappings — palette values differ, roles are identical */
  --bg:             var(--ctp-base);
  --bg-secondary:   var(--ctp-mantle);
  --bg-tertiary:    var(--ctp-crust);
  --surface-0:      var(--ctp-surface0);
  --surface-1:      var(--ctp-surface1);
  --surface-2:      var(--ctp-surface2);
  --overlay-0:      var(--ctp-overlay0);
  --overlay-1:      var(--ctp-overlay1);
  --overlay-2:      var(--ctp-overlay2);
  --text:           var(--ctp-text);
  --subtext-1:      var(--ctp-subtext1);
  --subtext-0:      var(--ctp-subtext0);
  --accent:         var(--ctp-blue);
  --on-accent:      var(--ctp-base);
  --success:        var(--ctp-green);
  --warning:        var(--ctp-yellow);
  --error:          var(--ctp-red);
  --note:           var(--ctp-mauve);
  --tip:            var(--ctp-teal);
  --selection-bg:   rgba(147, 153, 178, 0.25);

  --code-bg:        var(--ctp-crust);
  --code-text:      var(--ctp-text);
}


/* ── Base ─────────────────────────────────────────────────────────────────── */
*, *::before, *::after { box-sizing: border-box; }

html {
  transition: background var(--transition), color var(--transition);
}

body {
  font-family: var(--f-body);
  font-size: var(--f-size);
  color: var(--text);
  line-height: 1.7;
}

::selection {
  background: var(--selection-bg);
  color: var(--text);
}

code, pre, tt, kbd, samp, .highlight {
  font-family: var(--f-mono) !important;
}


/* ── Headings — Text per style guide ─────────────────────────────────────── */
h1, h2, h3, h4, h5, h6 {
  font-family: var(--f-body);
  color: var(--text);
  transition: color var(--transition);
}

h1 {
  font-size: 1.9em;
  font-weight: 700;
  border-bottom: 2px solid var(--accent);
  padding-bottom: 0.4em;
  margin-bottom: 0.8em;
}

h2 {
  font-size: 1.4em;
  font-weight: 600;
  border-bottom: 1px solid var(--surface-1);
  padding-bottom: 0.3em;
  margin-top: 2em;
  color: var(--subtext-1);
}

h3 {
  font-size: 1.15em;
  color: var(--subtext-0);
}

h4, h5, h6 {
  color: var(--overlay-2);
}


/* ── Links — Blue per style guide ────────────────────────────────────────── */
a {
  color: var(--accent);
  text-decoration: none;
  transition: opacity var(--transition);
}

a:hover { opacity: 0.8; text-decoration: underline; }


/* ── Code blocks ──────────────────────────────────────────────────────────── */
div[class^="highlight"] pre,
.highlight pre, pre {
  background: var(--code-bg) !important;
  color: var(--code-text) !important;
  border: 1px solid var(--surface-1) !important;
  border-left: 3px solid var(--accent) !important;
  border-radius: var(--radius) !important;
  padding: 1rem 1.2rem !important;
  font-size: 0.88em !important;
  line-height: 1.6 !important;
  overflow-x: auto;
  box-shadow: var(--shadow);
}

/* Inline code */
code.literal, tt.literal {
  background: var(--surface-0);
  color: var(--ctp-peach);
  border: 1px solid var(--surface-1);
  border-radius: 3px;
  padding: 1px 6px;
  font-size: 0.9em;
  transition: background var(--transition);
}


/* ── Tables ───────────────────────────────────────────────────────────────── */
table.docutils {
  width: 100%;
  border-collapse: collapse;
  background: transparent;
  border: 1px solid var(--surface-0);
  border-radius: var(--radius);
  overflow: hidden;
  font-size: 0.9em;
  transition: background var(--transition), border-color var(--transition);
}

table.docutils th {
  background: transparent;
  color: var(--overlay-2);
  font-weight: 600;
  font-family: var(--f-mono);
  font-size: 0.78em;
  letter-spacing: 0.07em;
  text-transform: uppercase;
  padding: 0.55rem 1rem;
  border-bottom: 1px solid var(--surface-1);
}

table.docutils td,
table.docutils tr:nth-child(odd) td,
table.docutils tr:nth-child(even) td {
  padding: 0.55rem 1rem;
  border-bottom: 1px solid var(--surface-0) !important;
  color: var(--text) !important;
  background: var(--bg) !important;
  vertical-align: middle;
  transition: color var(--transition), border-color var(--transition);
}

table.docutils tr:last-child td { border-bottom: none !important; }

/* Gentle stripe */
table.docutils tr:nth-child(even) td {
  background: rgba(124, 127, 147, 0.06) !important;
}

table.docutils tr:hover td {
  background: var(--selection-bg) !important;
}

table.docutils td:first-child {
  font-family: var(--f-mono);
  font-weight: 600;
  color: var(--subtext-1);
}


/* ── Admonitions — per style guide colour roles ───────────────────────────── */
.admonition {
  background: var(--surface-0);
  border: 1px solid var(--surface-1);
  border-left: 4px solid var(--accent);
  border-radius: var(--radius);
  padding: 1rem 1.2rem;
  margin: 1.5em 0;
  box-shadow: var(--shadow);
  color: var(--text);
  transition: background var(--transition);
}

.admonition-title {
  font-family: var(--f-mono);
  font-size: 0.78em;
  font-weight: 600;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--accent);
  margin-bottom: 0.5rem;
}

/* Warning → Yellow */
.admonition.warning {
  border-left-color: var(--warning);
}
.admonition.warning .admonition-title {
  color: var(--warning);
}

/* Error / Danger → Red */
.admonition.danger,
.admonition.error {
  border-left-color: var(--error);
}
.admonition.danger .admonition-title,
.admonition.error .admonition-title {
  color: var(--error);
}

/* Tip / Hint → Teal (Green family) */
.admonition.tip,
.admonition.hint {
  border-left-color: var(--tip);
}
.admonition.tip .admonition-title,
.admonition.hint .admonition-title {
  color: var(--tip);
}

/* Note → Mauve (extra semantic colour) */
.admonition.note {
  border-left-color: var(--note);
}
.admonition.note .admonition-title {
  color: var(--note);
}

/* Important → Peach */
.admonition.important {
  border-left-color: var(--ctp-peach);
}
.admonition.important .admonition-title {
  color: var(--ctp-peach);
}


/* ── WaveDrom ─────────────────────────────────────────────────────────────── */
.wavedrom {
  display: block;
  margin: 2em auto;
  text-align: center;
  background: var(--surface-0);
  border: 1px solid var(--surface-1);
  border-radius: var(--radius);
  padding: 1.5rem;
  box-shadow: var(--shadow);
}


/* ── Graphviz ─────────────────────────────────────────────────────────────── */
.graphviz {
  background: var(--surface-0);
  border: 1px solid var(--surface-1);
  border-radius: var(--radius);
  padding: 1rem;
  box-shadow: var(--shadow);
  margin: 1.5em 0;
}

.graphviz svg {
  max-width: 100%;
  height: auto;
  display: block;
  margin: 0 auto;
}


/* ── Process name rubric headings ────────────────────────────────────────── */
p.rubric {
  font-family: var(--f-mono);
  font-size: 0.85em;
  font-weight: 600;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--subtext-1);
  border-left: 3px solid var(--accent);
  padding-left: 0.75rem;
  margin-top: 2em;
}


/* ── Build badge ─────────────────────────────────────────────────────────── */
.hdl-build-badge {
  background: var(--accent);
  color: var(--on-accent);
  padding: 2px 8px;
  border-radius: 3px;
  font-size: 0.78em;
  font-family: var(--f-mono);
  font-weight: 600;
}


/* ── Footer ───────────────────────────────────────────────────────────────── */
.hdl-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.9rem 1.5rem;
  background: var(--bg-secondary);
  border-top: 1px solid var(--surface-0);
  font-size: 0.78em;
  color: var(--overlay-1);
  flex-wrap: wrap;
  gap: 0.5rem;
  font-family: var(--f-mono);
  transition: background var(--transition), border-color var(--transition);
}

.hdl-footer a { color: var(--accent); }
.hdl-footer a:hover { text-decoration: underline; }


/* ── Coverage table ──────────────────────────────────────────────────────── */

.coverage-table {
  border-collapse: collapse;
  width: 100%;
  margin: 1.5rem 0;
  font-family: var(--f-body);
  font-size: 0.9em;
}

.coverage-table th,
.coverage-table td {
  padding: 0.45rem 0.8rem;
  border: 1px solid var(--surface-0);
  text-align: center;
}

.coverage-table th:first-child,
.coverage-table td:first-child {
  text-align: left;
}

.coverage-table thead tr {
  background: var(--bg-secondary);
  font-weight: 600;
  color: var(--subtext-1);
}

.coverage-table tfoot tr {
  background: var(--bg-secondary);
  font-weight: 600;
  color: var(--subtext-1);
}

.cov-yes {
  background: color-mix(in srgb, var(--ctp-green) 18%, transparent);
  color: var(--success);
  font-weight: 600;
}

.cov-no {
  background: color-mix(in srgb, var(--surface-0) 60%, transparent);
  color: var(--overlay-1);
}

.cov-count {
  background: color-mix(in srgb, var(--ctp-blue) 12%, transparent);
  color: var(--accent);
  font-weight: 500;
}

/* ── Bus-group port table ─────────────────────────────────────────────────── */

.port-table {
  border-collapse: collapse;
  width: 100%;
  margin: 1.5rem 0;
  font-family: var(--f-body);
  font-size: 0.9em;
}

.port-table th,
.port-table td {
  padding: 0.45rem 0.8rem;
  border: 1px solid var(--surface-0);
  text-align: left;
}

.port-table thead tr {
  background: var(--bg-secondary);
  font-weight: 600;
  color: var(--subtext-1);
}

.bus-group-row td {
  background: var(--surface-1);
  padding: 0;
}

.bus-group-row summary {
  cursor: pointer;
  padding: 0.45rem 0.8rem;
  font-family: var(--f-mono);
}

.bus-ports-inner {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.9em;
  margin: 0.25rem 0 0.25rem 1.5rem;
}

.bus-ports-inner td {
  padding: 0.3rem 0.6rem;
  border: none;
  border-bottom: 1px solid var(--surface-0);
}

/* ── Register map tables ──────────────────────────────────────────────────── */

table.register-table {
  table-layout: fixed;
  width: 100%;
}

table.register-table th,
table.register-table td {
  overflow-wrap: break-word;
  word-break: break-word;
}
```

- [ ] **Step 2: Verify line count is reasonable**

```bash
wc -l docs/hdl_autodoc/_static/custom.css
```

Expected: approximately 330–360 lines (down from ~791).

- [ ] **Step 3: Commit**

```bash
git add docs/hdl_autodoc/_static/custom.css
git commit -m "style: strip RTD-specific CSS; keep Catppuccin variables and component rules for Furo"
```

---

## Task 3: Build verification

**Files:** None modified — run build and fix any issues found.

### Context

After installing Furo and applying all changes, `make html` should complete without errors. Furo's `html_theme_options` key `navigation_with_keys` requires Furo ≥ 2023.x — current stable versions support it.

The 10 acceptance criteria from the spec are the checklist. These are visual/browser checks — verify them by opening `docs/hdl_autodoc/_build/html/index.html` in a browser.

- [ ] **Step 1: Run full build**

```bash
make html 2>&1 | tail -10
```

Expected: `Documentation built: docs/hdl_autodoc/_build/html/index.html` with no `ERROR` or `WARNING` lines about unknown theme options or missing templates.

If Furo raises `ValueError: unsupported theme option 'navigation_with_keys'`, this means the installed Furo is older than expected — replace it with `"sidebar_hide_name": True` as the only option and remove `navigation_with_keys`.

- [ ] **Step 2: Verify HTML output exists**

```bash
test -f docs/hdl_autodoc/_build/html/index.html && echo "OK"
test -f docs/hdl_autodoc/_build/html/modules/counter/registers.html && echo "OK"
test -f docs/hdl_autodoc/_build/html/registers.html && echo "OK"
```

Expected: `OK` three times.

- [ ] **Step 3: Verify theme.js is NOT in the build output**

```bash
test ! -f docs/hdl_autodoc/_build/html/_static/theme.js && echo "OK - theme.js absent"
```

Expected: `OK - theme.js absent`

- [ ] **Step 4: Spot-check that Furo's built-in JS is present**

```bash
ls docs/hdl_autodoc/_build/html/_static/*.js | head -5
```

Expected: Furo's own JS files present (e.g. `documentation_options.js`, `furo.js` or similar). The old RTD files (`theme.js`) should not appear.

- [ ] **Step 5: Open the built docs and verify acceptance criteria**

Open `docs/hdl_autodoc/_build/html/index.html` in a browser and verify:

1. Site builds and displays without JS errors in browser console
2. Ctrl+K / Cmd+K opens the Furo search modal
3. Searching returns results with context snippets
4. Dark/light toggle (top-right) persists across page navigation
5. FSM `.dot` diagrams render on a module's FSM page
6. WaveDrom timing diagrams render on a timing page
7. Register tables render with correct column widths (no overflow)
8. Logo and favicon appear in the sidebar and browser tab
9. Footer attribution ("Built with Sphinx · WaveDrom · Graphviz") is visible at the bottom of pages
10. PDF build works: `make pdf` succeeds (Furo is HTML-only; PDF still uses LaTeX)

- [ ] **Step 6: Commit verification (add any minor CSS tweaks discovered during review)**

If any minor tweaks were needed (e.g. logo sizing, footer margin), commit them:

```bash
git add docs/hdl_autodoc/_static/custom.css  # only if tweaks were made
git commit -m "style: Furo post-build CSS tweaks — [describe what was adjusted]"
```

If no tweaks were needed, skip this step.

- [ ] **Step 7: Tag the branch as ready for review**

```bash
git log --oneline feat/furo-theme ^main
```

Expected: 2–3 commits listed (Task 1 commit, Task 2 commit, optional Task 3 tweak commit).
