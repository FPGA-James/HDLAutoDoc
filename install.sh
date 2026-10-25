#!/usr/bin/env bash
# install.sh — add HDL AutoDoc to an existing HDL project
#
# Usage:
#   ./install.sh /path/to/your/hdl-project            # add as a git submodule
#   ./install.sh /path/to/your/hdl-project --vendor   # copy src/ in (no git needed)
#
# What it does:
#   1. Places the tool at <target>/third_party/hdl_autodoc
#        default  : `git submodule add` of this repository's origin URL
#        --vendor : copies this checkout's src/ to third_party/hdl_autodoc/src
#   2. Adds `include third_party/hdl_autodoc/src/autodoc.mk` to <target>/Makefile
#      (creates the Makefile if there is none; skips if the line is present)
#
# All documentation targets (doc-html, doc-pdf, doc-regs, ...) live in autodoc.mk,
# so updating the tool is a submodule update (or replacing the vendored copy) and
# never touches your own Makefile.  Run `make doc-help` for the target list.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SRC="$SCRIPT_DIR/src"
DEST_REL="third_party/hdl_autodoc"
INCLUDE_LINE="include $DEST_REL/src/autodoc.mk"

VENDOR=0
TARGET_ARG=""
for arg in "$@"; do
    case "$arg" in
        --vendor) VENDOR=1 ;;
        -*) echo "Unknown option: $arg"; exit 1 ;;
        *)  [[ -z "$TARGET_ARG" ]] && TARGET_ARG="$arg" || { echo "Too many arguments"; exit 1; } ;;
    esac
done

if [[ -z "$TARGET_ARG" ]]; then
    echo "Usage: $0 <target-project-directory> [--vendor]"
    exit 1
fi

TARGET="$(realpath "$TARGET_ARG")"
if [[ ! -d "$TARGET" ]]; then
    echo "Error: target directory '$TARGET' does not exist."
    exit 1
fi

echo "Installing HDL AutoDoc into: $TARGET"

# ── tool checkout ─────────────────────────────────────────────────────────────
if [[ -f "$TARGET/$DEST_REL/src/autodoc.mk" ]]; then
    echo "  → $DEST_REL already present — leaving it as is"
elif [[ $VENDOR -eq 1 ]]; then
    echo "  → Copying src/ to $DEST_REL/src ..."
    mkdir -p "$TARGET/$DEST_REL"
    cp -r "$SRC" "$TARGET/$DEST_REL/"
else
    if ! git -C "$TARGET" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
        echo "Error: $TARGET is not a git repository. Use --vendor to copy the tool instead."
        exit 1
    fi
    URL="$(git -C "$SCRIPT_DIR" remote get-url origin)"
    echo "  → Adding submodule $URL at $DEST_REL ..."
    git -C "$TARGET" submodule add "$URL" "$DEST_REL"
fi

# ── Makefile include ──────────────────────────────────────────────────────────
if [[ -f "$TARGET/Makefile" ]]; then
    if grep -qF "$INCLUDE_LINE" "$TARGET/Makefile"; then
        echo "  → Makefile already includes autodoc.mk — skipping"
    else
        echo "  → Appending include to existing Makefile ..."
        printf '\n# HDL AutoDoc — documentation targets (make doc-help)\n%s\n' "$INCLUDE_LINE" >> "$TARGET/Makefile"
    fi
else
    echo "  → Creating Makefile ..."
    printf '# HDL AutoDoc — documentation targets (make doc-help)\n%s\n' "$INCLUDE_LINE" > "$TARGET/Makefile"
fi

echo ""
echo "Done!  Next steps:"
echo "  1. Add your HDL source files to $TARGET/src/"
echo "  2. Create $TARGET/filelist.f listing your source files (dependency-first)"
echo "  3. Run: cd $TARGET && make doc-venv && make doc-html PROJECT=\"My Design\""
