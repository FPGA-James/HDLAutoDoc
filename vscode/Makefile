# Build the extension and package it as a .vsix (no publisher account is needed to package).
#   make vsix        -> hdl-autodoc-<version>.vsix in this directory
#   make clean       -> remove build output
# Needs Node and npm; `npm ci` is run when node_modules is missing.
VERSION := $(shell node -p "require('./package.json').version")
SCRIPTS := ../src/scripts/hdl_autodoc

.PHONY: vsix stage-python build clean

node_modules: package.json package-lock.json
	npm ci
	@touch node_modules

build: node_modules
	npm run build

# The Python scripts the extension runs are copied in, so the .vsix needs no installation:
# top-level modules only, no tests and no caches.
stage-python:
	rm -rf python
	mkdir -p python/hdl_autodoc
	cp $(SCRIPTS)/*.py python/hdl_autodoc/

vsix: build stage-python
	rm -f hdl-autodoc-*.vsix
	npx vsce package --no-dependencies --allow-missing-repository --skip-license --out hdl-autodoc-$(VERSION).vsix

clean:
	rm -rf dist python hdl-autodoc-*.vsix
