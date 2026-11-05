# HDL AutoDoc for VS Code

A live documentation preview for the VHDL or SystemVerilog file you are editing. It shows what the
[HDL AutoDoc](https://github.com/FPGA-James/HDLAutoDoc) site will show for that module, as you type:

- the header description, generics or parameters, and ports (with bus groups and interface ports),
- instances, the state machine (diagram and transition table),
- every process, with its description, **WaveDrom** waveforms and **Mermaid** diagrams,
- clock-domain and reset analysis (crossings, synchronisers, dual-clock instances).

It uses the same extractors as the site build, so the preview and the generated documentation read your
comments the same way. It works on unsaved text, follows the active editor, follows the editor theme, and
clicking a port, generic, instance or process jumps to its line.

## Use

1. Open a `.vhd`, `.vhdl`, `.sv`, `.svh`, `.v` or `.vh` file.
2. Click the preview icon at the top right of the editor, or run **HDL AutoDoc: Show documentation** from the Command Palette. The panel opens beside the editor.
3. **Export HTML** (top right of the panel, or **HDL AutoDoc: Export documentation as HTML**) saves a standalone page with the diagrams drawn for a white background, whatever theme the panel is in.
4. **Export Markdown** (or **HDL AutoDoc: Export documentation as Markdown**) saves the same documentation as a `.md` file. Diagrams are inserted as their source in fenced `mermaid`, `wavedrom` and `dot` code blocks: GitHub and many editors draw the Mermaid ones, and the others stay readable as code.
5. **Export PDF** (or **HDL AutoDoc: Export documentation as PDF**) prints the same page as the HTML export to an A4 PDF, with tables and diagrams kept whole across page breaks. It needs Chrome, Edge, Brave or Chromium, found in the usual places or named in `hdlAutodoc.browserPath`; without one it offers to save the HTML for you to print from any browser.

The panel refreshes after you stop typing, on save, and when you switch files. Opening a file that is
not HDL leaves the last document in place and says so.

## Requirements

Python 3.11 or newer on your `PATH` (or set `hdlAutodoc.pythonPath`). The extractors use only Python's
standard library, so nothing needs installing, and the extension carries its own copy of them.

## Settings

| Setting | Default | |
|---|---|---|
| `hdlAutodoc.pythonPath` | `python3` | Python 3.11+ used to read the source |
| `hdlAutodoc.refreshDelayMs` | `400` | Pause after the last keystroke before the preview refreshes |
| `hdlAutodoc.browserPath` | *(empty)* | Chrome, Edge, Brave or Chromium used for the PDF export; empty looks in the usual places |

A SystemVerilog file that uses interfaces (`axis_if.slave s_axis`) is documented with those interfaces
when the workspace holds the `interface` definition. Custom port groups are read from
`docs/hdl_autodoc/bus_groups.toml` in the first workspace folder, as the site build does.

## Install the `.vsix`

```bash
code --install-extension hdl-autodoc-<version>.vsix
```

## Build it

From the repository root (needs Node 20 or newer):

```bash
make -C vscode vsix        # writes vscode/hdl-autodoc-<version>.vsix
cd vscode && npm test      # unit tests, the .vsix contents, and the webview in headless Chrome
cd vscode && npm run test:integration   # drives the installed VS Code with a throw-away profile
```

`npm test` renders real documents in headless Chrome (set `CHROME` if it is not found) and writes
screenshots to `test/out/`. The integration tests open a VS Code window briefly; they use their own
user-data and extensions folders and never touch your settings.

## Not included

- RTL schematics (they need Yosys and netlistsvg), the register map, testbenches and build reports:
  those belong to the full site (`make doc-html`).
- Descriptions are shown as plain text with ``code`` spans; other reStructuredText is not rendered.
- A port declaration must be on its own line to be read (`input a, input b,` on one line yields only `a`).
- No publishing to the Marketplace yet; the extension is installed from the `.vsix` file.
