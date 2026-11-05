"""autodoc_json: one JSON document per source file, for the VS Code extension."""

import json
import subprocess
import sys
from pathlib import Path

import pytest

import extract_block
from autodoc_json import build_document

ROOT = Path(__file__).parents[4]
SCRIPT = Path(__file__).parents[1] / "autodoc_json.py"

VHDL = """\
library ieee;
use ieee.std_logic_1164.all;

-- Counter with a handshake.
--
-- Counts requests.
entity counter is
    generic (
        -- Width.
        W : positive := 8
    );
    port (
        clk : in  std_logic;
        -- Count value.
        q   : out std_logic_vector(W - 1 downto 0)
    );
end entity counter;
"""


def test_vhdl_document_has_module_generics_and_ports_with_lines():
    doc = build_document(VHDL, "vhdl")
    assert doc["language"] == "vhdl"
    assert doc["module"]["name"] == "counter" and doc["module"]["line"] == 7
    assert doc["module"]["description"] == "Counter with a handshake.\n\nCounts requests."
    assert [(g["name"], g["default"], g["description"], g["line"]) for g in doc["generics"]] == [
        ("W", "8", "Width.", 10)]
    ports = {p["name"]: p for p in doc["ports"]}
    assert (ports["clk"]["direction"], ports["clk"]["type"], ports["clk"]["line"]) == ("in", "std_logic", 13)
    assert ports["q"]["range"] == "W - 1 downto 0" and ports["q"]["description"] == "Count value."
    assert ports["q"]["kind"] == "port" and ports["q"]["group"] is None


IFACE = "interface axis_if;\n  logic [7:0] tdata;\n  modport slave (input tdata);\nendinterface\n"
SV_IFACE_USER = "module m (\n    input logic clk,\n    axis_if.slave s\n);\nendmodule\n"


def test_interface_ports_appear_only_when_the_interface_file_is_supplied(tmp_path):
    support = tmp_path / "axis_if.sv"
    support.write_text(IFACE)
    without = build_document(SV_IFACE_USER, "systemverilog")
    assert [p["name"] for p in without["ports"]] == ["clk"]
    with_support = build_document(SV_IFACE_USER, "systemverilog", support_files=[support])
    iface = next(p for p in with_support["ports"] if p["name"] == "s")
    assert (iface["kind"], iface["interface"], iface["modport"], iface["line"]) == ("interface", "axis_if", "slave", 3)


def test_ports_are_grouped_by_built_in_patterns_and_bus_groups_toml(tmp_path):
    toml = tmp_path / "bus_groups.toml"
    toml.write_text('[[group]]\nprefix = "adc"\nlabel = "Converter"\n')
    text = ("module m (\n    input logic clk,\n    input logic adc_clk,\n    input logic adc_rst,\n"
            "    input logic adc_data,\n    input logic [7:0] s_axis_tdata,\n    input logic s_axis_tvalid,\n"
            "    output logic s_axis_tready,\n    input logic s_axis_tlast\n);\nendmodule\n")
    doc = build_document(text, "systemverilog", bus_groups=toml)
    groups = {p["name"]: p["group"] for p in doc["ports"]}
    assert groups["adc_clk"] == groups["adc_data"] == "Converter"
    assert groups["s_axis_tdata"] == "AXI4-Stream Subordinate"
    assert groups["clk"] is None


def test_instances_carry_component_and_line():
    text = ("module top;\n  async_fifo #(.W(clog2(8))) u_fifo (.wr_clk(a), .rd_clk(b));\n"
            "  plain u_plain (.x(y));\nendmodule\n")
    doc = build_document(text, "systemverilog")
    assert [(i["instance"], i["component"], i["line"]) for i in doc["instances"]] == [
        ("u_fifo", "async_fifo", 2), ("u_plain", "plain", 3)]


def test_vhdl_instances_and_their_lines():
    doc = build_document((ROOT / "example_full/src/top.vhd").read_text(), "vhdl")
    found = {i["instance"]: i for i in doc["instances"]}
    assert found["u_ctrl"]["component"] == "sample_ctrl"
    assert (ROOT / "example_full/src/top.vhd").read_text().splitlines()[found["u_ctrl"]["line"] - 1].strip().startswith("u_ctrl")


def test_processes_carry_description_waveforms_and_diagrams_with_their_line():
    path = ROOT / "example_full/src/sample_ctrl.vhd"
    text = path.read_text()
    doc = build_document(text, "vhdl")
    procs = {p["label"]: p for p in doc["processes"]}
    nxt = procs["p_next_state"]
    assert text.splitlines()[nxt["line"] - 1].strip().startswith("p_next_state")
    assert nxt["sensitivity"] == ["state", "start", "overflow", "run_last"]
    (diagram,) = nxt["mermaid"]
    assert diagram["caption"] == "Controller states" and diagram["source"].startswith("stateDiagram-v2")
    assert "    [*] --> IDLE" not in diagram["source"] and "  [*] --> IDLE" in diagram["source"]
    assert json.loads(nxt["wavedrom"][0])["signal"][0]["name"] == "clk"
    assert "Combinational next-state logic." in nxt["description"]


def test_header_diagrams_are_returned_with_the_module():
    text = ("// Filter.\n//\n// .. mermaid::\n//    :caption: Flow\n//\n//    flowchart LR\n//      A --> B\n"
            "module m;\nendmodule\n")
    doc = build_document(text, "systemverilog")
    assert doc["module"]["description"] == "Filter."
    assert doc["module"]["mermaid"] == [{"caption": "Flow", "source": "flowchart LR\n  A --> B"}]


def test_fsm_has_states_transitions_and_graphviz_source():
    doc = build_document((ROOT / "example/src/traffic_light.vhd").read_text(), "vhdl")
    fsm = doc["fsm"]
    assert {"RED", "RED_AMBER", "GREEN", "AMBER"} <= set(fsm["states"])
    assert {"from": "RED", "to": "RED_AMBER", "condition": "timer_exp = '1'"} in fsm["transitions"]
    assert fsm["dot"].startswith("digraph")


def test_a_file_without_a_state_machine_has_no_fsm():
    assert build_document(VHDL, "vhdl")["fsm"] is None


def test_cdc_and_reset_sections_for_a_two_clock_file():
    doc = build_document((ROOT / "example_full/src/sample_capture.sv").read_text(), "systemverilog")
    cdc = doc["cdc"]
    assert set(cdc["domains"]) == {"clk", "adc_clk"}
    assert any(c["signal"] == "capture_en" and c["synchronized"] for c in cdc["crossings"])
    assert cdc["dual_clock_instances"][0]["component"] == "async_fifo"
    reset = doc["reset"]
    assert {p["label"]: (p["reset"], p["style"]) for p in reset["processes"]}["p_adc_en"] == ("adc_rst", "sync")
    assert set(reset["domains"]) == {"rst_n", "adc_rst"}
    assert reset["domains"]["adc_rst"] == ["p_adc_en", "p_adc_capture"]


def test_a_file_with_no_clocked_logic_has_no_cdc_or_reset():
    doc = build_document("module m (input logic a, output logic b);\n  assign b = a;\nendmodule\n", "systemverilog")
    assert doc["cdc"] is None and doc["reset"] is None


@pytest.mark.parametrize("text", ["", "entity e is port (", "garbage ((( ;;; end", "\x00\x01 binary"])
def test_a_file_that_does_not_parse_returns_a_document_not_an_exception(text):
    doc = build_document(text, "vhdl")
    assert doc["ports"] == [] and isinstance(doc["warnings"], list)
    json.dumps(doc)


def test_a_failing_section_is_a_warning_and_the_rest_is_still_returned(monkeypatch):
    def boom(text):
        raise RuntimeError("boom")
    monkeypatch.setattr(extract_block, "extract_ports_vhdl", boom)
    doc = build_document(VHDL, "vhdl")
    assert doc["ports"] == [] and any("ports" in w and "boom" in w for w in doc["warnings"])
    assert doc["module"]["name"] == "counter" and doc["generics"]


def test_the_module_is_none_with_a_warning_when_there_is_no_entity():
    doc = build_document("-- just a comment\n", "vhdl")
    assert doc["module"] is None and any("no entity" in w.lower() for w in doc["warnings"])


def _cli(source: bytes, *args):
    return subprocess.run([sys.executable, str(SCRIPT), *args], input=source,
                          capture_output=True, check=True)


def test_cli_reads_stdin_and_writes_valid_json_with_crlf_and_non_ascii_text():
    source = VHDL.replace("Counts requests.", "Zählt Anfragen — naïve.").replace("\n", "\r\n").encode("utf-8")
    doc = json.loads(_cli(source, "--language", "vhdl").stdout)
    assert doc["module"]["description"].endswith("Zählt Anfragen — naïve.")
    assert doc["module"]["line"] == 7 and doc["ports"][0]["line"] == 13


def test_cli_takes_support_files_and_bus_groups(tmp_path):
    support = tmp_path / "axis_if.sv"
    support.write_text(IFACE)
    toml = tmp_path / "g.toml"
    toml.write_text('[[group]]\nprefix = "adc"\nlabel = "Converter"\n')
    text = ("module m (\n    axis_if.slave s,\n    input logic adc_a,\n    input logic adc_b,\n"
            "    input logic adc_c\n);\nendmodule\n")
    doc = json.loads(_cli(text.encode(), "--language", "systemverilog", "--support", str(support),
                          "--bus-groups", str(toml)).stdout)
    assert doc["ports"][0]["kind"] == "interface"
    assert doc["ports"][1]["group"] == "Converter"


def test_cli_exits_non_zero_on_a_usage_error():
    out = subprocess.run([sys.executable, str(SCRIPT), "--language", "cobol"], input=b"", capture_output=True)
    assert out.returncode != 0


def _example_sources():
    return sorted(p for pattern in ("example*/src/*.sv", "example*/src/*.vhd") for p in ROOT.glob(pattern))


@pytest.mark.parametrize("path", _example_sources(), ids=lambda p: f"{p.parents[1].name}/{p.name}")
def test_every_example_file_produces_a_serialisable_document(path):
    text = path.read_text()
    language = "vhdl" if path.suffix == ".vhd" else "systemverilog"
    doc = build_document(text, language)
    json.dumps(doc)
    expected = (extract_block.extract_ports_vhdl(text) if language == "vhdl"
                else extract_block.extract_ports_sv(text))
    assert len(doc["ports"]) == len(expected)
    assert doc["warnings"] == [] or doc["module"] is None


def test_interfaces_instantiated_in_the_body_are_listed_with_their_line(tmp_path):
    support = tmp_path / "axis_if.sv"
    support.write_text(IFACE)
    text = "module top;\n  axis_if s_if ();\n  plain u (.x(y));\nendmodule\n"
    doc = build_document(text, "systemverilog", support_files=[support])
    assert doc["warnings"] == []
    assert [(i["instance"], i["component"], i["kind"], i["line"]) for i in doc["instances"]] == [
        ("s_if", "axis_if", "interface", 2), ("u", "plain", "module", 3)]
