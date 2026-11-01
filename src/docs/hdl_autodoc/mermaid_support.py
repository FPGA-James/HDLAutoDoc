"""
mermaid_support.py
------------------
Mermaid helpers for conf.py: settings taken from the environment, and a LaTeX
fallback for when `mmdc` (mermaid-cli) is not installed.

HTML needs no setup: Mermaid is rendered by JavaScript in the browser.  The PDF
needs each diagram rendered to an image, which only `mmdc` can do.  Without it
sphinxcontrib-mermaid leaves an empty captioned figure and warns once per
diagram; here the diagram is replaced by a one-line note and a single
informational message says how many were left out.

Environment variables (set by autodoc.mk; all optional):
    AUTODOC_MERMAID_CMD     command that renders diagrams        (default: mmdc)
    AUTODOC_MERMAID_PARAMS  extra arguments for it, shell-quoted (default: none)
    AUTODOC_MERMAID_JS      where HTML loads mermaid.js from: a path relative to the site's
                            _static/ folder, or an https:// URL (default: a CDN)
"""
from __future__ import annotations

import shlex
import shutil
from collections.abc import Mapping

from docutils import nodes
from sphinx.util import logging
from sphinxcontrib import mermaid as mermaid_ext
from sphinxcontrib.mermaid import mermaid

logger = logging.getLogger("hdl_autodoc.mermaid")

NOTE = "Diagram omitted from the PDF: install mermaid-cli (mmdc) to include it."


def mermaid_settings(environ: Mapping[str, str]) -> dict:
    """sphinxcontrib-mermaid configuration values from the environment."""
    return {
        "mermaid_cmd":       (environ.get("AUTODOC_MERMAID_CMD") or "").strip() or "mmdc",
        "mermaid_params":    shlex.split(environ.get("AUTODOC_MERMAID_PARAMS") or ""),
        "mermaid_use_local": (environ.get("AUTODOC_MERMAID_JS") or "").strip(),
    }


def _program(command: str) -> str:
    """The program in a render command, as the extension splits it (arguments may follow;
    a space in the path is written `\\ `)."""
    try:
        parts = shlex.split(command)
    except ValueError:
        parts = command.split()
    return parts[0] if parts else command


def omit_unrendered_diagrams(app, doctree, docname) -> None:
    """
    `doctree-resolved` handler.  For the LaTeX builder, when the render command is
    not available, replace every Mermaid node with a note and count them.
    """
    if app.builder.name != "latex" or shutil.which(_program(app.config.mermaid_cmd)) is not None:
        return
    found = list(doctree.findall(mermaid))
    for node in found:
        # A captioned diagram sits in a figure; replace the whole figure, or the PDF
        # would hold a numbered "Figure" that contains only the note.
        target = node.parent if isinstance(node.parent, nodes.figure) else node
        target.replace_self(nodes.paragraph("", NOTE))
    app._hdl_mermaid_omitted = getattr(app, "_hdl_mermaid_omitted", 0) + len(found)


def report_omitted_diagrams(app, exception) -> None:
    """`build-finished` handler: one message for all documents."""
    count = getattr(app, "_hdl_mermaid_omitted", 0)
    if count:
        logger.info(
            f"{count} Mermaid diagram{'s' if count != 1 else ''} omitted from the PDF: "
            f"mermaid-cli ({_program(app.config.mermaid_cmd)}) was not found. Install it, "
            f"or set AUTODOC_MERMAID_CMD, to include them.")


def install_js_for_documents_only(app, pagename, templatename, context, doctree) -> None:
    """
    `html-page-context` handler replacing the extension's own.  The extension skips a
    page that has a document but no diagram, yet adds its script to pages that have no
    document at all (the index and search pages), so every project's index and search
    page would fetch Mermaid from a CDN.  Pages without a document cannot contain a
    diagram; leave them alone.
    """
    if doctree is None:
        return
    mermaid_ext.install_js(app, pagename, templatename, context, doctree)


def setup_mermaid(app) -> None:
    app.connect("doctree-resolved", omit_unrendered_diagrams)
    app.connect("build-finished", report_omitted_diagrams)

    for listener in list(app.events.listeners.get("html-page-context", [])):
        if listener.handler is mermaid_ext.install_js:
            app.disconnect(listener.id)
    app.connect("html-page-context", install_js_for_documents_only)
