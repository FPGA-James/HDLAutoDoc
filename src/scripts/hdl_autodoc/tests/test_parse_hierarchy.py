"""
test_parse_hierarchy.py
-----------------------
Tests for parse_hierarchy.py.

Covers:
  - Entity/module name extraction for VHDL and SystemVerilog.
  - Instantiation detection (entity work. style and component style for VHDL;
    named-instance style for SV).
  - Top-level auto-detection (module with no parents).
  - Shared component detection (module instantiated by more than one parent).
"""

from pathlib import Path

import pytest

from parse_hierarchy import (
    build_hierarchy,
    extract_instantiations_sv,
    extract_instantiations_vhdl,
    extract_module_name,
)


# ─────────────────────────────────────────────────────────────────────────────
# Module name extraction
# ─────────────────────────────────────────────────────────────────────────────

def test_extract_module_name_vhdl(tmp_path):
    """Entity name is extracted from a VHDL 'entity X is' declaration."""
    f = tmp_path / "foo.vhd"
    f.write_text("entity my_module is\n  port (clk : in std_logic);\nend entity my_module;\n")
    assert extract_module_name(f) == "my_module"


def test_extract_module_name_sv(tmp_path):
    """Module name is extracted from a SystemVerilog 'module X' declaration."""
    f = tmp_path / "bar.sv"
    f.write_text("module my_sv_mod (\n  input logic clk\n);\nendmodule\n")
    assert extract_module_name(f) == "my_sv_mod"


def test_extract_module_name_unknown_extension(tmp_path):
    """Files with unsupported extensions return None."""
    f = tmp_path / "notes.txt"
    f.write_text("entity ignored is\n")
    assert extract_module_name(f) is None


def test_extract_module_name_case_insensitive_vhdl(tmp_path):
    """Entity keyword matching is case-insensitive; the returned name is lowercased."""
    f = tmp_path / "upper.vhd"
    f.write_text("ENTITY UpperMod IS\n  port ();\nEND ENTITY UpperMod;\n")
    assert extract_module_name(f) == "uppermod"


# ─────────────────────────────────────────────────────────────────────────────
# VHDL instantiation extraction
# ─────────────────────────────────────────────────────────────────────────────

def test_extract_instantiations_vhdl_direct_style():
    """'entity work.child' instantiation style is detected."""
    text = """
    u1 : entity work.child_a port map (clk => clk);
    u2 : entity work.child_b port map (rst => rst);
    """
    result = extract_instantiations_vhdl(text, {"child_a", "child_b"})
    assert "child_a" in result
    assert "child_b" in result


def test_extract_instantiations_vhdl_component_style():
    """Component instantiation style (label : component_name port map) is detected
    only when the name appears in the known-names set."""
    text = "u1 : my_comp port map (clk => clk);"
    result = extract_instantiations_vhdl(text, {"my_comp"})
    assert "my_comp" in result


def test_extract_instantiations_vhdl_ignores_unknown():
    """Component-style instantiation is NOT matched if the name is not in known_names.
    This prevents false positives from identifiers that happen to precede 'port map'."""
    text = "u1 : not_a_module port map (clk => clk);"
    result = extract_instantiations_vhdl(text, {"other_module"})
    assert "not_a_module" not in result


def test_extract_instantiations_vhdl_comments_stripped():
    """Instantiations inside comments are not detected."""
    text = "-- u1 : entity work.ghost port map (clk => clk);\n"
    result = extract_instantiations_vhdl(text, {"ghost"})
    assert "ghost" not in result


# ─────────────────────────────────────────────────────────────────────────────
# SystemVerilog instantiation extraction
# ─────────────────────────────────────────────────────────────────────────────

def test_extract_instantiations_sv_basic():
    """A simple 'module_name inst_name (...)' instantiation is detected."""
    text = "child_mod u_child (\n  .clk(clk)\n);\n"
    result = extract_instantiations_sv(text, {"child_mod"})
    assert "child_mod" in result


def test_extract_instantiations_sv_with_params():
    """Instantiation with a positional parameter list '#(value)' is detected.
    Note: named-port parameter syntax '#(.PARAM(val))' is not supported by the
    regex (the inner ')' terminates the match early); positional syntax is used."""
    text = "child_mod #(8) u_child (.clk(clk));\n"
    result = extract_instantiations_sv(text, {"child_mod"})
    assert "child_mod" in result


def test_extract_instantiations_sv_keywords_excluded():
    """SV keywords like 'always', 'module', 'if' are never returned as instances."""
    text = "always @(posedge clk) begin : my_block\n  if (en) out <= 1;\nend\n"
    result = extract_instantiations_sv(text, {"always", "if", "begin"})
    assert result == []


# ─────────────────────────────────────────────────────────────────────────────
# Hierarchy building
# ─────────────────────────────────────────────────────────────────────────────

def test_build_hierarchy_top_detected(tmp_path):
    """The module not instantiated by any other is identified as the top level."""
    top = tmp_path / "top.vhd"
    top.write_text(
        "entity top is port (clk : in std_logic); end entity top;\n"
        "architecture rtl of top is begin\n"
        "  u1 : entity work.leaf port map (clk => clk);\n"
        "end architecture rtl;\n"
    )
    leaf = tmp_path / "leaf.vhd"
    leaf.write_text(
        "entity leaf is port (clk : in std_logic); end entity leaf;\n"
    )
    h = build_hierarchy([leaf, top])
    assert h["top"] == "top"
    assert "leaf" in h["modules"]["top"]["children"]
    assert h["modules"]["leaf"]["parents"] == ["top"]


def test_build_hierarchy_shared_component(tmp_path):
    """A module instantiated by two parents is flagged as shared."""
    shared = tmp_path / "shared.vhd"
    shared.write_text("entity shared is port (); end entity shared;\n")

    parent_a = tmp_path / "parent_a.vhd"
    parent_a.write_text(
        "entity parent_a is port (); end entity parent_a;\n"
        "architecture rtl of parent_a is begin\n"
        "  u1 : entity work.shared port map ();\n"
        "end architecture rtl;\n"
    )
    parent_b = tmp_path / "parent_b.vhd"
    parent_b.write_text(
        "entity parent_b is port (); end entity parent_b;\n"
        "architecture rtl of parent_b is begin\n"
        "  u1 : entity work.shared port map ();\n"
        "end architecture rtl;\n"
    )
    top = tmp_path / "top.vhd"
    top.write_text(
        "entity top is port (); end entity top;\n"
        "architecture rtl of top is begin\n"
        "  ua : entity work.parent_a port map ();\n"
        "  ub : entity work.parent_b port map ();\n"
        "end architecture rtl;\n"
    )
    h = build_hierarchy([shared, parent_a, parent_b, top])
    assert h["modules"]["shared"]["shared"] is True


def test_build_hierarchy_no_children(tmp_path):
    """A single module with no instantiations is its own top with no children."""
    f = tmp_path / "solo.vhd"
    f.write_text("entity solo is port (); end entity solo;\n")
    h = build_hierarchy([f])
    assert h["top"] == "solo"
    assert h["modules"]["solo"]["children"] == []


# ─────────────────────────────────────────────────────────────────────────────
# support_files (SystemVerilog packages / interfaces)
# ─────────────────────────────────────────────────────────────────────────────

def _sv_project(tmp_path):
    pkg = tmp_path / "aes_pkg.sv"
    pkg.write_text("package aes_pkg;\n  typedef logic [7:0] byte_t;\nendpackage\n")
    ifc = tmp_path / "bus_if.sv"
    ifc.write_text("interface bus_if (input logic clk);\n  logic v;\nendinterface\n")
    leaf = tmp_path / "leaf.sv"
    leaf.write_text("module leaf (input logic clk);\nendmodule\n")
    top = tmp_path / "top.sv"
    top.write_text("module top (input logic clk);\n  leaf u (.clk(clk));\nendmodule\n")
    return pkg, ifc, leaf, top


def test_module_less_sv_files_are_recorded_as_support_files_in_filelist_order(tmp_path):
    """Packages and interfaces land in support_files, in the filelist's order."""
    pkg, ifc, leaf, top = _sv_project(tmp_path)
    h = build_hierarchy([pkg, ifc, leaf, top])
    assert h["support_files"] == [str(pkg), str(ifc)]


def test_support_files_are_not_hierarchy_modules(tmp_path):
    """Support files do not become modules, and the real hierarchy is unaffected."""
    pkg, ifc, leaf, top = _sv_project(tmp_path)
    h = build_hierarchy([pkg, ifc, leaf, top])
    assert set(h["modules"]) == {"leaf", "top"}
    assert h["top"] == "top"
    assert h["modules"]["top"]["children"] == ["leaf"]


def test_support_files_is_present_and_empty_when_there_are_none(tmp_path):
    """The key always exists so readers need no special case for module-only projects."""
    pkg, ifc, leaf, top = _sv_project(tmp_path)
    assert build_hierarchy([leaf, top])["support_files"] == []


def test_non_sv_files_without_a_module_are_not_support_files(tmp_path):
    """VHDL (and unknown-extension) files with no entity keep the old warning path."""
    pkg = tmp_path / "pkg.vhd"
    pkg.write_text("package p is end package;\n")
    leaf = tmp_path / "leaf.sv"
    leaf.write_text("module leaf (input logic clk);\nendmodule\n")
    h = build_hierarchy([pkg, leaf])
    assert h["support_files"] == []


def test_support_file_note_goes_to_stderr_not_a_warning(tmp_path, capsys):
    pkg, ifc, leaf, top = _sv_project(tmp_path)
    build_hierarchy([pkg, leaf, top])
    err = capsys.readouterr().err
    assert "support file" in err and "could not extract module name" not in err
