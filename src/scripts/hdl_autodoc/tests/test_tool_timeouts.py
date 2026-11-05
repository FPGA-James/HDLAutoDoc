"""A schematic tool that hangs must not hang the build: each external run has a time limit."""

import time

import pytest

import generate_schematic


@pytest.fixture
def hanging_tools(tmp_path, monkeypatch):
    """`yosys`, `netlistsvg` and `rsvg-convert` that never finish, first on PATH; a short limit."""
    for tool in ("yosys", "netlistsvg", "rsvg-convert"):
        script = tmp_path / tool
        script.write_text("#!/bin/sh\nexec sleep 30\n")
        script.chmod(0o755)
    monkeypatch.setenv("PATH", f"{tmp_path}:/usr/bin:/bin")
    monkeypatch.setattr(generate_schematic, "TOOL_TIMEOUT_S", 0.3)
    return tmp_path


def _quick(call):
    started = time.monotonic()
    result = call()
    assert time.monotonic() - started < 5, "the call waited for the hanging tool"
    return result


def test_a_hanging_yosys_is_reported_as_a_failed_run(hanging_tools):
    ok, message = _quick(lambda: generate_schematic._run_yosys(["-p", "help"]))
    assert ok is False and "timed out" in message


def test_a_hanging_netlistsvg_is_a_failed_render(hanging_tools, capsys):
    ok = _quick(lambda: generate_schematic._run_netlistsvg(hanging_tools / "a.json", hanging_tools / "a.svg", "m"))
    assert ok is False
    assert "timed out" in capsys.readouterr().out


def test_a_hanging_rsvg_convert_gives_no_pdf(hanging_tools):
    assert _quick(lambda: generate_schematic._run_rsvg_convert(hanging_tools / "a.svg", hanging_tools / "a.pdf")) is False


def test_probing_for_the_ghdl_plugin_does_not_hang(hanging_tools):
    assert isinstance(_quick(generate_schematic._have_ghdl_plugin), bool)
