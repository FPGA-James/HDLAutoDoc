# conf.py — Sphinx configuration for VHDL HDL documentation

import os
from datetime import date

# ── Project metadata ─────────────────────────────────────────────────────────
project   = "Traffic Light Controller"
author    = "HDL Team"
copyright = f"{date.today().year}, HDL Team"
release   = "1.0.0"

# ── Extensions ───────────────────────────────────────────────────────────────
extensions = [
    "sphinx.ext.graphviz",       # FSM diagrams via graphviz/dot
    "sphinxcontrib.wavedrom",    # .. wavedrom:: directive
    "sphinxvhdl.vhdl",           # vhdl:autoentity:: auto-documentation
]

# ── WaveDrom ─────────────────────────────────────────────────────────────────
wavedrom_html_jsinline = False
online_wavedrom_js_url = "https://cdnjs.cloudflare.com/ajax/libs/wavedrom/3.3.0/wavedrom.min.js"
online_skin_js_url     = "https://cdnjs.cloudflare.com/ajax/libs/wavedrom/3.3.0/skins/default.js"

# ── Graphviz ─────────────────────────────────────────────────────────────────
graphviz_output_format = "svg"

# ── sphinx-vhdl ──────────────────────────────────────────────────────────────
vhdl_autodoc_source_path = os.path.normpath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "../src")
)

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
    "navigation_depth":    4,
    "collapse_navigation": False,
    "sticky_navigation":   True,
    "includehidden":       True,
    "titles_only":         False,
}

# ── LaTeX / PDF output ────────────────────────────────────────────────────────
latex_elements = {
    'fncychap':   '',
    'printindex': '',
    'preamble': r"""
\makeatletter
\@ifpackageloaded{wrapfig}{}{%
  \newenvironment{wrapfigure}[2][]{\begin{figure}[htbp]}{\end{figure}}%
  \newenvironment{wraptable}[2][]{\begin{table}[htbp]}{\end{table}}%
}
\makeatother
""",
}

# ── Source ────────────────────────────────────────────────────────────────────
source_suffix    = ".rst"
master_doc       = "index"
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]