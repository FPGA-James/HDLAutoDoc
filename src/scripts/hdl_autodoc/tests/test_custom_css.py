"""Guards for layout rules in custom.css that are easy to break silently."""

import re
from pathlib import Path

CSS = (Path(__file__).parents[3] / "docs" / "hdl_autodoc" / "_static" / "custom.css").read_text()


def _rule(selector: str) -> str:
    return re.search(rf"^{re.escape(selector)}\s*{{([^}}]*)}}", CSS, re.M).group(1)


def test_breadcrumb_bar_stays_in_view_while_scrolling():
    rule = _rule(".hdl-breadcrumbs")
    assert "position: sticky" in rule and "top: 0" in rule
    assert "background" in rule          # text scrolling underneath must not show through


def test_content_does_not_become_a_scroll_container_which_would_unstick_the_bar():
    # Furo sets .content{overflow-x:auto}; any value but visible/clip breaks position:sticky.
    rules = re.findall(r"^\.content\s*{([^}]*)}", CSS, re.M)
    assert any("overflow-x: clip" in r for r in rules)
