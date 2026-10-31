# Full-feature example — a mixed VHDL / SystemVerilog ECP5 design that exercises every
# feature of HDL AutoDoc.  Every documentation target comes from the shared include;
# run `make doc-help` for the list.  In your own project the path is
# third_party/hdl_autodoc/src/autodoc.mk (see install.sh).
PROJECT ?= ECP5 Sensor Logger

include ../src/autodoc.mk

# ── Build reports (open-source ECP5 flow) ─────────────────────────────────────
# Regenerates reports/yosys/{yosys.log,stat.txt,nextpnr.log}; the committed copies were
# produced by this target.  Needs yosys (with the ghdl plugin) and nextpnr-ecp5 on PATH —
# the OSS CAD Suite provides both.  The documentation build only reads the reports.
#
# Mixed-language flow (verified on a toy design in both directions):
#   * every SystemVerilog file is read with read_verilog -sv;
#   * every VHDL unit that is *not* instantiated by another VHDL unit is elaborated with
#     `ghdl -e <unit>` (ghdl pulls in the VHDL it instantiates), so SystemVerilog can
#     instantiate it and it can instantiate SystemVerilog components;
#   * a SystemVerilog parent cannot pass #(.PARAM()) overrides to a VHDL child — Yosys sees
#     ghdl-elaborated modules as non-parametric; set generics with `ghdl -g<name>=<value>`.
YOSYS   ?= yosys
NEXTPNR ?= nextpnr-ecp5
FILES   := $(shell grep -v '^\#' filelist.f)
SV_SRC  := $(filter %.sv,$(FILES))
VHDL_SRC:= $(filter %.vhd,$(FILES))
TOP     ?= top_not_set_yet
VHDL_ROOTS ?=

.PHONY: ecp5-reports
ecp5-reports:
	mkdir -p reports/yosys build
	$(YOSYS) -m ghdl -q -l reports/yosys/yosys.log -p "read_verilog -sv $(SV_SRC); \
		$(foreach r,$(VHDL_ROOTS),ghdl --std=08 $(VHDL_SRC) -e $(r);) \
		hierarchy -top $(TOP); synth_ecp5 -top $(TOP) -json build/top.json; \
		tee -o reports/yosys/stat.txt stat"
	$(NEXTPNR) --25k --package CABGA256 --json build/top.json --lpf ecp5.lpf \
		--lpf-allow-unconstrained --seed 1 --log reports/yosys/nextpnr.log
