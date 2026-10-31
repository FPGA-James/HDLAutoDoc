"""Tests for parse_build_info.py: nextpnr utilisation, versions, warnings."""

from datetime import datetime

from parse_build_info import (
    BuildInfo,
    ResourceUse,
    WarningSummary,
    device_class,
    parse_build_info,
    parse_device_utilisation,
    summarise_warnings,
)

# Real excerpts from nextpnr-ecp5 0.8 and Yosys 0.56.
NEXTPNR_LOG = """\
Info: constraining clock net 'clk' to 100.00 MHz
Warning: IO 'rst' is unconstrained in LPF and will be automatically placed
Warning: IO 'q[15]' is unconstrained in LPF and will be automatically placed
Info: Device utilisation:
Info: \t          TRELLIS_IO:      18/    197     9%
Info: \t                DCCA:       1/     56     1%
Info: \t              DP16KD:       0/     56     0%
Info: \t          TRELLIS_FF:      16/  24288     0%
Info: \t        TRELLIS_COMB:      23/  24288     0%
Info: \t        TRELLIS_RAMW:       0/   3036     0%

Info: Placed 18 cells based on constraints.
Info: Max frequency for clock 'clk': 346.86 MHz (PASS at 100.00 MHz)
"""

YOSYS_LOG = """\

 /----------------------------------------------------------------------------\\
 |  yosys -- Yosys Open SYnthesis Suite                                       |
 \\----------------------------------------------------------------------------/
 Yosys 0.56+186 (git sha1 83d953e95, aarch64-apple-darwin23.5-clang++ 18.1.8 -fPIC -O3)

ABC: Warning: The network is combinational.
"""

BANNER = '"nextpnr-ecp5" -- Next Generation Place and Route (Version nextpnr-0.8-108-gca4f727f)\n'


# ── parse_device_utilisation ─────────────────────────────────────────────────

def test_device_utilisation_rows_in_order_with_zero_rows_kept():
    rows = parse_device_utilisation(NEXTPNR_LOG)
    assert [r.name for r in rows] == [
        "TRELLIS_IO", "DCCA", "DP16KD", "TRELLIS_FF", "TRELLIS_COMB", "TRELLIS_RAMW"]
    assert rows[3] == ResourceUse("TRELLIS_FF", 16, 24288, 0)
    assert rows[0] == ResourceUse("TRELLIS_IO", 18, 197, 9)
    assert rows[2].used == 0


def test_device_utilisation_stops_at_the_first_line_outside_the_block():
    rows = parse_device_utilisation(NEXTPNR_LOG)
    assert "Placed" not in " ".join(r.name for r in rows)
    assert len(rows) == 6


def test_device_utilisation_uses_the_last_block_when_printed_more_than_once():
    log = ("Info: Device utilisation:\nInfo: \t  TRELLIS_FF:   10/ 24288   0%\n\n"
           "Info: Device utilisation:\nInfo: \t  TRELLIS_FF:   16/ 24288   0%\n\n")
    assert parse_device_utilisation(log) == [ResourceUse("TRELLIS_FF", 16, 24288, 0)]


def test_device_utilisation_empty_when_there_is_no_block():
    assert parse_device_utilisation("") == []
    assert parse_device_utilisation("Info: nothing here\n") == []


# ── device_class ─────────────────────────────────────────────────────────────

def test_device_class_from_the_flip_flop_capacity():
    def with_ff(n):
        return [ResourceUse("TRELLIS_FF", 0, n, 0)]
    assert device_class(with_ff(24288)) == "ECP5 25k class"
    assert device_class(with_ff(43848)) == "ECP5 45k class"
    assert device_class(with_ff(83640)) == "ECP5 85k class"
    assert device_class(with_ff(12345)) is None
    assert device_class([]) is None
    assert device_class([ResourceUse("DP16KD", 0, 56, 0)]) is None


# ── parse_build_info ─────────────────────────────────────────────────────────

def test_build_info_reads_yosys_and_nextpnr_versions_and_device_class():
    info = parse_build_info(YOSYS_LOG, BANNER + NEXTPNR_LOG, None)
    assert info.yosys_version == "0.56+186"
    assert info.nextpnr_version == "nextpnr-0.8-108-gca4f727f"
    assert info.device == "ECP5 25k class"


def test_build_info_nextpnr_version_is_none_when_the_banner_is_absent():
    """The banner goes to stdout, not into a --log file."""
    info = parse_build_info(YOSYS_LOG, NEXTPNR_LOG, None)
    assert info.nextpnr_version is None
    assert info.yosys_version == "0.56+186"


def test_build_info_with_no_logs_is_all_none():
    assert parse_build_info(None, None, None) == BuildInfo(None, None, None, None)


def test_build_info_report_time_comes_from_the_mtime():
    info = parse_build_info(None, None, 1_700_000_000.0)
    assert info.report_time == datetime.fromtimestamp(1_700_000_000.0)


# ── summarise_warnings ───────────────────────────────────────────────────────

def test_warnings_that_differ_only_by_quoted_names_are_grouped():
    log = "".join(f"Warning: IO 'q[{i}]' is unconstrained in LPF and will be automatically placed\n"
                  for i in range(18))
    s = summarise_warnings(log)
    assert s.total == 18
    assert s.top == [("IO '…' is unconstrained in LPF and will be automatically placed", 18)]


def test_warnings_count_both_cases_and_prefixed_lines():
    yosys = ("src/bridge.sv:19: Warning: Identifier `\\m_axis.tvalid' is implicitly declared.\n"
             "src/bridge.sv:20: Warning: Identifier `\\m_axis.tlast' is implicitly declared.\n"
             "ABC: Warning: The network is combinational.\n"
             "WARNING: something uppercase\n")
    s = summarise_warnings(yosys, "Warning: IO 'a' is unconstrained\n")
    assert s.total == 5
    top = dict(s.top)
    assert top["Identifier '…' is implicitly declared."] == 2
    assert top["The network is combinational."] == 1
    assert top["something uppercase"] == 1


def test_warnings_top_is_sorted_by_count_then_text_and_limited():
    log = ("Warning: b\nWarning: b\nWarning: a\nWarning: c\nWarning: c\nWarning: d\n")
    s = summarise_warnings(log, top_n=3)
    assert s.top == [("b", 2), ("c", 2), ("a", 1)]
    assert s.total == 6


def test_warnings_empty_input():
    assert summarise_warnings() == WarningSummary(0, [])
    assert summarise_warnings("", "") == WarningSummary(0, [])
    assert summarise_warnings("Info: all fine\n") == WarningSummary(0, [])
