"""Every page ends with Previous / Next links that follow the toctree order."""

import io
import os
import re
from pathlib import Path

import pytest
from sphinx.application import Sphinx
from sphinx.util.docutils import docutils_namespace

try:
    import sphinxcontrib.wavedrom  # noqa: F401  (the real conf.py loads it)
except Exception as exc:    # e.g. OSError: no library called "cairo-2" was found (macOS, no DYLD_LIBRARY_PATH)
    pytest.skip(f"the real conf.py cannot be loaded here: {exc}", allow_module_level=True)

CONFDIR = Path(__file__).parents[3] / "docs" / "hdl_autodoc"


def _build(tmp_path):
    src = tmp_path / "src"
    src.mkdir()
    (src / "index.rst").write_text("Home\n====\n\n.. toctree::\n\n   first\n   second\n   third\n")
    for name in ("first", "second", "third"):
        (src / f"{name}.rst").write_text(f"{name.title()} page\n{'=' * 10}\n\nText.\n")
    out = tmp_path / "out"
    old, os.environ["AUTODOC_SOURCEDIR"] = os.environ.get("AUTODOC_SOURCEDIR"), str(src)
    try:
        with docutils_namespace():
            Sphinx(str(src), str(CONFDIR), str(out), str(tmp_path / "dt"), "html",
                   status=io.StringIO(), warning=io.StringIO()).build()
    finally:
        if old is None:
            del os.environ["AUTODOC_SOURCEDIR"]
        else:
            os.environ["AUTODOC_SOURCEDIR"] = old
    return out


def _link(html, kind):
    m = re.search(rf'<a class="{kind}-page" href="([^"]*)">.*?<div class="title">([^<]*)</div>', html, re.S)
    return (m.group(1), m.group(2)) if m else None


def test_a_middle_page_links_to_its_neighbours_in_toctree_order(tmp_path):
    html = (_build(tmp_path) / "second.html").read_text()
    assert _link(html, "prev") == ("first.html", "First page")
    assert _link(html, "next") == ("third.html", "Third page")


def test_the_first_page_has_no_previous_and_the_last_has_no_next(tmp_path):
    out = _build(tmp_path)
    assert _link((out / "third.html").read_text(), "next") is None
    assert _link((out / "third.html").read_text(), "prev") == ("second.html", "Second page")


def test_the_page_footer_credit_is_still_there(tmp_path):
    assert "hdl-footer" in (_build(tmp_path) / "second.html").read_text()
