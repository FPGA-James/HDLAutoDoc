"""Tests for generate_schematic.py's netlistsvg -> yosys-show renderer fallback."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import generate_schematic

from generate_schematic import render_schematic


def _sv_src(tmp_path: Path) -> Path:
    src = tmp_path / "pwm_controller.sv"
    src.write_text("module pwm_controller; endmodule")
    return src


def test_uses_netlistsvg_when_available(tmp_path):
    src = _sv_src(tmp_path)
    json_path = tmp_path / "pwm_controller_schematic.json"
    svg_path = tmp_path / "pwm_controller_schematic.svg"

    with patch("generate_schematic._have", side_effect=lambda t: t in ("netlistsvg", "dot")), \
         patch("generate_schematic._run_yosys", return_value=(True, "")), \
         patch("generate_schematic._run_netlistsvg", return_value=True) as netlistsvg, \
         patch("generate_schematic._run_yosys_show") as yosys_show:
        ok = render_schematic(src, "pwm_controller", [], json_path, svg_path)

    assert ok is True
    netlistsvg.assert_called_once()
    yosys_show.assert_not_called()


def test_falls_back_to_yosys_show_when_netlistsvg_missing(tmp_path):
    src = _sv_src(tmp_path)
    json_path = tmp_path / "pwm_controller_schematic.json"
    svg_path = tmp_path / "pwm_controller_schematic.svg"

    with patch("generate_schematic._have", side_effect=lambda t: t == "dot"), \
         patch("generate_schematic._run_yosys", return_value=(True, "")), \
         patch("generate_schematic._run_netlistsvg") as netlistsvg, \
         patch("generate_schematic._run_yosys_show", return_value=True) as yosys_show:
        ok = render_schematic(src, "pwm_controller", [], json_path, svg_path)

    assert ok is True
    netlistsvg.assert_not_called()
    yosys_show.assert_called_once()


def test_yosys_show_fallback_cleans_up_dot_intermediate(tmp_path):
    src = _sv_src(tmp_path)
    json_path = tmp_path / "pwm_controller_schematic.json"
    svg_path = tmp_path / "pwm_controller_schematic.svg"
    dot_path = tmp_path / "pwm_controller_schematic.dot"

    def fake_yosys_show(script_prefix, yosys_args, module_name, svg_prefix):
        dot_path.write_text("digraph {}")
        return True

    with patch("generate_schematic._have", side_effect=lambda t: t == "dot"), \
         patch("generate_schematic._run_yosys", return_value=(True, "")), \
         patch("generate_schematic._run_yosys_show", side_effect=fake_yosys_show):
        ok = render_schematic(src, "pwm_controller", [], json_path, svg_path)

    assert ok is True
    assert not dot_path.exists()


def test_falls_back_to_yosys_show_when_netlistsvg_render_fails(tmp_path):
    src = _sv_src(tmp_path)
    json_path = tmp_path / "pwm_controller_schematic.json"
    svg_path = tmp_path / "pwm_controller_schematic.svg"

    with patch("generate_schematic._have", side_effect=lambda t: t in ("netlistsvg", "dot")), \
         patch("generate_schematic._run_yosys", return_value=(True, "")), \
         patch("generate_schematic._run_netlistsvg", return_value=False), \
         patch("generate_schematic._run_yosys_show", return_value=True) as yosys_show:
        ok = render_schematic(src, "pwm_controller", [], json_path, svg_path)

    assert ok is True
    yosys_show.assert_called_once()


def test_returns_false_when_no_renderer_available(tmp_path):
    src = _sv_src(tmp_path)
    json_path = tmp_path / "pwm_controller_schematic.json"
    svg_path = tmp_path / "pwm_controller_schematic.svg"

    with patch("generate_schematic._have", return_value=False), \
         patch("generate_schematic._run_yosys") as run_yosys:
        ok = render_schematic(src, "pwm_controller", [], json_path, svg_path)

    assert ok is False
    run_yosys.assert_not_called()


def test_returns_false_for_unsupported_extension(tmp_path):
    src = tmp_path / "thing.txt"
    src.write_text("not hdl")
    json_path = tmp_path / "thing_schematic.json"
    svg_path = tmp_path / "thing_schematic.svg"

    with patch("generate_schematic._have", return_value=True), \
         patch("generate_schematic._run_yosys") as run_yosys:
        ok = render_schematic(src, "thing", [], json_path, svg_path)

    assert ok is False
    run_yosys.assert_not_called()


def test_netlistsvg_is_given_the_custom_skin(tmp_path):
    """The bundled skin is passed to netlistsvg, and dropped if the file is absent."""
    ok = MagicMock(returncode=0, stderr="")
    with patch("generate_schematic.subprocess.run", return_value=ok) as run:
        assert generate_schematic._run_netlistsvg(tmp_path / "a.json", tmp_path / "a.svg", "m")
    cmd = run.call_args[0][0]
    assert cmd[cmd.index("--skin") + 1] == str(generate_schematic.NETLISTSVG_SKIN)
    assert generate_schematic.NETLISTSVG_SKIN.is_file()

    with patch("generate_schematic.NETLISTSVG_SKIN", tmp_path / "missing.svg"), \
         patch("generate_schematic.subprocess.run", return_value=ok) as run:
        generate_schematic._run_netlistsvg(tmp_path / "a.json", tmp_path / "a.svg", "m")
    assert "--skin" not in run.call_args[0][0]


def test_sv_stub_mirrors_generics_and_ports_and_ties_outputs_low(tmp_path):
    """A SV child becomes a VHDL entity with matching ports, outputs driven to 0."""
    sv = tmp_path / "pwm.sv"
    sv.write_text(
        "module pwm #(\n    parameter int WIDTH = 8\n)(\n"
        "    input  logic              clk,\n"
        "    input  logic [WIDTH-1:0]  duty_i,\n"
        "    output logic              pwm_o,\n"
        "    output logic [3:0]        cnt_o\n);\nendmodule\n"
    )
    vhdl = generate_schematic.sv_module_stub_vhdl(sv)
    assert "entity pwm is" in vhdl
    assert "WIDTH : integer := 8" in vhdl
    assert "duty_i : in std_logic_vector(WIDTH-1 downto 0)" in vhdl
    assert "pwm_o <= '0';" in vhdl
    assert "cnt_o <= (others => '0');" in vhdl


def test_sv_stub_is_none_when_there_are_no_ports(tmp_path):
    sv = tmp_path / "x.sv"
    sv.write_text("module x; endmodule\n")
    assert generate_schematic.sv_module_stub_vhdl(sv) is None


def test_prepare_netlist_puts_module_first_and_strips_generic_suffixes(tmp_path):
    """The requested module leads, and ghdl's `<entity>_<generics>` names are tidied."""
    import json
    j = tmp_path / "n.json"
    j.write_text(json.dumps({"modules": {
        "child_8": {"cells": {}},
        "top": {"cells": {"u": {"type": "child_8"}}},
        "my_fifo_2": {"cells": {}},          # base not a known entity: left alone
    }}))
    generate_schematic._prepare_netlist(j, "top", {"top", "child"})
    data = json.loads(j.read_text())
    assert list(data["modules"]) == ["top", "child", "my_fifo_2"]
    assert data["modules"]["top"]["cells"]["u"]["type"] == "child"
