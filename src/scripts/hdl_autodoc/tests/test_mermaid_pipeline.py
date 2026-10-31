"""
Mermaid diagrams written in source comments render through the real pipeline.

Each case builds a tiny Sphinx HTML project from what the tool itself generates
(vhdl:autoentity, the SystemVerilog entity page, a process page) and checks the
diagram arrives in the HTML intact.
"""

import html
import io
import re
import textwrap
from pathlib import Path

from sphinx.application import Sphinx
from sphinx.util.docutils import docutils_namespace

from extract_processes import find_processes_sv, find_processes_vhdl, render_process_page
from generate_rst import entity_rst, source_rst

HDL_AUTODOC_DOCS = Path(__file__).parents[3] / "docs" / "hdl_autodoc"
CDN = "cdn.jsdelivr.net/npm/mermaid"

VHDL = """\
library ieee;
use ieee.std_logic_1164.all;

-- Master side of a write handshake.
--
-- .. mermaid::
--    :caption: Write handshake
--
--    sequenceDiagram
--      Master->>Slave: valid
--      Slave-->>Master: ready
entity master is
    port (clk : in std_logic);
end entity master;
architecture rtl of master is begin end architecture rtl;
"""

SV = """\
// Stream filter.
//
// Forwards bytes at or above a threshold.
//
// .. mermaid::
//    :caption: Data path
//
//    flowchart LR
//      S[s_axis] --> F{">= threshold?"}
//      F -- yes --> M[m_axis]
//      F -- no --> D[dropped]
module stream_filter (input logic clk);
endmodule
"""

PROCESS = """\
// p_state: State machine.
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


def _build(tmp_path, files, conf_extra=""):
    """Build an HTML site from {name: text}; return (output dir, warnings)."""
    src = tmp_path / "src"
    src.mkdir()
    for name, text in files.items():
        (src / name).write_text(text)
    (src / "conf.py").write_text(
        f'import sys\nsys.path.insert(0, r"{HDL_AUTODOC_DOCS}")\n'
        'extensions = ["sphinxcontrib.mermaid", "sphinxvhdl.vhdl"]\n'
        f"{conf_extra}"
        "import mermaid_support\n"
        "def setup(app):\n    mermaid_support.setup_mermaid(app)\n")
    out, warnings = tmp_path / "out", io.StringIO()
    with docutils_namespace():
        Sphinx(str(src), str(src), str(out), str(tmp_path / "dt"), "html",
               status=io.StringIO(), warning=warnings).build()
    return out, warnings.getvalue()


def _diagrams(page: Path) -> list[str]:
    """The Mermaid source of every diagram on a built page, unescaped."""
    text = page.read_text()
    return [html.unescape(m) for m in re.findall(r'<pre\s+class="mermaid"[^>]*>(.*?)</pre>', text, re.S)]


def _dedented(diagram: str) -> str:
    """The diagram text with template whitespace removed.  The extension indents only
    the first line (its template), so the other lines show the author's indentation."""
    lines = diagram.strip("\n").rstrip().splitlines()
    lines[0] = lines[0].lstrip()
    return "\n".join(lines)


def test_vhdl_entity_header_diagram_renders_with_its_caption_and_arrows(tmp_path):
    vhdl_dir = tmp_path / "vhdl"
    vhdl_dir.mkdir()
    (vhdl_dir / "master.vhd").write_text(VHDL)
    out, warnings = _build(
        tmp_path, {"index.rst": "Index\n=====\n\n.. vhdl:autoentity:: master\n"},
        conf_extra=f'vhdl_autodoc_source_path = [r"{vhdl_dir}"]\n')
    assert warnings == ""
    (diagram,) = _diagrams(out / "index.html")
    assert _dedented(diagram) == ("sequenceDiagram\n  Master->>Slave: valid\n"
                                  "  Slave-->>Master: ready")
    assert "Write handshake" in (out / "index.html").read_text()


def test_sv_module_header_diagram_renders_through_the_entity_page(tmp_path):
    sv_dir = tmp_path / "svsrc"
    sv_dir.mkdir()
    (sv_dir / "stream_filter.sv").write_text(SV)
    entity = {"name": "stream_filter", "file": "stream_filter.sv"}
    out, warnings = _build(tmp_path, {
        "index.rst": "Index\n=====\n\n.. toctree::\n\n   entity\n",
        "entity.rst": entity_rst(entity, src_dir=sv_dir),
        "stream_filter_source.rst": source_rst(entity, enabled=False),
    })
    assert warnings == ""
    (diagram,) = _diagrams(out / "entity.html")
    text = _dedented(diagram)
    assert text.startswith("flowchart LR\n  S[s_axis]")
    assert "F -- yes --> M[m_axis]" in text and "F -- no --> D[dropped]" in text
    assert "Data path" in (out / "entity.html").read_text()


def test_process_comment_diagram_renders_on_the_process_page_with_nesting(tmp_path):
    proc = find_processes_sv(PROCESS)[0]
    out, warnings = _build(tmp_path, {
        "index.rst": "Index\n=====\n\n.. toctree::\n\n   p_state\n",
        "p_state.rst": render_process_page(proc, "t.sv", lambda body: {}),
    })
    assert warnings == ""
    (diagram,) = _diagrams(out / "p_state.html")
    assert _dedented(diagram) == (
        "stateDiagram-v2\n  [*] --> IDLE\n  state BUSY {\n    [*] --> WORK\n  }\n"
        "  IDLE --> BUSY: start")
    assert "States" in (out / "p_state.html").read_text()


def test_a_vhdl_process_comment_diagram_renders_with_its_arrows(tmp_path):
    source = textwrap.dedent("""\
        -- p_flow: Flow.
        --
        -- .. mermaid::
        --
        --    flowchart LR
        --      A --> B
        --      B -->|again| A
        p_flow : process(clk) is
        begin
            null;
        end process p_flow;
        """).splitlines()
    proc = find_processes_vhdl(source)[0]
    out, warnings = _build(tmp_path, {
        "index.rst": "Index\n=====\n\n.. toctree::\n\n   p_flow\n",
        "p_flow.rst": render_process_page(proc, "t.vhd", lambda body: {}),
    })
    assert warnings == ""
    (diagram,) = _diagrams(out / "p_flow.html")
    assert "A --> B" in diagram and "B -->|again| A" in diagram


def test_a_page_without_a_diagram_has_no_mermaid_element_and_no_script(tmp_path):
    out, warnings = _build(tmp_path, {"index.rst": "Index\n=====\n\nJust text.\n"})
    assert warnings == ""
    text = (out / "index.html").read_text()
    assert 'class="mermaid"' not in text and CDN not in text
