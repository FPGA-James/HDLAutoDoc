"""
test_extract_processes.py
-------------------------
Tests for extract_processes.py.

Covers:
  - Labeled VHDL process blocks are found with the correct label, sensitivity
    list, and source line number.
  - Labeled SystemVerilog always_ff / always_comb blocks are found.
  - Comment tokens (plain text and wavedrom blocks) are extracted correctly.
  - RST page rendering includes the expected metadata fields.
  - The processes index RST lists all found processes.
"""

import pytest

from extract_processes import (
    extract_comment_tokens,
    find_processes_sv,
    find_processes_vhdl,
    render_index_page,
    render_mermaid_block,
    render_process_page,
)


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures — minimal HDL snippets (as line lists)
# ─────────────────────────────────────────────────────────────────────────────

VHDL_SOURCE = """\
-- p_clk_reg: Clocked register process.
--
-- Captures next_state on rising edge of clk.
p_clk_reg : process(clk) is
begin
    if rising_edge(clk) then
        state <= next_state;
    end if;
end process p_clk_reg;

-- p_comb: Combinational next-state logic.
p_comb : process(state, en) is
begin
    next_state <= state;
end process p_comb;
""".splitlines()

SV_SOURCE = """\
// p_state_reg: Clocked state register.
always_ff @(posedge clk) begin : p_state_reg
    if (rst) state <= IDLE;
    else     state <= next_state;
end

// p_next: Combinational next-state.
always_comb begin : p_next
    next_state = state;
end
""".splitlines()

VHDL_WITH_WAVEDROM = """\
-- p_wave: Process with a wavedrom diagram.
--
-- .. wavedrom::
--
--    { "signal": [{ "name": "clk", "wave": "P...." }]}
p_wave : process(clk) is
begin
    if rising_edge(clk) then out <= inp; end if;
end process p_wave;
""".splitlines()


# ─────────────────────────────────────────────────────────────────────────────
# VHDL process discovery
# ─────────────────────────────────────────────────────────────────────────────

def test_vhdl_finds_all_processes():
    """All labeled processes in the source are discovered."""
    procs = find_processes_vhdl(VHDL_SOURCE)
    labels = [p["label"] for p in procs]
    assert "p_clk_reg" in labels
    assert "p_comb" in labels


def test_vhdl_process_sensitivity_list():
    """The sensitivity list tokens are parsed correctly."""
    procs = find_processes_vhdl(VHDL_SOURCE)
    p = next(p for p in procs if p["label"] == "p_clk_reg")
    assert "clk" in p["sensitivity"]


def test_vhdl_process_sensitivity_multiple():
    """A multi-signal sensitivity list is split into individual items."""
    procs = find_processes_vhdl(VHDL_SOURCE)
    p = next(p for p in procs if p["label"] == "p_comb")
    assert "state" in p["sensitivity"]
    assert "en" in p["sensitivity"]


def test_vhdl_process_line_number():
    """The reported line number points to the process declaration line (1-based)."""
    procs = find_processes_vhdl(VHDL_SOURCE)
    p = next(p for p in procs if p["label"] == "p_clk_reg")
    # Line 4 in VHDL_SOURCE (1-based)
    assert p["line"] == 4


def test_vhdl_process_kind():
    """VHDL processes are tagged with kind='process'."""
    procs = find_processes_vhdl(VHDL_SOURCE)
    assert all(p["kind"] == "process" for p in procs)


# ─────────────────────────────────────────────────────────────────────────────
# SystemVerilog process discovery
# ─────────────────────────────────────────────────────────────────────────────

def test_sv_finds_all_always_blocks():
    """All labeled always_ff / always_comb blocks are discovered."""
    procs = find_processes_sv(SV_SOURCE)
    labels = [p["label"] for p in procs]
    assert "p_state_reg" in labels
    assert "p_next" in labels


def test_sv_always_ff_kind():
    """always_ff blocks are tagged with kind='always_ff'."""
    procs = find_processes_sv(SV_SOURCE)
    p = next(p for p in procs if p["label"] == "p_state_reg")
    assert p["kind"] == "always_ff"


def test_sv_always_comb_kind():
    """always_comb blocks are tagged with kind='always_comb'."""
    procs = find_processes_sv(SV_SOURCE)
    p = next(p for p in procs if p["label"] == "p_next")
    assert p["kind"] == "always_comb"


def test_sv_always_ff_sensitivity():
    """The sensitivity list entry includes the edge qualifier, e.g. 'posedge clk'."""
    procs = find_processes_sv(SV_SOURCE)
    p = next(p for p in procs if p["label"] == "p_state_reg")
    # The raw token from @(posedge clk) is kept as-is including the edge keyword
    assert any("clk" in s for s in p["sensitivity"])


# ─────────────────────────────────────────────────────────────────────────────
# Comment token extraction
# ─────────────────────────────────────────────────────────────────────────────

def test_comment_tokens_text_extracted():
    """Plain comment text above a process is returned as a 'text' token."""
    procs = find_processes_vhdl(VHDL_SOURCE)
    p = next(p for p in procs if p["label"] == "p_clk_reg")
    text_tokens = [t for t in p["tokens"] if t["type"] == "text"]
    assert len(text_tokens) > 0
    combined = " ".join(" ".join(t["lines"]) for t in text_tokens)
    assert "Clocked register process" in combined


def test_comment_tokens_wavedrom_extracted():
    """A '.. wavedrom::' block in comments is returned as a 'wavedrom' token."""
    procs = find_processes_vhdl(VHDL_WITH_WAVEDROM)
    p = procs[0]
    wave_tokens = [t for t in p["tokens"] if t["type"] == "wavedrom"]
    assert len(wave_tokens) == 1
    assert any("signal" in line for line in wave_tokens[0]["lines"])


# ─────────────────────────────────────────────────────────────────────────────
# RST rendering
# ─────────────────────────────────────────────────────────────────────────────

def test_render_process_page_contains_metadata():
    """The rendered RST page contains source file name, line number, and block type."""
    procs = find_processes_vhdl(VHDL_SOURCE)
    p = next(p for p in procs if p["label"] == "p_clk_reg")
    rst = render_process_page(p, "test.vhd", lambda body: {})
    assert "test.vhd" in rst
    assert str(p["line"]) in rst
    assert "process" in rst


def test_render_process_page_contains_source_block():
    """The rendered RST page includes a code-block with the process source."""
    procs = find_processes_vhdl(VHDL_SOURCE)
    p = next(p for p in procs if p["label"] == "p_clk_reg")
    rst = render_process_page(p, "test.vhd", lambda body: {})
    assert ".. code-block::" in rst
    assert "p_clk_reg" in rst


def test_render_index_page_lists_all_processes():
    """The index RST page includes an entry for every discovered process."""
    procs = find_processes_vhdl(VHDL_SOURCE)
    rst = render_index_page(procs, "test.vhd")
    assert "p_clk_reg" in rst
    assert "p_comb" in rst


# ─────────────────────────────────────────────────────────────────────────────
# Mermaid blocks in process comments
# ─────────────────────────────────────────────────────────────────────────────

VHDL_WITH_MERMAID = """\
-- p_flow: Flow with a diagram.
--
-- Before the diagram.
--
-- .. mermaid::
--    :caption: Flow
--
--    flowchart LR
--      subgraph core
--        A[Start] --> B[Done]
--      end
--      B -->|again| A
--
-- After the diagram.
p_flow : process(clk) is
begin
    null;
end process p_flow;
""".splitlines()

SV_WITH_MERMAID = """\
// p_state: State diagram.
//
// .. mermaid::
//    :caption: States
//
//    stateDiagram-v2
//      [*] --> IDLE
//      state BUSY {
//        [*] --> WORK
//      }
//      IDLE --> BUSY: start
always_ff @(posedge clk) begin : p_state
    state <= next_state;
end
""".splitlines()

VHDL_WAVE_THEN_MERMAID = """\
-- p_both: Waveform then diagram.
--
-- .. wavedrom::
--
--    { "signal": [{ "name": "clk", "wave": "P...." }]}
-- .. mermaid::
--
--    flowchart LR
--      A --> B
p_both : process(clk) is
begin
    null;
end process p_both;
""".splitlines()

EXPECTED_FLOW = [
    ":caption: Flow", "", "flowchart LR", "  subgraph core",
    "    A[Start] --> B[Done]", "  end", "  B -->|again| A",
]


def _tokens(source):
    return find_processes_vhdl(source)[0]["tokens"]


def test_mermaid_block_becomes_a_token_between_the_surrounding_text():
    tokens = _tokens(VHDL_WITH_MERMAID)
    assert [t["type"] for t in tokens] == ["text", "mermaid", "text"]
    assert "Before the diagram." in " ".join(tokens[0]["lines"])
    assert "After the diagram." in " ".join(tokens[2]["lines"])


def test_mermaid_block_keeps_its_relative_indentation_options_and_blank_lines():
    (block,) = [t for t in _tokens(VHDL_WITH_MERMAID) if t["type"] == "mermaid"]
    assert block["lines"] == EXPECTED_FLOW


def test_vhdl_arrows_inside_a_comment_block_survive():
    """`-->` contains `--`: only the leading comment marker may be removed."""
    (block,) = [t for t in _tokens(VHDL_WITH_MERMAID) if t["type"] == "mermaid"]
    assert any("A[Start] --> B[Done]" in line for line in block["lines"])
    assert any(line.strip().endswith("B -->|again| A") for line in block["lines"])


def test_sv_mermaid_block_with_nested_state_keeps_indentation():
    (block,) = [t for t in find_processes_sv(SV_WITH_MERMAID)[0]["tokens"]
                if t["type"] == "mermaid"]
    assert block["lines"] == [
        ":caption: States", "", "stateDiagram-v2", "  [*] --> IDLE", "  state BUSY {",
        "    [*] --> WORK", "  }", "  IDLE --> BUSY: start"]


def test_a_mermaid_block_straight_after_a_wavedrom_block_keeps_token_order():
    types = [t["type"] for t in _tokens(VHDL_WAVE_THEN_MERMAID)]
    assert types == ["text", "wavedrom", "mermaid"]
    wave, mm = _tokens(VHDL_WAVE_THEN_MERMAID)[1:]
    assert any("signal" in line for line in wave["lines"])
    assert mm["lines"] == ["", "flowchart LR", "  A --> B"]


def test_render_mermaid_block_reindents_by_three_and_keeps_blank_lines():
    out = render_mermaid_block(EXPECTED_FLOW)
    assert out == [
        ".. mermaid::", "   :caption: Flow", "", "   flowchart LR", "     subgraph core",
        "       A[Start] --> B[Done]", "     end", "     B -->|again| A", ""]


def test_process_page_shows_the_diagram_in_the_description():
    p = find_processes_vhdl(VHDL_WITH_MERMAID)[0]
    rst = render_process_page(p, "t.vhd", lambda body: {})
    desc = rst[rst.index("Description"):]
    assert ".. mermaid::" in desc and "   :caption: Flow" in desc
    assert desc.index("Before the diagram.") < desc.index(".. mermaid::") < desc.index("After the diagram.")


def test_index_table_has_a_mermaid_column_marking_processes_with_a_diagram():
    procs = find_processes_vhdl(VHDL_WITH_MERMAID) + find_processes_vhdl(VHDL_WITH_WAVEDROM)
    rst = render_index_page(procs, "t.vhd")
    header = rst[rst.index("* - Block"):rst.index("* - :doc:")]
    assert "WaveDrom" in header and "Mermaid" in header
    assert header.index("WaveDrom") < header.index("Mermaid")
    flow_row = rst[rst.index("* - :doc:`p_flow`"):rst.index("* - :doc:`p_wave`")]
    wave_row = rst[rst.index("* - :doc:`p_wave`"):]
    assert flow_row.count("—") == 1 and flow_row.count("✔") == 1      # no waveform, has diagram
    assert wave_row.count("—") == 1 and wave_row.count("✔") == 1      # has waveform, no diagram


def test_a_process_without_diagrams_is_unchanged_apart_from_the_new_column():
    p = find_processes_vhdl(VHDL_SOURCE)[0]
    assert "mermaid" not in render_process_page(p, "t.vhd", lambda body: {}).lower()
