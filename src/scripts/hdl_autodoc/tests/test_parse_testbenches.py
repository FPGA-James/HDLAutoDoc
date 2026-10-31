"""Tests for parse_testbenches.py: VUnit / cocotb / directed testbench parsing."""

from parse_testbenches import (
    TestCase,
    discover_testbenches,
    framework_for_dir,
    header_purpose,
    link_dut,
    parse_cocotb,
    parse_directed,
    parse_vunit_hdl,
)

VUNIT_VHDL = """\
-- Testbench for the FIFO.
library vunit_lib;
context vunit_lib.vunit_context;

entity tb_fifo is
  generic (runner_cfg : string);
end entity tb_fifo;

architecture tb of tb_fifo is
begin
  main : process
  begin
    test_runner_setup(runner, runner_cfg);
    while test_suite loop
      -- Reset empties the FIFO.
      if run("reset") then
        null;
      -- Pointers wrap at the last address.
      -- Checked at depth 4.
      elsif run("wrap") then
        null;
      elsif run("inline") then  -- Purpose on the same line.
        null;
      -- elsif run("old_test") then
      end if;
    end loop;
    test_runner_cleanup(runner);
  end process;
end architecture tb;
"""

VUNIT_SV = """\
// Stream filter testbench.
`include "vunit_defines.svh"

module tb_stream_filter;
  `TEST_SUITE begin
    // Bytes at or above the threshold pass.
    `TEST_CASE("passes_above_threshold") begin
    end
    `TEST_CASE("drops_below_threshold") begin  // Below is dropped.
    end
    // `TEST_CASE("commented_out") begin
  end
endmodule
"""

COCOTB = '''\
"""Register file tests.

Second paragraph is not the purpose.
"""
import cocotb
from cocotb.triggers import RisingEdge

# @cocotb.test()
# async def commented_out(dut): ...

@cocotb.test()
async def reset_values(dut):
    """Registers read back their reset values.

    More detail here.
    """


@cocotb.test(
    timeout_time=10,
    timeout_unit="ns",
)
async def write_read(dut):
    """Written values read back."""


@cocotb.test(skip=True)
async def not_ready(dut):
    """Waiting for the next RTL drop."""


async def helper(dut):
    """Not a test: has a docstring mentioning @cocotb.test()."""
'''

DIRECTED_VHDL = """\
-- Directed testbench for the top level.
entity tb_top is end entity;
architecture sim of tb_top is
begin
  process begin
    -- TEST: reset_clears_fifo — FIFO is empty after reset
    wait for 10 ns;
    -- TEST: dash_sep - hyphen separator
    -- TEST: colon_sep: colon separator
    -- TEST: bare
    report "-- TEST: in_a_string — not a test";
    /* -- TEST: in_block — not a test */
    /* TEST: block_start — not a test */
    wait;
  end process;
end architecture;
"""

DIRECTED_SV = """\
// Smoke test.
module tb_smoke;
  initial begin
    // TEST: wrap_around — pointers wrap at the last address
    #10;
    $display("// TEST: in_string — no");
    /* // TEST: in_block — no
    */
    /* TEST: block_start_sv — no
       TEST: block_next_line — no */
  end
endmodule
"""


# ── framework_for_dir ────────────────────────────────────────────────────────

def test_framework_for_dir_is_case_insensitive_and_defaults_to_directed():
    assert framework_for_dir("vunit") == "vunit"
    assert framework_for_dir("VUnit") == "vunit"
    assert framework_for_dir("COCOTB") == "cocotb"
    assert framework_for_dir("directed") == "directed"
    assert framework_for_dir("unit_tests") == "directed"


# ── VUnit ────────────────────────────────────────────────────────────────────

def test_vunit_vhdl_run_blocks_are_tests_with_purposes_from_comments():
    tests = parse_vunit_hdl(VUNIT_VHDL, ".vhd")
    assert [t.name for t in tests] == ["reset", "wrap", "inline"]
    assert tests[0].purpose == "Reset empties the FIFO."
    assert tests[1].purpose == "Pointers wrap at the last address. Checked at depth 4."
    assert tests[2].purpose == "Purpose on the same line."


def test_vunit_vhdl_commented_out_run_is_not_counted():
    assert "old_test" not in [t.name for t in parse_vunit_hdl(VUNIT_VHDL, ".vhd")]


def test_vunit_sv_test_case_blocks():
    tests = parse_vunit_hdl(VUNIT_SV, ".sv")
    assert [t.name for t in tests] == ["passes_above_threshold", "drops_below_threshold"]
    assert tests[0].purpose == "Bytes at or above the threshold pass."
    assert tests[1].purpose == "Below is dropped."


def test_vunit_with_no_tests_is_empty():
    assert parse_vunit_hdl("entity tb is end entity;", ".vhd") == []


# ── cocotb ───────────────────────────────────────────────────────────────────

def test_cocotb_counts_only_real_decorated_tests():
    _, tests = parse_cocotb(COCOTB)
    assert [t.name for t in tests] == ["reset_values", "write_read", "not_ready"]


def test_cocotb_purposes_come_from_docstring_first_line_and_module_docstring():
    purpose, tests = parse_cocotb(COCOTB)
    assert purpose == "Register file tests."
    assert tests[0].purpose == "Registers read back their reset values."
    assert tests[1].purpose == "Written values read back."


def test_cocotb_skip_true_is_listed_and_flagged():
    _, tests = parse_cocotb(COCOTB)
    assert [t.skipped for t in tests] == [False, False, True]


def test_cocotb_module_purpose_falls_back_to_leading_comment_block():
    purpose, tests = parse_cocotb("# Smoke tests for the bridge.\n# More.\nimport cocotb\n"
                                  "@cocotb.test()\nasync def a(dut): pass\n")
    assert purpose == "Smoke tests for the bridge. More."
    assert [t.name for t in tests] == ["a"]


def test_cocotb_syntax_error_raises_so_discover_can_warn_and_skip():
    import pytest
    with pytest.raises(SyntaxError):
        parse_cocotb("def broken(:\n")


# ── directed ─────────────────────────────────────────────────────────────────

def test_directed_markers_with_each_separator_and_no_purpose():
    tests = parse_directed(DIRECTED_VHDL, ".vhd")
    assert [t.name for t in tests] == ["reset_clears_fifo", "dash_sep", "colon_sep", "bare"]
    assert tests[0].purpose == "FIFO is empty after reset"
    assert tests[1].purpose == "hyphen separator"
    assert tests[2].purpose == "colon separator"
    assert tests[3].purpose == ""


def test_directed_markers_in_strings_and_block_comments_are_ignored():
    names = [t.name for t in parse_directed(DIRECTED_VHDL, ".vhd")]
    assert "in_a_string" not in names and "in_block" not in names
    assert "block_start" not in names


def test_directed_sv_markers_use_slash_slash_and_ignore_strings_and_blocks():
    tests = parse_directed(DIRECTED_SV, ".sv")
    assert [(t.name, t.purpose) for t in tests] == [
        ("wrap_around", "pointers wrap at the last address")]


def test_directed_without_markers_is_empty():
    assert parse_directed("-- just a header\nentity tb is end entity;\n", ".vhd") == []


# ── header_purpose ───────────────────────────────────────────────────────────

def test_header_purpose_is_the_comment_block_directly_above_the_entity():
    text = "library ieee;\n-- Tests the\n-- FIFO.\nentity tb is end entity;\n"
    assert header_purpose(text, ".vhd") == "Tests the FIFO."


def test_header_purpose_falls_back_to_the_leading_block_of_the_file():
    text = "-- FIFO testbench.\n\nlibrary ieee;\nuse ieee.std_logic_1164.all;\nentity tb is end entity;\n"
    assert header_purpose(text, ".vhd") == "FIFO testbench."


def test_header_purpose_sv_and_decorative_lines():
    text = "//----------\n// Smoke test.\n//----------\nmodule tb_smoke;\nendmodule\n"
    assert header_purpose(text, ".sv") == "Smoke test."


def test_header_purpose_empty_when_there_is_no_comment():
    assert header_purpose("entity tb is end entity;\n", ".vhd") == ""


# ── link_dut ─────────────────────────────────────────────────────────────────

def test_link_dut_by_name_convention():
    mods = {"fifo", "uart"}
    for name in ("tb_fifo", "fifo_tb", "test_fifo", "fifo_test", "TB_FIFO"):
        assert link_dut(name, "", ".vhd", mods) == "fifo", name
    assert link_dut("tb_other", "", ".vhd", mods) is None


def test_link_dut_by_instantiation_when_the_name_does_not_match():
    text = "architecture a of bench is begin\n  u1 : entity work.fifo port map (clk => clk);\nend;\n"
    assert link_dut("bench", text, ".vhd", {"fifo"}) == "fifo"
    sv = "module bench;\n  fifo u1 (.clk(clk));\nendmodule\n"
    assert link_dut("bench", sv, ".sv", {"fifo"}) == "fifo"


def test_link_dut_for_cocotb_uses_the_name_only():
    assert link_dut("test_fifo", "fifo u1 (.clk(clk))", ".py", {"fifo"}) == "fifo"
    assert link_dut("bench", "fifo u1 (.clk(clk))", ".py", {"fifo"}) is None


# ── discover_testbenches ─────────────────────────────────────────────────────

def _tree(tmp_path):
    tb = tmp_path / "tb"
    for d in ("vunit", "cocotb", "directed", "Custom"):
        (tb / d).mkdir(parents=True)
    (tb / "vunit" / "tb_fifo.vhd").write_text(VUNIT_VHDL)
    (tb / "vunit" / "tb_filter.sv").write_text(VUNIT_SV)
    (tb / "vunit" / "pkg.vhd").write_text("package p is end package;\n")          # no entity
    (tb / "vunit" / "run.py").write_text("print('vunit runner')\n")                 # not a tb
    (tb / "cocotb" / "test_regs.py").write_text(COCOTB)
    (tb / "cocotb" / "helpers.py").write_text("def h(): pass\n")                    # no tests
    (tb / "cocotb" / "Makefile").write_text("all:\n")
    (tb / "directed" / "tb_top.vhd").write_text(DIRECTED_VHDL)
    (tb / "directed" / "tb_nomark.vhd").write_text(
        "-- No markers here.\nentity tb_nomark is end entity;\n")
    (tb / "Custom" / "tb_odd.sv").write_text(DIRECTED_SV)                           # unknown dir
    return tb


def test_discover_finds_testbenches_sorted_by_framework_then_name(tmp_path):
    tbs = discover_testbenches(_tree(tmp_path), {"fifo", "regs", "top", "stream_filter"})
    assert [(t.framework, t.name) for t in tbs] == [
        ("vunit", "tb_fifo"), ("vunit", "tb_stream_filter"),
        ("cocotb", "test_regs"),
        ("directed", "tb_nomark"), ("directed", "tb_smoke"), ("directed", "tb_top"),
    ]


def test_discover_fills_purpose_tests_and_dut(tmp_path):
    tbs = {t.name: t for t in discover_testbenches(_tree(tmp_path), {"fifo", "regs", "top"})}
    fifo = tbs["tb_fifo"]
    assert fifo.file == "tb/vunit/tb_fifo.vhd"
    assert fifo.purpose == "Testbench for the FIFO."
    assert len(fifo.tests) == 3 and fifo.dut == "fifo"
    regs = tbs["test_regs"]
    assert regs.purpose == "Register file tests." and regs.dut == "regs" and len(regs.tests) == 3
    assert tbs["tb_top"].dut == "top" and len(tbs["tb_top"].tests) == 4


def test_discover_directed_file_without_markers_is_one_test_named_after_the_testbench(tmp_path):
    tbs = {t.name: t for t in discover_testbenches(_tree(tmp_path), set())}
    (only,) = tbs["tb_nomark"].tests
    assert only == TestCase(name="tb_nomark", purpose="No markers here.")


def test_discover_treats_unknown_subdirectories_and_loose_files_as_directed(tmp_path, capsys):
    tb = _tree(tmp_path)
    (tb / "tb_loose.vhd").write_text("-- Loose.\nentity tb_loose is end entity;\n")
    tbs = {t.name: t for t in discover_testbenches(tb, set())}
    assert tbs["tb_smoke"].framework == "directed" and tbs["tb_loose"].framework == "directed"
    assert "directed" in capsys.readouterr().err        # a console note is printed


def test_discover_missing_or_empty_directory_gives_no_testbenches(tmp_path):
    assert discover_testbenches(tmp_path / "nope", set()) == []
    (tmp_path / "empty").mkdir()
    assert discover_testbenches(tmp_path / "empty", set()) == []


def test_discover_survives_empty_binary_and_non_utf8_files(tmp_path, capsys):
    tb = tmp_path / "tb"
    (tb / "directed").mkdir(parents=True)
    (tb / "directed" / "empty.vhd").write_text("")
    (tb / "directed" / "blob.vhd").write_bytes(b"\x00\x01\x02entity x is\x00")
    (tb / "directed" / "latin1.vhd").write_bytes(
        "-- Caf\xe9 bench.\nentity tb_latin is end entity;\n".encode("latin-1"))
    (tb / "directed" / "tb_ok.vhd").write_text("-- OK.\nentity tb_ok is end entity;\n")
    (tb / "cocotb").mkdir()
    (tb / "cocotb" / "test_bad.py").write_text("def broken(:\n")
    tbs = discover_testbenches(tb, set())
    names = sorted(t.name for t in tbs)
    assert "tb_ok" in names and "tb_latin" in names           # decoded with replacement
    assert "blob" not in names and "empty" not in names and "test_bad" not in names
    err = capsys.readouterr().err
    assert "blob.vhd" in err and "test_bad.py" in err          # warned, not crashed


# ── Review fixes: output directories, helper modules, byte-order marks ───────

def test_simulator_output_directories_are_not_scanned(tmp_path):
    """VUnit copies sources into vunit_out/; those copies are not testbenches."""
    tb = tmp_path / "tb" / "vunit"
    (tb / "vunit_out" / "preprocessed" / "lib").mkdir(parents=True)
    (tb / "tb_fifo.vhd").write_text(VUNIT_VHDL)
    (tb / "vunit_out" / "preprocessed" / "lib" / "tb_fifo.vhd").write_text(VUNIT_VHDL)
    for hidden in (".cache", "sim_build", "__pycache__", "obj_dir", "xsim.dir"):
        (tb / hidden).mkdir()
        (tb / hidden / "tb_copy.vhd").write_text(VUNIT_VHDL.replace("tb_fifo", "tb_copy"))
    tbs = discover_testbenches(tmp_path / "tb", set())
    assert [t.name for t in tbs] == ["tb_fifo"]


def test_a_module_instantiated_by_another_testbench_is_a_helper_not_a_testbench(tmp_path):
    d = tmp_path / "tb" / "directed"
    d.mkdir(parents=True)
    (d / "axi_bfm.sv").write_text("// Bus functional model.\nmodule axi_bfm (input logic clk);\nendmodule\n")
    (d / "tb_top.sv").write_text(
        "// Top bench.\nmodule tb_top;\n  logic clk;\n  axi_bfm u_bfm (.clk(clk));\n"
        "  // TEST: smoke — runs\nendmodule\n")
    names = [t.name for t in discover_testbenches(tmp_path / "tb", set())]
    assert names == ["tb_top"]


def test_vhdl_helper_entities_instantiated_by_a_testbench_are_skipped_too(tmp_path):
    d = tmp_path / "tb" / "directed"
    d.mkdir(parents=True)
    (d / "uart_model.vhd").write_text("-- Model.\nentity uart_model is end entity;\n")
    (d / "tb_uart.vhd").write_text(
        "-- Bench.\nentity tb_uart is end entity;\narchitecture a of tb_uart is begin\n"
        "  u : entity work.uart_model port map (clk => clk);\nend;\n")
    assert [t.name for t in discover_testbenches(tmp_path / "tb", set())] == ["tb_uart"]


def test_a_testbench_that_nothing_instantiates_is_kept(tmp_path):
    d = tmp_path / "tb" / "directed"
    d.mkdir(parents=True)
    (d / "tb_a.sv").write_text("// A.\nmodule tb_a;\nendmodule\n")
    (d / "tb_b.sv").write_text("// B.\nmodule tb_b;\nendmodule\n")
    assert [t.name for t in discover_testbenches(tmp_path / "tb", set())] == ["tb_a", "tb_b"]


def test_a_utf8_byte_order_mark_does_not_hide_a_cocotb_testbench(tmp_path):
    d = tmp_path / "tb" / "cocotb"
    d.mkdir(parents=True)
    (d / "test_bom.py").write_bytes(
        b'\xef\xbb\xbf"""BOM bench."""\nimport cocotb\n@cocotb.test()\nasync def a(dut):\n    """A."""\n')
    (tb,) = discover_testbenches(tmp_path / "tb", set())
    assert tb.name == "test_bom" and tb.purpose == "BOM bench." and len(tb.tests) == 1


def test_a_utf8_byte_order_mark_does_not_hide_an_hdl_header_purpose(tmp_path):
    d = tmp_path / "tb" / "directed"
    d.mkdir(parents=True)
    (d / "tb_bom.vhd").write_bytes(b"\xef\xbb\xbf-- FIFO bench.\nlibrary ieee;\nentity tb_bom is end entity;\n")
    (tb,) = discover_testbenches(tmp_path / "tb", set())
    assert tb.purpose == "FIFO bench."
