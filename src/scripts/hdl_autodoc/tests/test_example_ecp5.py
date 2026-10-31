"""The ECP5 example must stay consistent with the parsers that document it."""

import tomllib
from pathlib import Path

from extract_block import extract_ports_sv
from parse_build_info import (
    parse_build_info,
    parse_device_utilisation,
    summarise_warnings,
)
from parse_hierarchy import build_hierarchy, read_filelist
from parse_testbenches import discover_testbenches
from parse_timing import parse_timing
from sv_interfaces import collect_interfaces

EXAMPLE = Path(__file__).parents[4] / "example_ecp5"
MODULES = {"axil_regs", "stream_filter", "top"}


def test_testbenches_are_found_counted_and_linked():
    tbs = {t.name: t for t in discover_testbenches(EXAMPLE / "tb", MODULES)}
    assert set(tbs) == {"tb_stream_filter", "test_axil_regs", "tb_top"}
    assert {t.framework for t in tbs.values()} == {"vunit", "cocotb", "directed"}
    assert sum(len(t.tests) for t in tbs.values()) == 8
    assert sum(1 for t in tbs.values() for c in t.tests if c.skipped) == 1
    assert tbs["tb_stream_filter"].dut == "stream_filter"
    assert tbs["test_axil_regs"].dut == "axil_regs"
    assert tbs["tb_top"].dut == "top"
    assert all(t.purpose for t in tbs.values())          # every header comment is picked up


def test_committed_reports_parse():
    reports = EXAMPLE / "reports" / "yosys"
    nextpnr = (reports / "nextpnr.log").read_text()
    yosys = (reports / "yosys.log").read_text()

    resources = {r.name: r for r in parse_device_utilisation(nextpnr)}
    assert resources["TRELLIS_FF"].used > 0 and resources["TRELLIS_COMB"].used > 0

    clocks, tool = parse_timing(reports / "nextpnr.log")
    assert tool == "nextpnr" and clocks
    assert len({c.clock_name for c in clocks}) == len(clocks)      # one row per clock

    info = parse_build_info(yosys, nextpnr, None)
    assert info.yosys_version and info.device == "ECP5 25k class"
    assert summarise_warnings(yosys, nextpnr).total >= 0


def test_interface_ports_are_found_in_the_modules_that_have_them():
    ifaces = set(collect_interfaces([EXAMPLE / "src" / "axis_if.sv", EXAMPLE / "src" / "axil_if.sv"]))
    assert ifaces == {"axis_if", "axil_if"}

    def ports(name):
        return {p["name"] for p in extract_ports_sv((EXAMPLE / "src" / f"{name}.sv").read_text(), ifaces)
                if p.get("kind") == "interface"}

    assert ports("top") == {"s_axil", "s_axis", "m_axis"}
    assert ports("axil_regs") == {"s_axil"}
    assert ports("stream_filter") == {"s_axis", "m_axis"}


def test_register_map_has_the_four_registers():
    data = tomllib.loads((EXAMPLE / "registers" / "regs_axil_regs.toml").read_text())
    assert [k for k, v in data.items() if isinstance(v, dict) and "mode" in v] == [
        "ctrl", "status", "threshold", "scratch"]


def test_hierarchy_has_three_modules_and_two_support_files(monkeypatch):
    monkeypatch.chdir(EXAMPLE)
    h = build_hierarchy(read_filelist(EXAMPLE / "filelist.f"))
    assert h["top"] == "top"
    assert set(h["modules"]) == MODULES
    assert [Path(p).name for p in h["support_files"]] == ["axis_if.sv", "axil_if.sv"]
    assert set(h["modules"]["top"]["children"]) == {"axil_regs", "stream_filter"}
