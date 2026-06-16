"""Tests for the has_coverage guard in generate_rst.index_rst()."""

from generate_rst import index_rst

_ENTITIES = [{"name": "blinky", "file": "src/blinky.vhd", "brief": ""}]
_HIERARCHY = {"top": "blinky", "modules": {"blinky": {"children": [], "parents": []}}}


def test_coverage_not_in_toctree_by_default():
    rst = index_rst(_ENTITIES, "TestProject", _HIERARCHY)
    assert "coverage" not in rst


def test_coverage_in_toctree_when_has_coverage_true():
    rst = index_rst(_ENTITIES, "TestProject", _HIERARCHY, has_coverage=True)
    assert "   coverage" in rst


def test_coverage_entry_position_after_hierarchy():
    rst = index_rst(_ENTITIES, "TestProject", _HIERARCHY, has_coverage=True)
    pos_hierarchy = rst.index("   hierarchy")
    pos_coverage  = rst.index("   coverage")
    assert pos_coverage > pos_hierarchy
