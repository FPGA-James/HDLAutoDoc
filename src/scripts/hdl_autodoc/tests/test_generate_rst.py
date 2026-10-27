"""
test_generate_rst.py
--------------------
Tests for generate_rst.py.

Covers:
  - module_index_rst toctree contains the expected page entries (entity, fsm,
    timing, cdc, processes) and omits optional entries when not applicable.
  - entity_rst uses vhdl:autoentity for VHDL and literalinclude for SV.
  - cdc_rst returns a placeholder when no extracted file exists, and an
    include directive when the extracted file is present.
  - fsm_rst returns a placeholder when no extracted file exists, and an
    include directive when present.
  - write_if_missing does not overwrite an existing file.
  - write_always overwrites an existing file.
"""

from pathlib import Path

import pytest

from generate_rst import (
    cdc_rst,
    entity_rst,
    legacy_entity_rsts,
    overview_rst,
    source_rst,
    write_if_missing_or_pristine,
    fsm_rst,
    index_rst,
    module_index_rst,
    registers_rst,
    write_always,
    write_if_missing,
)


# ─────────────────────────────────────────────────────────────────────────────
# module_index_rst
# ─────────────────────────────────────────────────────────────────────────────

def _make_entity(name="my_mod", filename="my_mod.vhd"):
    return {"name": name, "brief": "A test module.", "file": filename, "ports": []}


def test_index_rst_contains_core_pages():
    """The module toctree always includes entity, fsm, timing, and cdc."""
    rst = module_index_rst(_make_entity(), children=[], shared_children=set())
    assert "entity" in rst
    assert "fsm" in rst
    assert "timing" in rst
    assert "cdc" in rst


def test_index_rst_includes_processes_when_present():
    """processes/index is added to the toctree when has_processes=True."""
    rst = module_index_rst(_make_entity(), children=[], shared_children=set(),
                           has_processes=True)
    assert "processes/index" in rst


def test_index_rst_omits_processes_when_absent():
    """processes/index is NOT added to the toctree when has_processes=False."""
    rst = module_index_rst(_make_entity(), children=[], shared_children=set(),
                           has_processes=False)
    assert "processes/index" not in rst


def test_index_rst_includes_submodules_section():
    """A 'Submodules' section is added when the module has children."""
    rst = module_index_rst(_make_entity(), children=["child_a", "child_b"],
                           shared_children=set())
    assert "Submodules" in rst
    assert "../child_a/index" in rst


def test_index_rst_no_submodules_section_when_childless():
    """No 'Submodules' section is emitted for a leaf module."""
    rst = module_index_rst(_make_entity(), children=[], shared_children=set())
    assert "Submodules" not in rst


def test_index_rst_top_includes_registers():
    """The module toctree includes the registers page when has_registers=True."""
    rst = module_index_rst(_make_entity(), children=[], shared_children=set(),
                           has_registers=True)
    assert "registers" in rst


# ─────────────────────────────────────────────────────────────────────────────
# entity_rst
# ─────────────────────────────────────────────────────────────────────────────

def test_entity_rst_vhdl_uses_autoentity():
    """VHDL entity pages use the vhdl:autoentity directive."""
    entity = _make_entity(filename="my_mod.vhd")
    rst = entity_rst(entity)
    assert "vhdl:autoentity" in rst


def test_entity_rst_sv_has_no_autoentity_and_includes_the_source_section():
    """SV has no sphinx-vhdl support; the listing comes from the included source page."""
    entity = _make_entity(name="my_mod", filename="my_mod.sv")
    rst = entity_rst(entity)
    assert "vhdl:autoentity" not in rst
    assert ".. include:: my_mod_source.rst" in rst
    assert "literalinclude" not in rst   # lives in <name>_source.rst now
    assert "literalinclude" in source_rst(entity)
    assert ":language: systemverilog" in source_rst(entity)


def test_entity_rst_sv_includes_module_description(tmp_path):
    """The // block above `module` is rendered as the SV entity description."""
    (tmp_path / "my_mod.sv").write_text(
        "// My module.\n//\n// Does a thing.\n"
        "module my_mod (input logic clk);\nendmodule\n"
    )
    entity = _make_entity(name="my_mod", filename="my_mod.sv")
    rst = entity_rst(entity, src_dir=tmp_path)
    assert "My module.\n\nDoes a thing." in rst
    assert rst.index("Does a thing.") < rst.index(".. include:: my_mod_source.rst")


def test_entity_rst_sv_no_description_when_no_comment(tmp_path):
    """No stray text is emitted when the module has no leading comment."""
    (tmp_path / "my_mod.sv").write_text("module my_mod (input logic clk);\nendmodule\n")
    entity = _make_entity(name="my_mod", filename="my_mod.sv")
    with_src = entity_rst(entity, src_dir=tmp_path)
    assert with_src == entity_rst(entity)


def test_entity_rst_contains_source_filename():
    """The entity page mentions the HDL source filename."""
    entity = _make_entity(filename="counter.vhd")
    rst = entity_rst(entity)
    assert "counter.vhd" in rst


# ─────────────────────────────────────────────────────────────────────────────
# cdc_rst
# ─────────────────────────────────────────────────────────────────────────────

def test_cdc_rst_placeholder_when_no_extracted_file(tmp_path):
    """A 'pending' placeholder is returned when no *_cdc.rst file exists."""
    entity = _make_entity()
    rst = cdc_rst(entity, module_dir=tmp_path)
    assert "pending" in rst.lower() or "make extract" in rst


def test_cdc_rst_include_when_extracted_file_exists(tmp_path):
    """An include directive is returned when the extracted *_cdc.rst file exists."""
    entity = _make_entity(name="my_mod")
    (tmp_path / "my_mod_cdc.rst").write_text("CDC content here.\n")
    rst = cdc_rst(entity, module_dir=tmp_path)
    assert ".. include::" in rst
    assert "my_mod_cdc.rst" in rst


# ─────────────────────────────────────────────────────────────────────────────
# fsm_rst
# ─────────────────────────────────────────────────────────────────────────────

def test_fsm_rst_placeholder_when_no_extracted_file(tmp_path):
    """A 'no FSM detected' placeholder is returned when no extracted FSM file exists."""
    entity = _make_entity()
    rst = fsm_rst(entity, module_dir=tmp_path)
    assert "No FSM" in rst or "no FSM" in rst.lower()


def test_fsm_rst_include_when_extracted_file_exists(tmp_path):
    """An include directive is returned when the extracted FSM rst file exists."""
    entity = _make_entity(name="my_mod")
    (tmp_path / "my_mod.rst").write_text("FSM content here.\n")
    rst = fsm_rst(entity, module_dir=tmp_path)
    assert ".. include::" in rst
    assert "my_mod.rst" in rst


# ─────────────────────────────────────────────────────────────────────────────
# File write helpers
# ─────────────────────────────────────────────────────────────────────────────

def test_write_if_missing_creates_file(tmp_path):
    """write_if_missing creates the file when it does not already exist."""
    p = tmp_path / "new.rst"
    write_if_missing(p, "content")
    assert p.read_text() == "content"


def test_write_if_missing_does_not_overwrite(tmp_path):
    """write_if_missing leaves an existing file untouched."""
    p = tmp_path / "existing.rst"
    p.write_text("original")
    write_if_missing(p, "new content")
    assert p.read_text() == "original"


def test_write_always_overwrites_existing(tmp_path):
    """write_always replaces an existing file with the new content."""
    p = tmp_path / "regen.rst"
    p.write_text("old content")
    write_always(p, "new content")
    assert p.read_text() == "new content"


def test_write_always_creates_parent_dirs(tmp_path):
    """write_always creates any missing parent directories."""
    p = tmp_path / "deep" / "nested" / "file.rst"
    write_always(p, "content")
    assert p.exists()


# ── Register-aware toctree tests ──────────────────────────────────────────────

def test_module_index_rst_with_registers_includes_registers_entry():
    """has_registers=True adds registers to the module toctree."""
    rst = module_index_rst(
        _make_entity(), children=[], shared_children=set(),
        has_registers=True
    )
    assert "   registers" in rst


def test_module_index_rst_without_registers_excludes_registers_entry():
    """has_registers=False (default) does not add registers to the toctree."""
    rst = module_index_rst(
        _make_entity(), children=[], shared_children=set()
    )
    assert "registers" not in rst


def test_registers_rst_generates_toctree():
    """registers_rst writes a toctree with module paths."""
    rst = registers_rst(["counter", "top"])
    assert "modules/counter/registers" in rst
    assert "modules/top/registers" in rst
    assert ".. toctree::" in rst


def test_index_rst_includes_registers_when_modules_present():
    """index_rst adds a registers entry when modules_with_regs is non-empty."""
    entity = {"name": "top", "brief": "Top.", "file": "top.vhd", "ports": []}
    rst = index_rst([entity], "MyProject", modules_with_regs=["top"])
    assert "registers" in rst


# ─────────────────────────────────────────────────────────────────────────────
# has_synthesis — module_index_rst
# ─────────────────────────────────────────────────────────────────────────────

def test_module_index_includes_synthesis_when_has_synthesis_true():
    """synthesis is added to the module toctree when has_synthesis=True."""
    rst = module_index_rst(_make_entity(), children=[], shared_children=set(),
                           has_synthesis=True)
    assert "synthesis" in rst


def test_module_index_omits_synthesis_when_has_synthesis_false():
    """synthesis is NOT added to the module toctree when has_synthesis=False."""
    rst = module_index_rst(_make_entity(), children=[], shared_children=set(),
                           has_synthesis=False)
    assert "synthesis" not in rst


# ─────────────────────────────────────────────────────────────────────────────
# has_synthesis — index_rst (top-level)
# ─────────────────────────────────────────────────────────────────────────────

def test_top_index_has_implementation_section_when_has_synthesis_true():
    """synthesis/index is included and 'Implementation' caption present."""
    rst = index_rst([_make_entity()], "MyProject", has_synthesis=True)
    assert "synthesis/index" in rst
    assert "Implementation" in rst


def test_top_index_no_implementation_section_when_has_synthesis_false():
    """synthesis/index is NOT present when has_synthesis=False."""
    rst = index_rst([_make_entity()], "MyProject", has_synthesis=False)
    assert "synthesis/index" not in rst


def test_unedited_entity_shell_is_upgraded_but_edits_are_kept(tmp_path):
    """An untouched old shell gains the SV description; a hand-edited one is left alone."""
    old, new = "old shell\n", "new shell\n"
    f = tmp_path / "entity.rst"
    f.write_text(old)
    write_if_missing_or_pristine(f, new, pristine=old)
    assert f.read_text() == new
    f.write_text("my edits\n")
    write_if_missing_or_pristine(f, new, pristine=old)
    assert f.read_text() == "my edits\n"


_H = {"top": "top", "modules": {
    "top":   {"file": "src/top.vhd",   "parents": [],      "children": ["leaf", "other"], "shared": False},
    "leaf":  {"file": "src/leaf.vhd",  "parents": ["top"], "children": [],                "shared": False},
    "other": {"file": "src/other.vhd", "parents": ["top"], "children": ["leaf"],          "shared": False},
}}
_E = [{"name": n, "file": m["file"], "brief": f"{n} brief."} for n, m in _H["modules"].items()]


def test_overview_includes_tree_and_parent_child_columns():
    """The overview carries what the old Design Hierarchy page showed."""
    rst = overview_rst(_E, "P", _H)
    assert ".. graphviz:: hierarchy.dot" in rst
    assert "Instantiated by" in rst and "Instantiates" in rst
    assert "*(top)*" in rst
    assert "``leaf``, ``other``" in rst
    assert "top brief." in rst  # descriptions are still there


def test_overview_without_hierarchy_keeps_the_plain_table():
    rst = overview_rst(_E, "P", None)
    assert "graphviz" not in rst and "Instantiates" not in rst


def test_index_toctree_has_no_separate_hierarchy_page():
    rst = index_rst(_E, "P", _H)
    assert "   overview" in rst
    assert "\n   hierarchy\n" not in rst


def test_source_rst_is_a_comment_only_when_disabled():
    """ANNOTATED_SOURCE=0 leaves an empty (comment) include, so no listing renders."""
    entity = _make_entity(name="my_mod", filename="my_mod.vhd")
    on, off = source_rst(entity, enabled=True), source_rst(entity, enabled=False)
    assert "Annotated Source" in on and "literalinclude" in on
    assert "Annotated Source" not in off and "literalinclude" not in off
    assert off.startswith("..")


def test_legacy_inline_shells_are_upgraded_to_the_include_form(tmp_path):
    """An unedited pre-split entity.rst (with or without an SV description) is upgraded."""
    (tmp_path / "my_mod.sv").write_text("// Desc.\nmodule my_mod (input logic clk);\nendmodule\n")
    entity = _make_entity(name="my_mod", filename="my_mod.sv")
    new = entity_rst(entity, "../src", src_dir=tmp_path)
    for legacy in legacy_entity_rsts(entity, "../src", tmp_path):
        f = tmp_path / "entity.rst"
        f.write_text(legacy)
        write_if_missing_or_pristine(f, new, pristine=legacy_entity_rsts(entity, "../src", tmp_path))
        assert f.read_text() == new
    f.write_text("hand edited\n")
    write_if_missing_or_pristine(f, new, pristine=legacy_entity_rsts(entity, "../src", tmp_path))
    assert f.read_text() == "hand edited\n"
