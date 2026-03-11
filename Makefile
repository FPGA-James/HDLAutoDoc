# Makefile for HDL Sphinx Documentation

PYTHON = python3

# Project name — used as the documentation title.
# Defaults to the parent directory name if left blank.
PROJECT        ?= test123

# =============================================================================
# HDL AutoDoc (Sphinx pipeline) variables
# =============================================================================
AUTODOC_SPHINXOPTS    ?=
AUTODOC_SPHINXBUILD    = sphinx-build
AUTODOC_SOURCEDIR      = docs
AUTODOC_BUILDDIR       = docs/_build
AUTODOC_SCRIPTDIR      = scripts/hdl_autodoc
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
AUTODOC_REGGEN     ?= scripts/registers/generate.py


# =============================================================================
# Register generation variables
# =============================================================================
REGS_CONFIG        := registers/config.yml
REGS_REGMAP        := registers/$(PROJECT).yml
REGS_GENERATED_DIR := registers/generated
REGS_OUT_DIR       := registers/out
REGS_PLUGINS       := rggen-vhdl rggen-markdown


.PHONY: help install hierarchy scaffold extract html pdf \
        clean clean-generated clean-all

help:
	@echo ""
	@echo "  make install           Install Python dependencies"
	@echo "  make hierarchy         Parse filelist.f and write hierarchy.json"
	@echo "  make scaffold          Generate RST shells (runs hierarchy first)"
	@echo "  make extract           Extract FSM + process docs (runs scaffold first)"
	@echo "  make html              Build HTML documentation"
	@echo "  make pdf               Build PDF documentation"
	@echo "  make clean             Remove Sphinx build output only"
	@echo "  make clean-generated   Remove always-regenerated files"
	@echo "  make clean-all         Remove everything including hand-editable shells"
	@echo ""

install:
	pip install -r requirements.txt

## ── Step 1: parse filelist.f → hierarchy.json ─────────────────────────────────
hierarchy:
	@echo "Parsing design hierarchy from $(AUTODOC_FILELIST)..."
	python $(AUTODOC_SCRIPTDIR)/parse_hierarchy.py $(AUTODOC_FILELIST) $(AUTODOC_HIERARCHY_JSON)

# ── Step 2: scaffold RST shells from hierarchy ────────────────────────────────
scaffold: hierarchy
	@echo "Scaffolding RST files..."
	python $(AUTODOC_SCRIPTDIR)/generate_rst.py src $(AUTODOC_SOURCEDIR) "$(PROJECT)"

# ── Step 3: extract FSM + processes for every module ─────────────────────────
# run_extract.py reads hierarchy.json — no hardcoded module names here.
extract: scaffold
	python $(AUTODOC_SCRIPTDIR)/run_extract.py \
		$(AUTODOC_HIERARCHY_JSON) $(AUTODOC_SOURCEDIR) $(AUTODOC_SCRIPTDIR)
	@echo "Regenerating timing pages..."
	python $(AUTODOC_SCRIPTDIR)/generate_rst.py src $(AUTODOC_SOURCEDIR) "$(PROJECT)"

# ── Step 4: build HTML ────────────────────────────────────────────────────────
html: extract
	mkdir -p $(AUTODOC_SOURCEDIR)/_static $(AUTODOC_SOURCEDIR)/_templates
	@echo "Checking for register map..."
	python $(AUTODOC_SCRIPTDIR)/include_registers.py . $(AUTODOC_SOURCEDIR)
	$(AUTODOC_SPHINXBUILD) -M html $(AUTODOC_SOURCEDIR) $(AUTODOC_BUILDDIR) $(AUTODOC_SPHINXOPTS)
	@echo ""
	@echo "Documentation built: $(AUTODOC_BUILDDIR)/html/index.html"

# ── PDF build ─────────────────────────────────────────────────────────────────
pdf: extract
	@echo "Checking for register map..."
	python $(AUTODOC_SCRIPTDIR)/include_registers.py . $(AUTODOC_SOURCEDIR)
	$(AUTODOC_SPHINXBUILD) -M latexpdf $(AUTODOC_SOURCEDIR) $(AUTODOC_BUILDDIR) $(AUTODOC_SPHINXOPTS)

# -- make all docs, html and pdf
doc: regs
	$(MAKE) html
	$(MAKE) pdf


# ─────────────────────────────────────────────────────────────────────────────
# Clean targets
#   Tier 1 — Sphinx build output              → make clean
#   Tier 2 — Always-regenerated files         → make clean-generated
#   Tier 3 — Hand-editable scaffolded shells  → make clean-all
# ─────────────────────────────────────────────────────────────────────────────
clean:
	@echo "Removing Sphinx build output..."
	rm -rf $(AUTODOC_BUILDDIR)
	@echo "Done."

clean-generated: clean
	@echo "Removing always-regenerated files..."
	rm -f  $(AUTODOC_HIERARCHY_JSON)
	rm -f  $(AUTODOC_SOURCEDIR)/index.rst
	rm -f  $(AUTODOC_SOURCEDIR)/overview.rst
	rm -f  $(AUTODOC_SOURCEDIR)/hierarchy.rst
	rm -f  $(AUTODOC_SOURCEDIR)/hierarchy.dot
	rm -f  $(AUTODOC_SOURCEDIR)/registers.rst
	rm -rf $(AUTODOC_SOURCEDIR)/_static/registers
	@# Stale top-level dirs from old flat structure
	rm -rf $(AUTODOC_SOURCEDIR)/fsm
	rm -rf $(AUTODOC_SOURCEDIR)/processes
	rm -rf $(AUTODOC_SOURCEDIR)/timing
	@# Per-module always-regenerated files (walk modules/ if it exists)
	@if [ -d $(AUTODOC_SOURCEDIR)/modules ]; then \
		find $(AUTODOC_SOURCEDIR)/modules -maxdepth 2 \
		     -name "index.rst" -o -name "fsm.rst" -o -name "timing.rst" \
		     -o -name "cdc.rst" -o -name "*_cdc.rst" -o -name "*_cdc.dot" \
		     -o -name "*.dot"  -o -name "*.rst" -path "*/processes/*" \
		| xargs rm -f 2>/dev/null; \
		find $(AUTODOC_SOURCEDIR)/modules -maxdepth 2 -name "processes" -type d \
		| xargs rm -rf 2>/dev/null; \
	fi
	@echo "Done."

clean-all: clean-generated
	@echo "WARNING: Removing hand-editable shells (edits will be lost)..."
	rm -rf $(AUTODOC_SOURCEDIR)/modules
	@echo "Done. Run 'make html' to regenerate everything from scratch."

## regs : Generate registers from the register map
regs: $(REGS_OUT_DIR)
	$(PYTHON) scripts/registers/generate.py
# 	rggen --plugin rggen-vhdl -c $(REGS_CONFIG) --output $(REGS_OUT_DIR) $(REGS_REGMAP)
# 	pandoc $(REGS_OUT_DIR)/*.md -o $(REGS_OUT_DIR)/registers.html

$(REGS_OUT_DIR):
	mkdir -p $(REGS_OUT_DIR)
