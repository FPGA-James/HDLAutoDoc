"""Tests for rst_escape.escape_rst."""

import io

import pytest

from rst_escape import escape_rst


def _docutils_problems(rst: str) -> str:
    """Everything docutils reports (warnings and errors) when parsing `rst`."""
    docutils_core = pytest.importorskip("docutils.core")
    stream = io.StringIO()
    docutils_core.publish_doctree(rst, settings_overrides={
        "warning_stream": stream, "report_level": 2, "halt_level": 5})
    return stream.getvalue()


def test_markup_characters_are_escaped():
    assert escape_rst("a*b `c` | d") == "a\\*b \\`c\\` \\| d"
    assert escape_rst("back\\slash") == "back\\\\slash"


def test_underscores_inside_a_word_are_left_alone():
    assert escape_rst("reset_clears_fifo") == "reset_clears_fifo"


def test_a_trailing_underscore_is_escaped_before_space_punctuation_and_end():
    assert escape_rst("x_ y") == "x\\_ y"
    assert escape_rst("drives a_, b_.") == "drives a\\_, b\\_."
    assert escape_rst("ends_") == "ends\\_"
    assert escape_rst("a__ b") == "a\\_\\_ b"


@pytest.mark.parametrize("text", ["drives a_, b_.", "a__ b", "see x_ and y_", "tail_",
                                  "uses * and `c` and |bars|", "reset_clears_fifo is fine"])
def test_escaped_text_gives_docutils_no_errors_or_warnings(text):
    assert _docutils_problems(f"Paragraph: {escape_rst(text)}\n") == ""


def test_the_unescaped_text_really_would_have_errored():
    """Guards the test above: without escaping, docutils does complain."""
    assert "Unknown target name" in _docutils_problems("Paragraph: drives a_, b_.\n")
