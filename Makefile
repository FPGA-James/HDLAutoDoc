# Makefile for HDL Sphinx Documentation
SPHINXOPTS   ?=
SPHINXBUILD   = sphinx-build
SOURCEDIR     = docs
BUILDDIR      = docs/_build
SCRIPTDIR     = scripts
SRCDIR        = src
PROJECT       = "test auto"

VHD_FILES    := $(wildcard $(SRCDIR)/*.vhd)
VHD_MODULES  := $(basename $(notdir $(VHD_FILES)))

.PHONY: help install scaffold extract html pdf clean clean-generated clean-all

help:
	@echo ""
	@echo "  make install           Install Python dependencies"
	@echo "  make scaffold          Generate RST shells from VHDL entity names"
	@echo "  make extract           Extract FSM + process docs from VHDL source"
	@echo "  make html              Build HTML documentation"
	@echo "  make pdf               Build PDF documentation"
	@echo "  make clean             Remove Sphinx build output only"
	@echo "  make clean-generated   Remove always-regenerated files"
	@echo "  make clean-all         Remove everything including hand-editable shells"
	@echo ""
	@echo "  Detected VHDL modules: $(VHD_MODULES)"
	@echo ""

install:
	pip install -r requirements.txt

scaffold:
	@echo "Scaffolding RST files from VHDL entities..."
	python $(SCRIPTDIR)/generate_rst.py $(SRCDIR) $(SOURCEDIR) $(PROJECT)

# FSM dot+rst and processes all go directly into docs/modules/<mod>/

extract: scaffold
	@$(foreach mod, $(VHD_MODULES), \
		echo "Extracting: $(mod)..." && \
		python $(SCRIPTDIR)/extract_fsm.py \
			$(SRCDIR)/$(mod).vhd $(mod) $(SOURCEDIR)/modules/$(mod) && \
		python $(SCRIPTDIR)/extract_processes.py \
			$(SRCDIR)/$(mod).vhd $(SOURCEDIR)/modules/$(mod)/processes; \
	)
	@echo "Regenerating timing pages from extracted process diagrams..."
	python $(SCRIPTDIR)/generate_rst.py $(SRCDIR) $(SOURCEDIR) $(PROJECT)

html: extract
	mkdir -p $(SOURCEDIR)/_static $(SOURCEDIR)/_templates
	$(SPHINXBUILD) -M html $(SOURCEDIR) $(BUILDDIR) $(SPHINXOPTS)
	@echo ""
	@echo "Documentation built: $(BUILDDIR)/html/index.html"

pdf: extract
	$(SPHINXBUILD) -M latexpdf $(SOURCEDIR) $(BUILDDIR) $(SPHINXOPTS)

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

clean-generated: clean
	@echo "Removing always-regenerated files..."
	rm -f  $(SOURCEDIR)/index.rst
	rm -f  $(SOURCEDIR)/overview.rst
	@# Remove stale top-level dirs from old structure if present
	rm -rf $(SOURCEDIR)/fsm
	rm -rf $(SOURCEDIR)/processes
	rm -rf $(SOURCEDIR)/timing
	rm -f  $(foreach mod, $(VHD_MODULES), $(SOURCEDIR)/modules/$(mod)/index.rst)
	rm -f  $(foreach mod, $(VHD_MODULES), $(SOURCEDIR)/modules/$(mod)/fsm.rst)
	rm -f  $(foreach mod, $(VHD_MODULES), $(SOURCEDIR)/modules/$(mod)/timing.rst)
	rm -f  $(foreach mod, $(VHD_MODULES), $(SOURCEDIR)/modules/$(mod)/$(mod).dot)
	rm -f  $(foreach mod, $(VHD_MODULES), $(SOURCEDIR)/modules/$(mod)/$(mod).rst)
	rm -rf $(foreach mod, $(VHD_MODULES), $(SOURCEDIR)/modules/$(mod)/processes)
	@echo "Done."

clean-all: clean-generated
	@echo "WARNING: Removing hand-editable shells (edits will be lost)..."
	rm -rf $(SOURCEDIR)/modules
	rm -f  $(SOURCEDIR)/overview.rst
	@echo "Done. Run 'make html' to regenerate everything from scratch."