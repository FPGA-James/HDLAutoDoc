# ECP5 example — an AXI4-Stream filter with an AXI4-Lite register file.
# Every documentation target comes from the shared HDL AutoDoc include; run
# `make doc-help` for the list.  In your own project the path is
# third_party/hdl_autodoc/src/autodoc.mk (see install.sh).
PROJECT ?= ECP5 Stream Filter

include ../src/autodoc.mk

# ── Build reports (open-source ECP5 flow) ─────────────────────────────────────
# Regenerates reports/yosys/{yosys.log,stat.txt,nextpnr.log} with Yosys and
# nextpnr-ecp5; the committed copies were produced by this target.  Needs yosys and
# nextpnr-ecp5 on PATH (the OSS CAD Suite provides both).  The documentation build
# only reads the reports, it never runs this flow.
YOSYS   ?= yosys
NEXTPNR ?= nextpnr-ecp5
ECP5_SRC := $(shell grep -v '^\#' filelist.f)

.PHONY: ecp5-reports
ecp5-reports:
	mkdir -p reports/yosys build
	$(YOSYS) -q -l reports/yosys/yosys.log -p "read_verilog -sv $(ECP5_SRC); \
		hierarchy -top top; synth_ecp5 -top top -json build/top.json; \
		tee -o reports/yosys/stat.txt stat"
	$(NEXTPNR) --25k --package CABGA256 --json build/top.json --lpf ecp5.lpf \
		--lpf-allow-unconstrained --seed 1 --log reports/yosys/nextpnr.log
