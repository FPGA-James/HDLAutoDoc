# conf.py — Sphinx configuration for VHDL HDL documentation

import os
from datetime import date

# ── Project metadata ─────────────────────────────────────────────────────────
# autodoc.mk passes these through the environment; the defaults apply when
# conf.py is used standalone.
project   = os.environ.get("AUTODOC_PROJECT") or "Traffic Light Controller"
author    = os.environ.get("AUTODOC_AUTHOR") or "HDL Team"
copyright = f"{date.today().year}, {author}"
release   = os.environ.get("AUTODOC_RELEASE") or "1.0.0"

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
# conf.py may live outside the project (shared tool checkout) and Sphinx chdirs to
# its confdir while loading it, so autodoc.mk passes absolute project paths.
_candidate = os.path.abspath(os.environ.get("AUTODOC_SRC") or "src")
# sphinx-vhdl requires a list, not a bare string
vhdl_autodoc_source_path = [_candidate]

# ── HTML output ──────────────────────────────────────────────────────────────
html_theme          = "furo"
# Tool assets first, then the project's own _static (generated register pages
# land there). Sphinx ignores entries that do not exist.
html_static_path    = ["_static", os.path.abspath(os.path.join(os.environ.get("AUTODOC_SOURCEDIR") or "docs/hdl_autodoc", "_static"))]
templates_path      = ["_templates"]
html_css_files      = ["custom.css"]
html_js_files       = ["search-hotkey.js", "sidebar-scroll.js"]
html_logo           = "_static/logo.svg"
html_favicon        = "_static/logo.svg"
html_show_sphinx    = False
html_title          = project
html_short_title    = project

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
\usepackage{pdflscape}   % full-page rotated RTL schematics
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

# ── sphinx-vhdl incremental-build workaround ─────────────────────────────────
# sphinx-vhdl keeps "VHDL files already parsed" in the pickled environment, but
# the parsed entities live in memory.  On an incremental build (a fresh process
# reusing the pickle) it skips parsing, so every vhdl:autoentity of a re-read
# page warns "not found" and renders empty.  Reset the flag so each run parses.
def _reset_vhdl_parse_flag(app):
    app.env.domaindata.get("vhdl", {})["autodoc_initialized"] = False


def setup(app):
    app.connect("builder-inited", _reset_vhdl_parse_flag)
