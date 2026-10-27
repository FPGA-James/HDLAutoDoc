#!/usr/bin/env python3
"""
generate_schematic.py
---------------------
Generates an RTL schematic for a VHDL or SystemVerilog module using yosys.

Pipeline:
  yosys (synthesis + opt) → write_json → netlistsvg → <module>_schematic.svg

netlistsvg gives the nicest rendering (proper mux/DFF symbols) but is an
`npm install -g netlistsvg` dependency that's easy to miss. If it's missing,
or its render fails, this falls back to yosys's own `show -format svg`
renderer, which only needs graphviz `dot` (already a hard dependency of
this pipeline's other diagrams).

For VHDL modules, requires yosys with the ghdl-yosys-plugin (OSS CAD Suite).
For SystemVerilog modules, requires yosys with native SV support.

Writes:
  <module_name>_schematic.svg  — gate-level schematic (netlistsvg or yosys-show)
  <module_name>_schematic.pdf  — PDF sibling for LaTeX builds (needs rsvg-convert;
                                 skipped, non-fatally, if unavailable)

Usage:
    python generate_schematic.py <file.vhd|file.sv> <module_name> <output_dir>

Always exits with code 0 — schematic generation is optional and failures are
non-fatal.  The build continues; the block diagram RST simply omits the
schematic section if the SVG was not produced.
"""

import shutil
import subprocess
import sys
from pathlib import Path


def _have(tool: str) -> bool:
    return shutil.which(tool) is not None


def _have_ghdl_plugin() -> bool:
    """Return True if yosys can load the ghdl plugin."""
    r = subprocess.run(
        ["yosys", "-m", "ghdl", "-p", ""],
        capture_output=True,
        text=True,
    )
    return "Can't load module" not in r.stderr


def _run_yosys(args: list[str]) -> tuple[bool, str]:
    """Run yosys with *args; return (success, stderr_snippet)."""
    r = subprocess.run(["yosys"] + args, capture_output=True, text=True)
    return r.returncode == 0, r.stderr[:600] if r.stderr else ""


def _build_prefix_vhdl(src: Path, module_name: str,
                       extra_srcs: list[Path]) -> tuple[str, list[str]] | None:
    """Build the read+elaborate yosys script prefix for a VHDL module.

    Returns (script_prefix, extra_yosys_args), or None if this design can't
    be elaborated at all (missing ghdl plugin, or a SystemVerilog dependency
    ghdl can't read) — the caller should treat that as a schematic skip.
    """
    if not _have_ghdl_plugin():
        print(f"  ! SCHEMATIC [{module_name}]: ghdl-yosys-plugin not available — skipping")
        return None

    # Collect all VHDL files: extra deps first (leaves before top), then src.
    # Deduplicate while preserving order so ghdl sees units before they're used.
    seen: set[Path] = set()
    vhdl_files: list[Path] = []
    sv_deps: list[str] = []
    for f in extra_srcs + [src]:
        if f in seen:
            continue
        seen.add(f)
        if f.suffix.lower() in (".vhd", ".vhdl"):
            vhdl_files.append(f)
        elif f.suffix.lower() in (".sv", ".svh"):
            sv_deps.append(f.stem)

    # If this module instantiates SystemVerilog submodules, ghdl cannot
    # elaborate it — skip cleanly rather than dumping a synthesis error.
    if sv_deps:
        sv_names = ", ".join(sv_deps)
        print(f"  ! SCHEMATIC [{module_name}]: mixed-language design "
              f"(SystemVerilog deps: {sv_names}) — ghdl cannot elaborate, skipping")
        return None

    files_str = " ".join(str(f) for f in vhdl_files)
    script_prefix = f"ghdl --std=08 {files_str} -e {module_name}; proc; opt;"
    return script_prefix, ["-m", "ghdl"]


def _build_prefix_sv(src: Path, extra_srcs: list[Path]) -> tuple[str, list[str]]:
    """Build the read+elaborate yosys script prefix for a SystemVerilog module."""
    seen: set[Path] = set()
    sv_files: list[Path] = []
    for f in extra_srcs + [src]:
        if f not in seen and f.suffix.lower() in (".sv", ".svh"):
            seen.add(f)
            sv_files.append(f)

    read_cmds = " ".join(f"read_verilog -sv {f};" for f in sv_files)
    script_prefix = f"{read_cmds} proc; opt;"
    return script_prefix, []


# Custom netlistsvg skin (colours, font, light/dark palette). Optional: if the
# file is missing netlistsvg falls back to its bundled default skin.
NETLISTSVG_SKIN = Path(__file__).with_name("netlistsvg_skin.svg")


def _run_netlistsvg(json_path: Path, svg_path: Path, module_name: str) -> bool:
    cmd = ["netlistsvg", str(json_path), "-o", str(svg_path)]
    if NETLISTSVG_SKIN.is_file():
        cmd += ["--skin", str(NETLISTSVG_SKIN)]
    r = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
    )
    if r.returncode != 0:
        print(f"  ! SCHEMATIC [{module_name}]: netlistsvg failed")
        if r.stderr:
            print("    " + r.stderr[:400].replace("\n", "\n    "))
        return False
    return True


def _run_yosys_show(script_prefix: str, yosys_args: list[str], module_name: str,
                    svg_prefix: Path) -> bool:
    """Fallback renderer: ask yosys to render the current design itself via
    `show`, instead of handing a JSON netlist to netlistsvg. Needs graphviz
    `dot` on PATH (yosys shells out to it). Writes `<svg_prefix>.svg`."""
    tail = f"show -format svg -viewer none -prefix {svg_prefix} {module_name}"
    ok, err = _run_yosys(yosys_args + ["-p", f"{script_prefix} {tail}"])
    if not ok:
        print(f"  ! SCHEMATIC [{module_name}]: yosys show failed")
        if err:
            print("    " + err.replace("\n", "\n    "))
    return ok


def _run_rsvg_convert(svg_path: Path, pdf_path: Path) -> bool:
    """Render a PDF sibling of the schematic so PDF builds (which can't embed
    raw SVG) have a candidate to fall back to. Best-effort; PDF builds simply
    omit the schematic if this — or rsvg-convert itself — isn't available."""
    if not _have("rsvg-convert"):
        return False
    r = subprocess.run(
        ["rsvg-convert", "-f", "pdf", "-o", str(pdf_path), str(svg_path)],
        capture_output=True,
        text=True,
    )
    return r.returncode == 0


def render_schematic(src_path: Path, module_name: str, extra_srcs: list[Path],
                     json_path: Path, svg_path: Path) -> bool:
    """Render the RTL schematic, preferring netlistsvg and falling back to
    yosys's own `show` renderer if netlistsvg is missing or its render fails."""
    ext = src_path.suffix.lower()
    if ext in (".vhd", ".vhdl"):
        built = _build_prefix_vhdl(src_path, module_name, extra_srcs)
    elif ext in (".sv", ".svh"):
        built = _build_prefix_sv(src_path, extra_srcs)
    else:
        print(f"  ! SCHEMATIC [{module_name}]: unsupported file type '{ext}' — skipping")
        return False
    if built is None:
        return False
    script_prefix, yosys_args = built

    have_netlistsvg = _have("netlistsvg")
    have_dot = _have("dot")
    if not have_netlistsvg and not have_dot:
        print(f"  ! SCHEMATIC [{module_name}]: no schematic renderer available — skipping")
        print("    Install netlistsvg (npm install -g netlistsvg), "
              "or graphviz for the yosys-show fallback")
        return False

    if have_netlistsvg:
        ok, err = _run_yosys(yosys_args + ["-p", f"{script_prefix} write_json {json_path}"])
        if not ok:
            print(f"  ! SCHEMATIC [{module_name}]: yosys/ghdl synthesis failed")
            if err:
                print("    " + err.replace("\n", "\n    "))
        if ok:
            ok = _run_netlistsvg(json_path, svg_path, module_name)
        if json_path.exists():
            json_path.unlink()
        if ok:
            print(f"  → {svg_path}")
            return True
        if have_dot:
            print(f"  ! SCHEMATIC [{module_name}]: falling back to yosys show")

    if have_dot:
        ok = _run_yosys_show(script_prefix, yosys_args, module_name, svg_path.with_suffix(""))
        # yosys `show -prefix` always writes a .dot intermediate alongside the SVG.
        dot_path = svg_path.with_suffix(".dot")
        if dot_path.exists():
            dot_path.unlink()
        if ok:
            print(f"  → {svg_path} (yosys show fallback)")
            return True

    return False


if __name__ == "__main__":
    if len(sys.argv) < 4:
        sys.exit("Usage: generate_schematic.py <file.vhd|file.sv> <module_name> <output_dir>")

    src_path    = Path(sys.argv[1])
    module_name = sys.argv[2]
    output_dir  = Path(sys.argv[3])
    output_dir.mkdir(parents=True, exist_ok=True)

    if not _have("yosys"):
        print(f"  ! SCHEMATIC [{module_name}]: yosys not found — skipping")
        sys.exit(0)

    extra_srcs = [Path(f) for f in sys.argv[4:]]
    json_path  = output_dir / f"{module_name}_schematic.json"
    svg_path   = output_dir / f"{module_name}_schematic.svg"
    pdf_path   = output_dir / f"{module_name}_schematic.pdf"

    if render_schematic(src_path, module_name, extra_srcs, json_path, svg_path):
        if _run_rsvg_convert(svg_path, pdf_path):
            print(f"  → {pdf_path}")

    sys.exit(0)  # Always non-fatal
