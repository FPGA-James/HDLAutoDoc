# HDL AutoDoc for VS Code — design

## Intent

Existing HDL AutoDoc users write documentation in comments and read it in the generated Sphinx site.
They want to see what a file will produce **while they are editing it**, without running `make doc-html`.
The extension is a live, per-file preview in the editor. It is a convenience for people who already use
the tool; it does not replace the site and is not aimed at users of other tools.

## Decisions already made

- Audience: existing AutoDoc users who want a preview (not TerosHDL users switching over).
- Python is an acceptable requirement (3.11+, as the tool already needs).
- No publishing for now. The deliverable is a `.vsix` file installed locally (`code --install-extension`).
- TerosHDL's `--!` / `//!` comment style is **not** in v1 (see "Not in v1").

## Goals

1. A command **"HDL AutoDoc: Show documentation"** opens a side panel for the active VHDL or SystemVerilog
   file and keeps it in step with the editor (refresh on save, and on edit after a short pause).
2. The panel shows what the site shows for the module, from the same extractors:
   header description; generics/parameters; ports (grouped as on the site: bus groups, interfaces);
   instances; FSM diagram and transition table; processes with their descriptions, WaveDrom
   waveforms and Mermaid diagrams; clock-domain and reset analysis.
3. Works on unsaved text (the editor buffer is what is documented).
4. Follows the editor theme (light, dark, high contrast).
5. Click a port, generic or process to jump to its line in the source.
6. The `.vsix` is self-contained: no `pip install`, no virtual environment.

## Non-goals

- Publishing to the Marketplace or Open VSX (a later, separate step).
- Rebuilding the Sphinx site inside the editor (a "Build full site" command is a later phase).
- RTL schematics (they need Yosys and netlistsvg); the panel simply omits them.
- Any change to how documentation comments are written, or to the generated site.
- Language-server features (hover, completion, diagnostics) — later, and they would reuse the same JSON.

## Architecture

```
VS Code extension (TypeScript)  --stdin: file text, args: language, name-->  python3 autodoc_json.py
        │                                                                       │
        │  <--stdout: one JSON document--                                       ▼
        ▼                                                          existing extractors (stdlib only)
 webview panel: renders the JSON; bundles wavedrom, mermaid, viz-js (Graphviz as WASM)
```

- **The extractors need only the Python standard library** (checked: no third-party import in
  `src/scripts/hdl_autodoc`). The extension therefore bundles a copy of those scripts inside the `.vsix`
  and runs them with whatever `python3` is on the machine. No packaging of the tool is needed for v1.
- **`autodoc_json.py` is the only new Python file.** It reads source text on stdin and writes one JSON
  document. It calls the same functions the site build calls, so the preview and the site cannot disagree
  about what a file means. It is also the natural data layer for later work (coverage statistics, diagnostics).
- **The webview renders everything locally.** WaveDrom, Mermaid and viz-js are bundled; nothing is fetched
  from a CDN, so it works offline and under VS Code's content-security policy.
- **Plain RST descriptions** (what the comments contain today) are shown as text with simple formatting;
  directives the tool handles (`.. wavedrom::`, `.. mermaid::`) become diagrams. Other directives are shown
  as plain text, which is the one place the preview is allowed to differ from the site.

### JSON contract (outline)

```
{ "language": "vhdl" | "systemverilog",
  "module": { "name", "line", "description" },
  "generics": [ { "name", "type", "default", "description", "line" } ],
  "ports":    [ { "name", "direction", "type", "range", "description", "line", "group" } ],
  "instances":[ { "instance", "component", "line" } ],
  "fsm":      { "states": [...], "transitions": [ { "from", "to", "condition" } ], "dot": "..." } | null,
  "processes":[ { "label", "kind", "line", "sensitivity", "description", "wavedrom": [...], "mermaid": [...] } ],
  "cdc":      { "domains": {...}, "crossings": [...], "dual_clock_instances": [...] } | null,
  "reset":    { "domains": {...}, "crossings": [...] } | null,
  "warnings": [ "..." ] }
```

A file that cannot be parsed returns `warnings` and as much as was found, never an error exit; the panel
shows what it has and lists the warnings.

## What changes in the existing tool

Additive only:

- new `src/scripts/hdl_autodoc/autodoc_json.py` and its tests;
- ports, generics and parameters gain a `line` field (processes already have one) — an extra dict key,
  ignored by every existing consumer;
- a new top-level `vscode/` directory for the extension.

No existing output, make target or variable changes.

## Build and delivery

- `vscode/` is a normal extension project (`package.json`, TypeScript, one webview bundle).
- `make -C vscode vsix` copies `src/scripts/hdl_autodoc` (without `tests/`) into the extension, bundles the
  webview, and runs `vsce package` to produce `hdl-autodoc-<version>.vsix`. `vsce` needs Node and npm at
  build time only; it needs no publisher account to package.
- The extension version tracks the tool version.
- CI builds the `.vsix` on every push and uploads it as a build artifact, so a current file is always
  available without building locally.

## Phases

| Phase | Scope | Effort |
|---|---|---|
| 0 | `autodoc_json.py`, `line` fields, tests | 2–3 days |
| 1 (MVP) | panel for the active file: header, generics, ports, instances, FSM, processes with WaveDrom and Mermaid, CDC, reset; refresh on save and while typing; theming; `.vsix` build in CI | 1.5–2 weeks |
| 2 | click-to-source, outline tree view, project hierarchy view, export of the panel to HTML | 1 week |
| 3 | "Build full site" command (runs `make doc-html`, serves it over http because offline Mermaid does not load from `file://`); undocumented-port warnings in the Problems panel (from the coverage work) | 1 week |

Phases 2 and 3 are not committed to by this document.

## Not in v1: TerosHDL's `--!` / `//!` comment style

Today a `--!` or `//!` line is read as an ordinary comment whose text starts with `!`, so it is not
unsupported-and-silent: the `!` shows up in descriptions. Two levels of support are possible:

- *Prefix only* (treat `--!` / `//!` as `--` / `//` and drop the `!`): about a day in our extractors, but
  VHDL entity headers are read by the third-party sphinx-vhdl, which we do not control, so the site would still
  show the `!` and the preview would differ from it.
- *Markdown content* (TerosHDL comments are Markdown; ours are reStructuredText): about a week and a half,
  and it needs a Markdown path in the Sphinx build.

Neither serves the stated audience, so both are deferred. If TerosHDL users become a target audience this
becomes its own feature of the tool, with the extension following it.

## Risks

- **Parser fidelity.** A live preview exposes every extraction bug at once. Mitigation: the preview and the
  site share the same code, so fixes land in both; the extension's own tests run the extractors against the
  four example projects.
- **Responsiveness.** Each refresh starts a Python process. The extractors are fast on one file (tens of
  milliseconds), but the debounce and a cancel-previous-request rule are required, and a very large file may
  need the debounce lengthened.
- **`python3` not found or too old.** The panel shows a clear message naming the setting
  (`hdlAutodoc.pythonPath`) and the minimum version.
- **Webview bundle size.** Mermaid is large (tens of MB of chunks in the Sphinx offline build); the extension
  must bundle the single-file build and may lazy-load it only when a file contains a diagram.
- **Dark and light themes.** WaveDrom and Graphviz output must use theme colours, not fixed ones.

## Left to the builder

Folder layout of `vscode/`, the webview framework (plain DOM is enough), the exact debounce, the panel's
visual design, test tooling for the extension (the Python side is tested with pytest as today).
