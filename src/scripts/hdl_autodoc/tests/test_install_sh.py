"""install.sh --vendor copies the tool, not its tests or caches."""

import shutil
import subprocess
from pathlib import Path

import pytest

INSTALL = Path(__file__).parents[4] / "install.sh"
pytestmark = pytest.mark.skipif(shutil.which("bash") is None or shutil.which("tar") is None, reason="needs bash and tar")


def _vendor(tmp_path):
    target = tmp_path / "project"
    target.mkdir()
    out = subprocess.run(["bash", str(INSTALL), str(target), "--vendor"], capture_output=True, text=True)
    assert out.returncode == 0, out.stderr + out.stdout
    return target / "third_party" / "hdl_autodoc" / "src"


def test_vendored_copy_runs_the_tool_and_adds_the_include(tmp_path):
    src = _vendor(tmp_path)
    assert (src / "autodoc.mk").is_file()
    assert (src / "scripts" / "hdl_autodoc" / "run_extract.py").is_file()
    assert (src / "docs" / "hdl_autodoc" / "conf.py").is_file()
    assert "include third_party/hdl_autodoc/src/autodoc.mk" in (src.parents[2] / "Makefile").read_text()


def test_vendored_copy_has_no_tests_and_no_python_caches(tmp_path):
    src = _vendor(tmp_path)
    assert not (src / "scripts" / "hdl_autodoc" / "tests").exists()
    assert not list(src.rglob("__pycache__")) and not list(src.rglob("*.pyc"))
