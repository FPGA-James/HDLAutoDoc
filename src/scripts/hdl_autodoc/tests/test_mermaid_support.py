"""Tests for src/docs/hdl_autodoc/mermaid_support.py: settings and the PDF fallback."""

import io
import sys
from pathlib import Path
from types import SimpleNamespace

from docutils import nodes
from docutils.utils import new_document
from sphinx.application import Sphinx
from sphinx.util.docutils import docutils_namespace
from sphinxcontrib.mermaid import mermaid

HDL_AUTODOC_DOCS = Path(__file__).parents[3] / "docs" / "hdl_autodoc"
sys.path.insert(0, str(HDL_AUTODOC_DOCS))

import mermaid_support as ms  # noqa: E402

MISSING = "definitely-not-an-installed-command-xyz"
NOTE = "Diagram omitted from the PDF"


# ── mermaid_settings ─────────────────────────────────────────────────────────

def test_settings_defaults_when_nothing_is_set():
    assert ms.mermaid_settings({}) == {
        "mermaid_cmd": "mmdc", "mermaid_params": [], "mermaid_use_local": ""}


def test_settings_come_from_the_environment():
    s = ms.mermaid_settings({
        "AUTODOC_MERMAID_CMD": "/x/mmdc",
        "AUTODOC_MERMAID_PARAMS": "-p /x/p.json --scale 2",
        "AUTODOC_MERMAID_JS": "/x/mermaid.js",
    })
    assert s == {"mermaid_cmd": "/x/mmdc",
                 "mermaid_params": ["-p", "/x/p.json", "--scale", "2"],
                 "mermaid_use_local": "/x/mermaid.js"}


def test_blank_values_give_the_defaults():
    s = ms.mermaid_settings({"AUTODOC_MERMAID_CMD": "  ", "AUTODOC_MERMAID_PARAMS": " ",
                             "AUTODOC_MERMAID_JS": ""})
    assert s == ms.mermaid_settings({})


def test_params_may_quote_a_path_with_spaces():
    s = ms.mermaid_settings({"AUTODOC_MERMAID_PARAMS": '-p "/a b/p.json"'})
    assert s["mermaid_params"] == ["-p", "/a b/p.json"]


# ── omit_unrendered_diagrams / report_omitted_diagrams ───────────────────────

class _Recorder:
    def __init__(self):
        self.messages = []

    def info(self, message, *args, **kwargs):
        self.messages.append(message % args if args else message)


def _app(builder="latex", cmd=MISSING):
    return SimpleNamespace(builder=SimpleNamespace(name=builder),
                           config=SimpleNamespace(mermaid_cmd=cmd))


def _doctree(count=2):
    doc = new_document("test")
    section = nodes.section()
    for _ in range(count):
        section += mermaid()
    doc += section
    return doc


def _paragraph_text(doc):
    return " ".join(p.astext() for p in doc.findall(nodes.paragraph))


def test_latex_without_the_command_replaces_diagrams_with_a_note():
    doc = _doctree(2)
    ms.omit_unrendered_diagrams(_app("latex"), doc, "index")
    assert not list(doc.findall(mermaid))
    assert _paragraph_text(doc).count(NOTE) == 2
    assert "mmdc" in _paragraph_text(doc)


def test_one_info_message_states_the_count_across_documents(monkeypatch):
    rec = _Recorder()
    monkeypatch.setattr(ms, "logger", rec)
    app = _app("latex")
    ms.omit_unrendered_diagrams(app, _doctree(2), "a")
    ms.omit_unrendered_diagrams(app, _doctree(1), "b")
    assert rec.messages == []                      # nothing per document
    ms.report_omitted_diagrams(app, None)
    assert len(rec.messages) == 1
    assert "3" in rec.messages[0] and "mmdc" in rec.messages[0]


def test_no_message_when_nothing_was_omitted(monkeypatch):
    rec = _Recorder()
    monkeypatch.setattr(ms, "logger", rec)
    ms.report_omitted_diagrams(_app("latex"), None)
    assert rec.messages == []


def test_html_builder_is_untouched():
    doc = _doctree(2)
    ms.omit_unrendered_diagrams(_app("html"), doc, "index")
    assert len(list(doc.findall(mermaid))) == 2


def test_latex_with_an_available_command_is_untouched():
    doc = _doctree(2)
    ms.omit_unrendered_diagrams(_app("latex", cmd=sys.executable), doc, "index")
    assert len(list(doc.findall(mermaid))) == 2


# ── real Sphinx builds ───────────────────────────────────────────────────────

_INDEX = """\
Index
=====

.. mermaid::
   :caption: A flow

   flowchart LR
     A --> B

.. mermaid::
   :caption: Handshake

   sequenceDiagram
     Master->>Slave: valid
"""


def _build(tmp_path, builder, extra_pages=None):
    src = tmp_path / "src"
    src.mkdir()
    index = _INDEX
    for name, text in (extra_pages or {}).items():
        (src / f"{name}.rst").write_text(text)
        index += f"\n.. toctree::\n\n   {name}\n"
    (src / "index.rst").write_text(index)
    (src / "conf.py").write_text(
        f'import sys\nsys.path.insert(0, r"{HDL_AUTODOC_DOCS}")\n'
        'extensions = ["sphinxcontrib.mermaid"]\n'
        f'mermaid_cmd = "{MISSING}"\n'
        "import mermaid_support\n"
        "def setup(app):\n    mermaid_support.setup_mermaid(app)\n")
    out = tmp_path / f"out_{builder}"
    warnings, status = io.StringIO(), io.StringIO()
    # docutils keeps node registrations globally; isolate each build from the others.
    with docutils_namespace():
        app = Sphinx(str(src), str(src), str(out), str(tmp_path / f"dt_{builder}"), builder,
                     status=status, warning=warnings)
        app.build()
    return out, warnings.getvalue(), status.getvalue()


def test_latex_build_without_mmdc_has_no_warnings_and_a_single_message(tmp_path):
    out, warnings, status = _build(tmp_path, "latex")
    assert warnings == ""
    tex = next(out.glob("*.tex")).read_text()
    assert tex.count(NOTE) == 2
    assert status.count("Mermaid diagram") == 1 and "2" in status
    assert "includegraphics" not in tex            # no broken image


def test_html_build_still_renders_the_diagrams(tmp_path):
    out, warnings, _ = _build(tmp_path, "html")
    assert warnings == ""
    html = (out / "index.html").read_text()
    assert html.count('class="mermaid"') == 2 and "sequenceDiagram" in html


CDN = "cdn.jsdelivr.net/npm/mermaid"


def test_pages_without_a_diagram_never_load_the_mermaid_script(tmp_path):
    """sphinxcontrib-mermaid skips pages with a document and no diagram, but not the
    index and search pages (they have no document); those must stay script-free too."""
    out, warnings, _ = _build(tmp_path, "html", extra_pages={
        "plain": "Plain\n=====\n\n.. index:: thing\n\nNo diagrams here.\n"})
    assert warnings == ""
    assert CDN in (out / "index.html").read_text()                 # the page with diagrams
    for page in ("plain.html", "genindex.html", "search.html"):
        assert (out / page).exists(), page
        assert CDN not in (out / page).read_text(), page


# ── make doc-check-env ───────────────────────────────────────────────────────

def test_check_env_asks_for_doc_venv_when_sphinxcontrib_mermaid_is_missing(tmp_path):
    """A project upgraded to a tool that needs sphinxcontrib-mermaid, with an old
    environment, is told to run `make doc-venv` instead of getting a traceback."""
    import subprocess
    # A Python that behaves like this one except that sphinxcontrib.mermaid is not installed.
    shim = tmp_path / "python-without-mermaid"
    shim.write_text(
        "#!/bin/sh\n"
        f'exec "{sys.executable}" -c "import sys; sys.modules[\'sphinxcontrib.mermaid\'] = None; '
        'exec(sys.argv[1])" "$2"\n')
    shim.chmod(0o755)
    project = tmp_path / "project"
    project.mkdir()
    (project / "Makefile").write_text(f"include {HDL_AUTODOC_DOCS.parents[1] / 'autodoc.mk'}\n")
    result = subprocess.run(["make", "-C", str(project), "doc-check-env", f"PYTHON={shim}"],
                            capture_output=True, text=True)
    assert result.returncode != 0
    assert "make doc-venv" in result.stdout + result.stderr
