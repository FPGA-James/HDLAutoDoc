# autodoc.mk — HDL AutoDoc make targets.
#
# Include this from your project Makefile (it is not meant to be run directly):
#   include path/to/hdl_autodoc/src/autodoc.mk
#
# Every target is prefixed `doc-` so it cannot clash with the host Makefile.

# Directory containing this file (the tool root). Must be evaluated at include time.
AUTODOC_HOME := $(patsubst %/,%,$(dir $(lastword $(MAKEFILE_LIST))))

# Use the project virtualenv if it exists, otherwise fall back to system python3.
PYTHON ?= $(shell test -f .venv/bin/python3 && echo .venv/bin/python3 || echo python3)

# Project name — used as the documentation title.
# Defaults to the parent directory name if left blank.
PROJECT        ?=

# Set to 1 to generate RTL schematics via yosys (requires yosys, and
# ghdl-yosys-plugin for VHDL modules).  Schematics are inserted into each
# module's block diagram page.
#   make doc-html SCHEMATICS=1
SCHEMATICS     ?= 0

# =============================================================================
# HDL AutoDoc (Sphinx pipeline) variables
# =============================================================================
AUTODOC_SPHINXOPTS    ?=
# Project metadata handed to the shared conf.py (all optional).
AUTODOC_AUTHOR        ?=
AUTODOC_RELEASE       ?=
AUTODOC_ENV            = AUTODOC_PROJECT="$(PROJECT)" AUTODOC_AUTHOR="$(AUTODOC_AUTHOR)" \
                         AUTODOC_RELEASE="$(AUTODOC_RELEASE)" AUTODOC_SRC="$(abspath $(AUTODOC_SRCDIR))" \
                         AUTODOC_SOURCEDIR="$(abspath $(AUTODOC_SOURCEDIR))"
AUTODOC_SPHINXBUILD    = $(PYTHON) -m sphinx
AUTODOC_SOURCEDIR      = docs/hdl_autodoc
AUTODOC_BUILDDIR       = $(AUTODOC_SOURCEDIR)/_build
AUTODOC_SCRIPTDIR      = $(AUTODOC_HOME)/scripts/hdl_autodoc
# Sphinx config (conf.py, _static, _templates) is read from the tool, not the project.
AUTODOC_CONFDIR        = $(AUTODOC_HOME)/docs/hdl_autodoc
AUTODOC_SRCDIR         = src
AUTODOC_FILELIST       = filelist.f
AUTODOC_HIERARCHY_JSON = $(AUTODOC_SOURCEDIR)/hierarchy.json
# Entry point filename for the register map HTML output.
# Override to match your register tool's output filename.
# Examples:
#   make doc AUTODOC_REG_ENTRY=index.html            (Questa Register Assistant)
#   make doc AUTODOC_REG_ENTRY=counter_regs.html     (custom generator)
#   make doc AUTODOC_REG_ENTRY=regmap.html           (other tools)
# Leave blank to auto-detect (picks index.html or first .html found).
AUTODOC_REG_ENTRY  ?= counter_regs.html

# ── Register generation + full doc build ─────────────────────────────────────
# Runs the register generator first, then the full Sphinx pipeline.
# Set AUTODOC_REGGEN to your register generation script path if different.
AUTODOC_REGGEN     ?= $(AUTODOC_HOME)/scripts/registers/generate.py


# =============================================================================
# Register generation variables
# =============================================================================
REGS_GENERATED_DIR := registers/generated
REGS_OUT_DIR       := registers/out


.PHONY: doc-help doc-venv doc-install doc-hierarchy doc-scaffold doc-extract \
        doc-reports doc-html doc-pdf doc-coverage doc-regs doc-all \
        doc-clean doc-clean-generated doc-clean-all

doc-help:
	@echo ""
	@echo "  make doc-venv                 Create .venv and install Python dependencies (recommended)"
	@echo "  make doc-install              Install Python dependencies into current environment"
	@echo "  make doc-hierarchy            Parse filelist.f and write hierarchy.json"
	@echo "  make doc-scaffold             Generate RST shells (runs hierarchy first)"
	@echo "  make doc-extract              Extract FSM + process docs (runs scaffold first)"
	@echo "  make doc-extract FORCE=1      Force re-extraction of all modules (bypass cache)"
	@echo "  make doc-coverage              Generate documentation coverage report"
	@echo "  make doc-html                 Build HTML documentation"
	@echo "  make doc-html SCHEMATICS=1    Build HTML with RTL schematics (requires yosys)"
	@echo "  make doc-pdf                  Build PDF documentation"
	@echo "  make doc-clean                Remove Sphinx build output only"
	@echo "  make doc-clean-generated      Remove always-regenerated files"
	@echo "  make doc-clean-all            Remove everything including hand-editable shells"
	@echo ""

doc-venv:
	python3 -m venv .venv
	.venv/bin/pip install --upgrade pip
	.venv/bin/pip install -r $(AUTODOC_HOME)/requirements.txt
	@echo ""
	@echo "Virtualenv ready. Activate with: source .venv/bin/activate"

doc-install:
	$(PYTHON) -m pip install -r $(AUTODOC_HOME)/requirements.txt

## ── Step 1: parse filelist.f → hierarchy.json ─────────────────────────────────
doc-hierarchy:
	@echo "Parsing design hierarchy from $(AUTODOC_FILELIST)..."
	$(PYTHON) $(AUTODOC_SCRIPTDIR)/parse_hierarchy.py $(AUTODOC_FILELIST) $(AUTODOC_HIERARCHY_JSON)

# ── Step 2: doc-scaffold RST shells from hierarchy ────────────────────────────────
doc-scaffold: doc-hierarchy
	@echo "Scaffolding RST files..."
	$(PYTHON) $(AUTODOC_SCRIPTDIR)/generate_rst.py $(AUTODOC_SRCDIR) $(AUTODOC_SOURCEDIR) "$(PROJECT)"

# ── Step 3: doc-extract FSM + processes for every module ─────────────────────────
# run_extract.py reads hierarchy.json — no hardcoded module names here.
# Pass --schematics when SCHEMATICS=1 to enable yosys RTL schematic generation.
doc-extract: doc-scaffold
	$(PYTHON) $(AUTODOC_SCRIPTDIR)/run_extract.py \
		$(AUTODOC_HIERARCHY_JSON) $(AUTODOC_SOURCEDIR) $(AUTODOC_SCRIPTDIR) \
		$(if $(filter 1,$(SCHEMATICS)),--schematics) $(if $(FORCE),--force)
	@echo "Regenerating timing pages..."
	$(PYTHON) $(AUTODOC_SCRIPTDIR)/generate_rst.py $(AUTODOC_SRCDIR) $(AUTODOC_SOURCEDIR) "$(PROJECT)"

# ── Step 3b: doc-coverage report (opt-in, runs independently after extract) ──────
doc-coverage: doc-hierarchy
	$(PYTHON) $(AUTODOC_SCRIPTDIR)/generate_coverage.py \
		$(AUTODOC_HIERARCHY_JSON) $(AUTODOC_SOURCEDIR)

# ── Step 3c: synthesis/PnR report ingestion (opt-in, after CI generates reports/) ──
doc-reports: doc-hierarchy
	@echo "Ingesting synthesis reports..."
	$(PYTHON) $(AUTODOC_SCRIPTDIR)/extract_reports.py \
		$(AUTODOC_HIERARCHY_JSON) $(AUTODOC_SOURCEDIR) reports
	@echo "Regenerating RST for implementation pages..."
	$(PYTHON) $(AUTODOC_SCRIPTDIR)/generate_rst.py $(AUTODOC_SRCDIR) $(AUTODOC_SOURCEDIR) "$(PROJECT)"

# ── Step 4: build HTML ────────────────────────────────────────────────────────
doc-html: doc-extract
	mkdir -p $(AUTODOC_SOURCEDIR)/_static
	$(AUTODOC_ENV) $(AUTODOC_SPHINXBUILD) -M html $(AUTODOC_SOURCEDIR) $(AUTODOC_BUILDDIR) -c $(AUTODOC_CONFDIR) $(AUTODOC_SPHINXOPTS)
	@echo ""
	@echo "Documentation built: $(AUTODOC_BUILDDIR)/html/index.html"

# ── PDF build ─────────────────────────────────────────────────────────────────
doc-pdf: doc-extract
	$(AUTODOC_ENV) $(AUTODOC_SPHINXBUILD) -M latexpdf $(AUTODOC_SOURCEDIR) $(AUTODOC_BUILDDIR) -c $(AUTODOC_CONFDIR) $(AUTODOC_SPHINXOPTS)

# -- make all docs, html and pdf
doc-all: doc-regs
	$(MAKE) doc-html
	$(MAKE) doc-pdf


# ─────────────────────────────────────────────────────────────────────────────
# Clean targets
#   Tier 1 — Sphinx build output              → make clean
#   Tier 2 — Always-regenerated files         → make clean-generated
#   Tier 3 — Hand-editable scaffolded shells  → make clean-all
# ─────────────────────────────────────────────────────────────────────────────
doc-clean:
	@echo "Removing Sphinx build output..."
	rm -rf $(AUTODOC_BUILDDIR)
	@echo "Done."

doc-clean-generated: doc-clean
	@echo "Removing always-regenerated files..."
	rm -f  $(AUTODOC_HIERARCHY_JSON)
	rm -f  $(AUTODOC_SOURCEDIR)/index.rst
	rm -f  $(AUTODOC_SOURCEDIR)/overview.rst
	rm -f  $(AUTODOC_SOURCEDIR)/hierarchy.rst
	rm -f  $(AUTODOC_SOURCEDIR)/hierarchy.dot
	rm -f  $(AUTODOC_SOURCEDIR)/registers.rst
	rm -f  $(AUTODOC_SOURCEDIR)/coverage.rst
	rm -f  $(AUTODOC_SOURCEDIR)/synthesis/index.rst
	rm -rf $(AUTODOC_SOURCEDIR)/synthesis
	rm -f  $(AUTODOC_SOURCEDIR)/.extract_cache.json
	rm -rf $(AUTODOC_SOURCEDIR)/_static/registers
	@# Per-module always-regenerated files (walk modules/ if it exists)
	@if [ -d $(AUTODOC_SOURCEDIR)/modules ]; then \
		find $(AUTODOC_SOURCEDIR)/modules -maxdepth 2 \
		     -name "index.rst" -o -name "fsm.rst" -o -name "timing.rst" \
		     -o -name "cdc.rst" -o -name "*_cdc.rst" -o -name "*_cdc.dot" \
		     -o -name "block.rst" -o -name "*_block.rst" -o -name "*_block.dot" \
		     -o -name "*_schematic.svg" \
		     -o -name "reset.rst" -o -name "*_reset.rst" -o -name "*_reset.dot" \
		     -o -name "registers.rst" \
		     -o -name "synthesis.rst" \
		     -o -name "*.dot"  -o -name "*.rst" -path "*/processes/*" \
		| xargs rm -f 2>/dev/null; \
		find $(AUTODOC_SOURCEDIR)/modules -maxdepth 2 -name "processes" -type d \
		| xargs rm -rf 2>/dev/null; \
	fi
	@echo "Done."

doc-clean-all: doc-clean-generated
	@echo "WARNING: Removing hand-editable shells (edits will be lost)..."
	rm -rf $(AUTODOC_SOURCEDIR)/modules
	@echo "Done. Run 'make doc-html' to regenerate everything from scratch."

## doc-regs : Generate registers from the register map
doc-regs: $(REGS_OUT_DIR)
	$(PYTHON) $(AUTODOC_REGGEN)

$(REGS_OUT_DIR):
	mkdir -p $(REGS_OUT_DIR)
