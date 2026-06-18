# Furo Theme Migration — Design Spec

**Date:** 2026-06-18
**Status:** Approved
**Branch:** `feat/furo-theme`

---

## Overview

Replace the `sphinx-rtd-theme` with `furo` to gain a modern, polished documentation experience — most importantly a built-in Ctrl+K search modal and native dark/light toggle. Developed on a feature branch; `main` is untouched until the work is approved.

---

## Architecture

Five files change. All RST content, Python extractors, Makefile, and register maps are untouched.

| File | Change |
|---|---|
| `requirements.txt` | Replace `sphinx-rtd-theme>=2.0` with `furo` |
| `docs/hdl_autodoc/conf.py` | Set `html_theme = "furo"`, replace `html_theme_options`, remove `html_js_files` |
| `docs/hdl_autodoc/_static/custom.css` | Strip RTD-specific rules; keep `.register-table`; add Furo logo/footer tweaks |
| `docs/hdl_autodoc/_static/theme.js` | Delete — Furo ships its own dark/light toggle |
| `docs/hdl_autodoc/_templates/layout.html` | Rewrite for Furo block names |
| `docs/hdl_autodoc/_templates/breadcrumbs.html` | Delete — Furo renders its own breadcrumbs |

---

## `requirements.txt`

Remove:
```
sphinx-rtd-theme>=2.0
```

Add:
```
furo
```

---

## `conf.py` Changes

### Theme

```python
html_theme = "furo"
```

### Theme options

Replace the existing `html_theme_options` dict entirely:

```python
html_theme_options = {
    "navigation_with_keys": True,   # j/k keyboard nav between pages
    "top_of_page_buttons": [],      # remove "view source" / "edit" clutter
    "light_css_variables": {},      # reserved — Catppuccin Latte port goes here
    "dark_css_variables": {},       # reserved — Catppuccin Mocha port goes here
}
```

### Remove

```python
html_js_files = ["theme.js"]
```

### Keep unchanged

```python
html_static_path   = ["_static"]
html_templates_path = ["_templates"]
html_css_files     = ["custom.css"]
html_logo          = "_static/logo.svg"
html_favicon       = "_static/logo.svg"
html_show_sphinx   = False
html_title         = project
html_short_title   = project
```

---

## `_templates/layout.html`

Rewrite entirely. Furo uses different block names — the sidebar brand is handled natively via `html_logo` and `html_title`, so only the footer attribution and meta head tags require overrides:

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

---

## `_templates/breadcrumbs.html`

Delete the file. Furo renders its own breadcrumbs natively.

---

## `_static/theme.js`

Delete the file. Furo ships a dark/light toggle with `localStorage` persistence that matches the existing UX. No custom JS is needed.

---

## `_static/custom.css`

### Remove

All RTD-specific selectors and the dark/light variable blocks (`.wy-*`, `.rst-content`, `[data-theme]` colour overrides).

### Keep

The `.register-table` block for enforcing fixed column widths:

```css
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

### Add

Any minor Furo-specific tweaks discovered during build review (logo sizing, footer margin, etc.). These are determined during implementation by running the build and inspecting the output.

---

## What Furo Provides Out of the Box

- **Ctrl+K / Cmd+K search modal** with context snippets from Sphinx's existing `searchindex.js`
- **Dark/light toggle** (top-right button, `localStorage` persistence, respects OS preference)
- **Responsive layout** — sidebar collapses on mobile
- **j/k keyboard navigation** between pages (enabled via `navigation_with_keys`)
- Clean two-column layout (left sidebar + content)

---

## Future: Catppuccin Port

Furo exposes `light_css_variables` and `dark_css_variables` dicts in `html_theme_options`. Porting Catppuccin Latte/Mocha later is a conf.py-only change — no CSS file editing required. Example:

```python
"light_css_variables": {
    "--color-brand-primary": "#1e66f5",   # Catppuccin Latte Blue
    "--color-brand-content": "#1e66f5",
    # ...
},
```

---

## Testing

After `make html` on the branch, verify:

1. Site builds without warnings or errors
2. Ctrl+K / Cmd+K opens the search modal
3. Searching returns results with context snippets
4. Dark/light toggle persists across page navigation
5. All FSM `.dot` diagrams render
6. All WaveDrom timing diagrams render
7. Register tables render with correct column widths
8. Logo and favicon appear in sidebar and browser tab
9. Footer attribution ("Built with Sphinx · WaveDrom · Graphviz") is visible
10. PDF build (`make pdf`) succeeds — Furo is HTML-only; PDF output uses LaTeX regardless of `html_theme`

---

## What Does Not Change

- All RST content and Sphinx extensions (`graphviz`, `wavedrom`, `sphinxvhdl`)
- `parse_hierarchy.py`, `generate_rst.py`, `run_extract.py`, all extractors
- `Makefile` targets
- `registers/` directory and register pipeline
- `docs/hdl_autodoc/hierarchy.json`
- Module `entity.rst` files (hand-editable)
