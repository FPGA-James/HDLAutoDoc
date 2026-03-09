#!/usr/bin/env python3
"""
include_registers.py
--------------------
Looks for an auto-generated register map HTML file at:
    <project_root>/registers/generated/*.html

If found:
  - Copies the first match to docs/_static/registers.html
  - Writes docs/registers.rst embedding it in a full-height iframe

If not found:
  - Writes docs/registers.rst with a clear "not yet generated" notice

Always writes docs/registers.rst so the toctree entry never breaks.

Usage:
    python scripts/include_registers.py <project_root> <docs_dir>
"""

import shutil
import sys
from pathlib import Path


REGISTERS_RST_PLACEHOLDER = """\
Registers
=========

.. admonition:: Register map not yet generated
   :class: warning

   No register map HTML file was found at ``registers/generated/*.html``.

   To generate it, run your register builder tool and re-run ``make html``.

   Expected location::

       registers/
       └── generated/
           └── <your_register_map>.html

"""

REGISTERS_RST_TEMPLATE = """\
Registers
=========

Auto-generated register map imported from ``{src_rel}``.

.. raw:: html

   <div style="
       width: 100%;
       height: 80vh;
       min-height: 600px;
       border: 1px solid #e1e4e5;
       border-radius: 4px;
       overflow: hidden;
   ">
     <iframe
       src="_static/registers.html"
       style="width:100%; height:100%; border:none;"
       title="Register Map">
     </iframe>
   </div>

.. note::

   This page embeds the register map generated at ``{src_rel}``.
   Re-run ``make html`` after regenerating the register map to update it.

"""


if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.exit("Usage: include_registers.py <project_root> <docs_dir>")

    project_root = Path(sys.argv[1])
    docs_dir     = Path(sys.argv[2])
    static_dir   = docs_dir / "_static"
    registers_rst = docs_dir / "registers.rst"

    # Glob for generated HTML
    pattern = project_root / "registers" / "generated" / "*.html"
    matches = sorted(pattern.parent.glob(pattern.name)) if pattern.parent.exists() else []

    if matches:
        if len(matches) > 1:
            print(f"  WARNING: multiple HTML files in registers/generated/ — using {matches[0].name}")
            for m in matches[1:]:
                print(f"           ignoring: {m.name}")
        src      = matches[0]
        src_rel  = src.relative_to(project_root)
        dest     = static_dir / "registers.html"

        static_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)
        registers_rst.write_text(REGISTERS_RST_TEMPLATE.format(src_rel=src_rel))
        print(f"  → registers: copied {src_rel} → docs/_static/registers.html")
        print(f"  → {registers_rst}")
    else:
        registers_rst.write_text(REGISTERS_RST_PLACEHOLDER)
        print(f"  → registers: no HTML found at registers/generated/*.html — writing placeholder")
        print(f"  → {registers_rst}")