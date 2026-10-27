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
For SystemVerilog modules, requires yosys with native SV support.  Files that
define no module (packages, interfaces) are passed with `--support` and read
first, in the order given (the filelist's dependency order), so package-scoped
names and interface-typed ports resolve.

Writes:
  <module_name>_schematic.svg  — gate-level schematic (netlistsvg or yosys-show)
  <module_name>_schematic.pdf  — PDF sibling for LaTeX builds (needs rsvg-convert;
                                 skipped, non-fatally, if unavailable)

Usage:
    python generate_schematic.py <file.vhd|file.sv> <module_name> <output_dir>
        [dependency_file ...] [--support <support_file> ...]

Always exits with code 0 — schematic generation is optional and failures are
non-fatal.  The build continues; the block diagram RST simply omits the
schematic section if the SVG was not produced.
"""

import json
import re
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


def sv_module_stub_vhdl(sv_file: Path) -> str | None:
    """
    Build a VHDL entity with the same generics and ports as a SystemVerilog
    module, and an architecture that only ties its outputs low, so ghdl can elaborate a VHDL parent that
    instantiates it.  The child then shows up as a black-box instance.

    Returns None if the header uses something this simple converter does not
    handle (packed multi-dimensional ports, no module found).
    """
    from extract_block import extract_params_sv, extract_ports_sv

    text = sv_file.read_text(errors="replace")
    m = re.search(r"^\s*(?:module|macromodule)\s+(\w+)", text, re.MULTILINE)
    if not m:
        return None
    name = m.group(1)

    ports = extract_ports_sv(text)
    if not ports:
        return None
    generics = [p for p in extract_params_sv(text) if p["kind"] == "parameter"]

    port_lines = []
    drivers = []
    for p in ports:
        rng = p["range"]
        if rng:
            parts = rng.split(":")
            if len(parts) != 2 or "[" in rng:
                return None
            vtype = f"std_logic_vector({parts[0].strip()} downto {parts[1].strip()})"
        else:
            vtype = "std_logic"
        port_lines.append(f"    {p['name']} : {p['dir']} {vtype}")
        if p["dir"] == "out":
            # Drive outputs: undriven bits become 'x' in the netlist, which
            # netlistsvg's schema rejects.
            zero = "(others => '0')" if rng else "'0'"
            drivers.append(f"  {p['name']} <= {zero};")

    out = ["library ieee;", "use ieee.std_logic_1164.all;", "",
           f"entity {name} is"]
    if generics:
        out.append("  generic (")
        out.append(";\n".join(
            f"    {g['name']} : integer := {g['default'] or 0}" for g in generics))
        out.append("  );")
    out.append("  port (")
    out.append(";\n".join(port_lines))
    out += ["  );", f"end entity {name};", "",
            f"architecture stub of {name} is", "begin", *drivers,
            "end architecture stub;", ""]
    return "\n".join(out)


def _build_prefix_vhdl(src: Path, module_name: str,
                       extra_srcs: list[Path],
                       stub_dir: Path | None = None) -> tuple[str, list[str]] | None:
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
    sv_files: list[Path] = []
    for f in extra_srcs + [src]:
        if f in seen:
            continue
        seen.add(f)
        if f.suffix.lower() in (".vhd", ".vhdl"):
            vhdl_files.append(f)
        elif f.suffix.lower() in (".sv", ".svh"):
            sv_deps.append(f.stem)
            sv_files.append(f)

    # ghdl cannot read SystemVerilog.  Stand in a port-only VHDL stub for each
    # SV child so the parent elaborates and the child is drawn as a black box.
    # Without a stub directory (or if a header can't be converted), skip cleanly.
    if sv_deps:
        stubs: list[Path] = []
        for sv_file in sv_files:
            stub = sv_module_stub_vhdl(sv_file) if stub_dir is not None else None
            if stub is None:
                sv_names = ", ".join(f.stem for f in sv_files)
                print(f"  ! SCHEMATIC [{module_name}]: mixed-language design "
                      f"(SystemVerilog deps: {sv_names}) — ghdl cannot elaborate, skipping")
                return None
            stub_dir.mkdir(parents=True, exist_ok=True)
            stub_path = stub_dir / f"{sv_file.stem}_stub.vhd"
            stub_path.write_text(stub)
            stubs.append(stub_path)
        vhdl_files = stubs + vhdl_files

    files_str = " ".join(str(f) for f in vhdl_files)
    script_prefix = f"ghdl --std=08 {files_str} -e {module_name}; proc; opt;"
    return script_prefix, ["-m", "ghdl"]


def _sv_module_spelling(src: Path, module_name: str) -> str:
    """
    The module's name as spelled in the source.  hierarchy.json lower-cases
    module names, but `hierarchy -top` is case-sensitive for SystemVerilog.
    """
    try:
        text = src.read_text(errors="replace")
    except OSError:
        return module_name
    for m in re.finditer(
            r"^\s*(?:macromodule|module)\s+(?:automatic\s+|static\s+)?(\w+)",
            text, re.MULTILINE):
        if m.group(1).lower() == module_name.lower():
            return m.group(1)
    return module_name


def _build_prefix_sv(src: Path, extra_srcs: list[Path],
                     support_srcs: list[Path] | tuple = (),
                     module_name: str | None = None) -> tuple[str, list[str]]:
    """
    Build the read+elaborate yosys script prefix for a SystemVerilog module.

    Read order: support files (packages, interfaces; filelist order, so a package
    precedes its users), then the dependencies' files, then the module's own file.
    `hierarchy -top` then elaborates from the module: it resolves interface-typed
    ports into plain signals (netlistsvg rejects the raw interface port) and
    prunes anything the module does not use.
    """
    seen: set[Path] = set()
    sv_files: list[Path] = []
    for f in [*support_srcs, *extra_srcs, src]:
        if f not in seen and f.suffix.lower() in (".sv", ".svh"):
            seen.add(f)
            sv_files.append(f)

    top = _sv_module_spelling(src, module_name or src.stem)
    read_cmds = " ".join(f"read_verilog -sv {f};" for f in sv_files)
    script_prefix = f"{read_cmds} hierarchy -top {top}; proc; opt;"
    return script_prefix, []


# Custom netlistsvg skin (colours, font, light/dark palette). Optional: if the
# file is missing netlistsvg falls back to its bundled default skin.
NETLISTSVG_SKIN = Path(__file__).with_name("netlistsvg_skin.svg")


_GENERIC_SUFFIX_RE = re.compile(r"^(?P<base>.+?)(?:_\d+)+$")


def _prepare_netlist(json_path: Path, module_name: str, known: set[str]) -> None:
    """
    Tidy a hierarchical yosys netlist for netlistsvg.

    * netlistsvg draws the first module, so move the requested one to the front
      (the others stay so its instances resolve to their port lists).
    * ghdl names entities specialised by generics ``pwm_controller_8`` or
      ``traffic_light_50000000_5000_2000``; strip the generic-value suffix when
      the base is a known entity name, so boxes carry the entity name.
    """
    try:
        data = json.loads(json_path.read_text())
    except (OSError, ValueError):
        return  # cosmetic only — let netlistsvg try the netlist as written
    modules = data.get("modules", {})

    rename: dict[str, str] = {}
    for key in modules:
        m = _GENERIC_SUFFIX_RE.match(key)
        if m and m["base"] in known and m["base"] not in modules:
            rename[key] = m["base"]
        elif "$interfaces$" in key:
            # yosys derives one copy of a module per interface it is bound to,
            # `producer$interfaces$stream_if`; label the box with the module name.
            base = key.split("$interfaces$")[0]
            if base and base not in modules and base not in rename.values():
                rename[key] = base
    if rename:
        modules = {rename.get(k, k): v for k, v in modules.items()}
        for mod in modules.values():
            for cell in mod.get("cells", {}).values():
                cell["type"] = rename.get(cell.get("type"), cell.get("type"))

    top = next((k for k in modules if k.lower() == module_name.lower()), None)
    if top is not None and next(iter(modules)) != top:
        modules = {top: modules[top], **{k: v for k, v in modules.items() if k != top}}

    # yosys names a flattened interface member `if_name.signal`.  netlistsvg labels
    # such a port with the generic skin text ("output") instead of its name, so
    # swap the dot for an underscore on the module being drawn.
    if top is not None:
        ports = modules[top].get("ports", {})
        renamed: dict = {}
        for pname, pval in ports.items():
            new_name = pname.replace(".", "_")
            renamed[new_name if new_name == pname or new_name not in ports else pname] = pval
        modules[top]["ports"] = renamed

    data["modules"] = modules
    json_path.write_text(json.dumps(data))


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
                     json_path: Path, svg_path: Path,
                     support_srcs: list[Path] | None = None) -> bool:
    """Render the RTL schematic, preferring netlistsvg and falling back to
    yosys's own `show` renderer if netlistsvg is missing or its render fails."""
    stub_dir = json_path.parent / f".{module_name}_sv_stubs"
    try:
        return _render(src_path, module_name, extra_srcs, json_path, svg_path,
                       stub_dir, support_srcs or [])
    finally:
        shutil.rmtree(stub_dir, ignore_errors=True)


def _render(src_path: Path, module_name: str, extra_srcs: list[Path],
            json_path: Path, svg_path: Path, stub_dir: Path,
            support_srcs: list[Path]) -> bool:
    ext = src_path.suffix.lower()
    if ext in (".vhd", ".vhdl"):
        built = _build_prefix_vhdl(src_path, module_name, extra_srcs, stub_dir)
    elif ext in (".sv", ".svh"):
        built = _build_prefix_sv(src_path, extra_srcs, support_srcs, module_name)
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
            _prepare_netlist(json_path, module_name,
                             {module_name} | {p.stem for p in [src_path, *extra_srcs]})
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


def parse_source_args(args: list[str]) -> tuple[list[Path], list[Path]]:
    """
    Split the trailing CLI arguments into (dependency files, support files).
    Positional arguments are dependency files; `--support F` adds a support file
    (package/interface).  Order is preserved in both lists.
    """
    extra_srcs: list[Path] = []
    support_srcs: list[Path] = []
    i = 0
    while i < len(args):
        if args[i] == "--support" and i + 1 < len(args):
            support_srcs.append(Path(args[i + 1]))
            i += 2
        else:
            extra_srcs.append(Path(args[i]))
            i += 1
    return extra_srcs, support_srcs


if __name__ == "__main__":
    if len(sys.argv) < 4:
        sys.exit("Usage: generate_schematic.py <file.vhd|file.sv> <module_name> <output_dir> "
                 "[dependency_file ...] [--support <support_file> ...]")

    src_path    = Path(sys.argv[1])
    module_name = sys.argv[2]
    output_dir  = Path(sys.argv[3])
    output_dir.mkdir(parents=True, exist_ok=True)

    if not _have("yosys"):
        print(f"  ! SCHEMATIC [{module_name}]: yosys not found — skipping")
        sys.exit(0)

    extra_srcs, support_srcs = parse_source_args(sys.argv[4:])
    json_path  = output_dir / f"{module_name}_schematic.json"
    svg_path   = output_dir / f"{module_name}_schematic.svg"
    pdf_path   = output_dir / f"{module_name}_schematic.pdf"

    if render_schematic(src_path, module_name, extra_srcs, json_path, svg_path,
                        support_srcs):
        if _run_rsvg_convert(svg_path, pdf_path):
            print(f"  → {pdf_path}")

    sys.exit(0)  # Always non-fatal
