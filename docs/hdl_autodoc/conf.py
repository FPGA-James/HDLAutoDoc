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
# Walk up from conf.py to find src/ — works regardless of how deep docs/ is
_conf_dir = os.path.dirname(os.path.abspath(__file__))
_root = _conf_dir
for _ in range(6):
    _candidate = os.path.join(_root, "src")
    if os.path.isdir(_candidate):
        break
    _root = os.path.dirname(_root)
# sphinx-vhdl requires a list, not a bare string
vhdl_autodoc_source_path = [_candidate]

# ── HTML output ──────────────────────────────────────────────────────────────
html_theme          = "furo"
html_static_path    = ["_static"]
html_css_files      = ["custom.css"]
html_logo           = "_static/logo.svg"
html_favicon        = "_static/logo.svg"
html_show_sphinx    = False
html_title          = project
html_short_title    = project

# ── Template overrides ────────────────────────────────────────────────────────
templates_path      = ["_templates"]

html_theme_options = {
    "top_of_page_buttons":  [],     # remove "view source" / "edit" clutter
    "light_css_variables":  {},     # reserved — Catppuccin Latte port goes here
    "dark_css_variables":   {},     # reserved — Catppuccin Mocha port goes here
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