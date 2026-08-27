"""Tests for generate_schematic.py's netlistsvg -> yosys-show renderer fallback."""

from pathlib import Path
from unittest.mock import patch

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
