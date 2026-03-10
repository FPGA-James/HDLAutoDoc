# Makefile for HDL Sphinx Documentation

PYTHON = python3

# Project name — used as the documentation title.
# Defaults to the parent directory name if left blank.
PROJECT        ?= test123

# =============================================================================
# HDL_AUTODOC Generation Make Variables
# =============================================================================
SPHINXOPTS    ?=
SPHINXBUILD    = sphinx-build
SOURCEDIR      = docs
BUILDDIR       = docs/_build
SCRIPTDIR      = scripts
FILELIST       = filelist.f
HIERARCHY_JSON = $(SOURCEDIR)/hierarchy.json
# Entry point filename for the register map HTML output.
# Override to match your register tool's output filename.
# Examples:
#   make doc REG_ENTRY=index.html            (Questa Register Assistant)
#   make doc REG_ENTRY=counter_regs.html     (custom generator)
#   make doc REG_ENTRY=regmap.html           (other tools)
# Leave blank to auto-detect (picks index.html or first .html found).
REG_ENTRY  ?= counter_regs.html

# ── Register generation + full doc build ─────────────────────────────────────
# Runs the register generator first, then the full Sphinx pipeline.
# Set REGGEN to your register generation script path if different.
REGGEN     ?= scripts/registers/generate.py


# =============================================================================
# RgGen Register Generation Makefile
# =============================================================================
CONFIG   := registers/config.yml
REGMAP   := registers/$(PROJECT).yml
REG_OUT_DIR  := registers/generated
OUT_DIR  := registers/out
PLUGINS  := rggen-vhdl rggen-markdown


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
	@echo "Parsing design hierarchy from $(FILELIST)..."
	python $(SCRIPTDIR)/parse_hierarchy.py $(FILELIST) $(HIERARCHY_JSON)

# ── Step 2: scaffold RST shells from hierarchy ────────────────────────────────
scaffold: hierarchy
	@echo "Scaffolding RST files..."
	python $(SCRIPTDIR)/generate_rst.py src $(SOURCEDIR) "$(PROJECT)"

# ── Step 3: extract FSM + processes for every module ─────────────────────────
# run_extract.py reads hierarchy.json — no hardcoded module names here.
extract: scaffold
	python $(SCRIPTDIR)/run_extract.py \
		$(HIERARCHY_JSON) $(SOURCEDIR) $(SCRIPTDIR)
	@echo "Regenerating timing pages..."
	python $(SCRIPTDIR)/generate_rst.py src $(SOURCEDIR) "$(PROJECT)"

# ── Step 4: build HTML ────────────────────────────────────────────────────────
html: extract
	mkdir -p $(SOURCEDIR)/_static $(SOURCEDIR)/_templates
	@echo "Checking for register map..."
	python $(SCRIPTDIR)/include_registers.py . $(SOURCEDIR)
	$(SPHINXBUILD) -M html $(SOURCEDIR) $(BUILDDIR) $(SPHINXOPTS)
	@echo ""
	@echo "Documentation built: $(BUILDDIR)/html/index.html"

# ── PDF build ─────────────────────────────────────────────────────────────────
pdf: extract
	@echo "Checking for register map..."
	python $(SCRIPTDIR)/include_registers.py . $(SOURCEDIR)
	$(SPHINXBUILD) -M latexpdf $(SOURCEDIR) $(BUILDDIR) $(SPHINXOPTS)

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
	rm -rf $(BUILDDIR)
	@echo "Done."

cclean-generated: clean
	@echo "Removing always-regenerated files..."
	rm -f  $(HIERARCHY_JSON)
	rm -f  $(SOURCEDIR)/index.rst
	rm -f  $(SOURCEDIR)/overview.rst
	rm -f  $(SOURCEDIR)/hierarchy.rst
	rm -f  $(SOURCEDIR)/hierarchy.dot
	rm -f  $(SOURCEDIR)/registers.rst
	rm -rf $(SOURCEDIR)/_static/registers
	@# Stale top-level dirs from old flat structure
	rm -rf $(SOURCEDIR)/fsm
	rm -rf $(SOURCEDIR)/processes
	rm -rf $(SOURCEDIR)/timing
	@# Per-module always-regenerated files (walk modules/ if it exists)
	@if [ -d $(SOURCEDIR)/modules ]; then \
		find $(SOURCEDIR)/modules -maxdepth 2 \
		     -name "index.rst" -o -name "fsm.rst" -o -name "timing.rst" \
		     -o -name "*.dot"  -o -name "*.rst" -path "*/processes/*" \
		| xargs rm -f 2>/dev/null; \
		find $(SOURCEDIR)/modules -maxdepth 2 -name "processes" -type d \
		| xargs rm -rf 2>/dev/null; \
	fi
	@echo "Done."

clean-all: clean-generated
	@echo "WARNING: Removing hand-editable shells (edits will be lost)..."
	rm -rf $(SOURCEDIR)/modules
	@echo "Done. Run 'make html' to regenerate everything from scratch."

## regs : Generate registers from the register map
regs: $(OUT_DIR)
	$(PYTHON) scripts/registers/generate.py
# 	rggen --plugin rggen-vhdl -c $(CONFIG) --output $(OUT_DIR) $(REGMAP)
# 	pandoc $(OUT_DIR)/*.md -o $(OUT_DIR)/registers.html

$(OUT_DIR):
	mkdir -p $(OUT_DIR)