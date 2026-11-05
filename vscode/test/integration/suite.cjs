// Runs inside the VS Code extension host (see run.mjs).  Each step throws on failure.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vscode = require('vscode');

const workspace = vscode.workspace.workspaceFolders[0].uri.fsPath;
const file = (...parts) => path.join(workspace, ...parts);

let detail = () => '';

async function waitFor(what, predicate, ms = 20000) {
  const end = Date.now() + ms;
  while (Date.now() < end) {
    if (await predicate()) return;
    await new Promise((r) => setTimeout(r, 50));
  }
  throw new Error(`timed out waiting for ${what}; the panel holds: ${detail().slice(0, 500)}`);
}

async function open(p) {
  return vscode.window.showTextDocument(await vscode.workspace.openTextDocument(p), { viewColumn: vscode.ViewColumn.One });
}

exports.run = async function run() {
  const config = vscode.workspace.getConfiguration('hdlAutodoc');
  await config.update('refreshDelayMs', 50, vscode.ConfigurationTarget.Global);

  const extension = vscode.extensions.getExtension('local.hdl-autodoc');
  assert.ok(extension, 'the extension is not installed in the test host');
  const api = await extension.activate();
  detail = () => api.lastHtml();

  // 1. The command opens the panel and documents the active VHDL file.
  const ctrl = await open(file('src', 'sample_ctrl.vhd'));
  await vscode.commands.executeCommand('hdlAutodoc.showDocumentation');
  assert.ok(api.hasPanel());
  await waitFor('the webview to load and report ready', () => api.webviewReady());
  await waitFor('the VHDL document', () => api.lastHtml().includes('sample_ctrl') && api.lastHtml().includes('capture_en'));
  assert.match(api.lastHtml(), /class="fsm"/);
  assert.match(api.lastHtml(), /class="mermaid"/);

  // 2. An unsaved edit is documented, and nothing is written to disk.
  const before = fs.readFileSync(file('src', 'sample_ctrl.vhd'), 'utf8');
  const line = ctrl.document.getText().split('\n').findIndex((l) => l.includes('clk        : in'));
  await ctrl.edit((e) => e.insert(new vscode.Position(line, 0), '        extra_i    : in  std_logic;\n'));
  assert.ok(ctrl.document.isDirty);
  await waitFor('the unsaved port', () => api.lastHtml().includes('extra_i'));
  assert.equal(fs.readFileSync(file('src', 'sample_ctrl.vhd'), 'utf8'), before, 'the file on disk changed');

  // 3. Another file, with the bus groups from docs/hdl_autodoc/bus_groups.toml.
  await open(file('src', 'sample_capture.sv'));
  await waitFor('the SystemVerilog document', () => api.lastHtml().includes('sample_capture') && api.lastHtml().includes('Converter interface'));
  assert.ok(api.followedUri().endsWith('sample_capture.sv'));

  // 4. A file that is not HDL says so and keeps the last document.
  await open(file('README.md'));
  await waitFor('the note', () => api.lastHtml().includes('not a VHDL or SystemVerilog file'));
  assert.match(api.lastHtml(), /sample_capture/);
  assert.ok(api.followedUri().endsWith('sample_capture.sv'), 'the panel should keep following the last HDL file');

  // 5. Clicking a row takes the editor to that line of the followed file.
  await api.handleMessage({ type: 'goto', line: 30 });
  const active = vscode.window.activeTextEditor;
  assert.ok(active.document.uri.fsPath.endsWith('sample_capture.sv'));
  assert.equal(active.selection.active.line, 29);

  // 6. A wrong interpreter is reported with the setting to change, then recovers.
  await config.update('pythonPath', '/no/such/python', vscode.ConfigurationTarget.Global);
  await waitFor('the error', () => api.lastHtml().includes('hdlAutodoc.pythonPath'));
  await config.update('pythonPath', undefined, vscode.ConfigurationTarget.Global);
  await waitFor('recovery', () => !api.lastHtml().includes('message-error') && api.lastHtml().includes('sample_capture'));

  // 7. Closing the panel stops the updates.
  await vscode.commands.executeCommand('workbench.action.closeAllEditors');
  await waitFor('the panel to close', () => !api.hasPanel());
};
