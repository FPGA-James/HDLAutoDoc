#!/usr/bin/env bash
# install.sh — copy HDL AutoDoc tooling into an existing HDL project
#
# Usage:
#   ./install.sh /path/to/your/hdl-project
#
# What it does:
#   1. Copies scripts/hdl_autodoc and scripts/registers into <target>/scripts/
#   2. Copies docs/hdl_autodoc (Sphinx config + static assets) into <target>/docs/
#   3. Copies Makefile into <target>/Makefile (skips if already present)
#   4. Copies requirements.txt into <target>/requirements.txt (skips if already present)
#
# Re-running is safe — scripts/ and docs/hdl_autodoc/ are always overwritten
# with the latest tool version.  Makefile and requirements.txt are skipped if
# they already exist so your project-level customisations are preserved.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SRC="$SCRIPT_DIR/src"

if [[ $# -ne 1 ]]; then
    echo "Usage: $0 <target-project-directory>"
    exit 1
fi

TARGET="$(realpath "$1")"

if [[ ! -d "$TARGET" ]]; then
    echo "Error: target directory '$TARGET' does not exist."
    exit 1
fi

echo "Installing HDL AutoDoc into: $TARGET"

# ── scripts ───────────────────────────────────────────────────────────────────
echo "  → Copying scripts/hdl_autodoc ..."
mkdir -p "$TARGET/scripts"
cp -r "$SRC/scripts/hdl_autodoc" "$TARGET/scripts/"

echo "  → Copying scripts/registers ..."
cp -r "$SRC/scripts/registers" "$TARGET/scripts/"

# ── Sphinx config ─────────────────────────────────────────────────────────────
echo "  → Copying docs/hdl_autodoc ..."
mkdir -p "$TARGET/docs"
cp -r "$SRC/docs/hdl_autodoc" "$TARGET/docs/"

# ── Makefile ──────────────────────────────────────────────────────────────────
if [[ -f "$TARGET/Makefile" ]]; then
    echo "  → Makefile already exists — skipping (preserving yours)"
else
    echo "  → Copying Makefile ..."
    cp "$SRC/Makefile" "$TARGET/Makefile"
fi

# ── requirements.txt ──────────────────────────────────────────────────────────
if [[ -f "$TARGET/requirements.txt" ]]; then
    echo "  → requirements.txt already exists — skipping (preserving yours)"
else
    echo "  → Copying requirements.txt ..."
    cp "$SRC/requirements.txt" "$TARGET/requirements.txt"
fi

echo ""
echo "Done!  Next steps:"
echo "  1. Add your HDL source files to $TARGET/src/"
echo "  2. Create $TARGET/filelist.f listing your source files (dependency-first)"
echo "  3. Run: cd $TARGET && make venv && make html"
