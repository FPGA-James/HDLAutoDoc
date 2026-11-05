import * as fs from 'node:fs';
import * as path from 'node:path';
import * as vscode from 'vscode';
import { resetVersionCache, runAutodocJson } from './runner.ts';
import { languageOf, Session } from './session.ts';
import type { RunRequest, Snapshot } from './session.ts';
import { SupportFinder } from './support.ts';

/** What the integration tests can observe; the webview itself cannot be inspected from here. */
export interface TestApi {
  lastHtml(): string;
  followedUri(): string | undefined;
  hasPanel(): boolean;
  /** True once the webview has loaded its script and said so (proves the CSP and asset URIs work). */
  webviewReady(): boolean;
  handleMessage(message: unknown): Promise<void>;
}

const RUN_TIMEOUT_MS = 15000;

function snapshot(document: vscode.TextDocument): Snapshot {
  return { uri: document.uri.toString(), languageId: document.languageId, text: document.getText() };
}

export function activate(context: vscode.ExtensionContext): TestApi {
  let panel: vscode.WebviewPanel | undefined;
  let session: Session | undefined;
  let followed: vscode.TextDocument | undefined;
  let lastHtml = '';
  let pending: { type: 'render'; html: string } | undefined;
  let ready = false;

  const settings = () => vscode.workspace.getConfiguration('hdlAutodoc');

  // The bundled copy in a packaged extension; the repository's own scripts when run from a checkout.
  const bundled = path.join(context.extensionPath, 'python', 'hdl_autodoc', 'autodoc_json.py');
  const script = fs.existsSync(bundled)
    ? bundled
    : path.join(context.extensionPath, '..', 'src', 'scripts', 'hdl_autodoc', 'autodoc_json.py');

  const support = new SupportFinder({
    list: async () => (await vscode.workspace.findFiles('**/*.{sv,svh}', '**/node_modules/**', 2000)).map((u) => u.fsPath),
    read: (file) => fs.promises.readFile(file, 'utf8'),
    mtime: async (file) => (await fs.promises.stat(file)).mtimeMs,
  });

  function busGroupsFile(): string | undefined {
    const root = vscode.workspace.workspaceFolders?.[0]?.uri.fsPath;
    const file = root ? path.join(root, 'docs', 'hdl_autodoc', 'bus_groups.toml') : undefined;
    return file && fs.existsSync(file) ? file : undefined;
  }

  const run = async (request: RunRequest, signal: AbortSignal) =>
    runAutodocJson({
      python: settings().get<string>('pythonPath', 'python3'),
      script,
      language: request.language,
      text: request.text,
      support: request.language === 'systemverilog' ? await support.find() : [],
      busGroups: busGroupsFile(),
      timeoutMs: RUN_TIMEOUT_MS,
      signal,
    });

  function send(message: { type: 'render'; html: string }): void {
    lastHtml = message.html;
    pending = message;
    if (ready) void panel?.webview.postMessage(message);
  }

  function refreshNow(): void {
    const editor = vscode.window.activeTextEditor;
    if (editor && languageOf(snapshot(editor.document)) !== null) followed = editor.document;
    if (editor) session?.flush(snapshot(editor.document));
  }

  function shell(webview: vscode.Webview, dist: vscode.Uri): string {
    const nonce = Array.from({ length: 24 }, () => Math.floor(Math.random() * 36).toString(36)).join('');
    const asset = (...parts: string[]) => webview.asWebviewUri(vscode.Uri.joinPath(dist, ...parts)).toString();
    const csp = [
      "default-src 'none'",
      'img-src data:',
      `style-src ${webview.cspSource} 'unsafe-inline'`,
      `script-src 'nonce-${nonce}' 'wasm-unsafe-eval'`,
      `font-src ${webview.cspSource}`,
    ].join('; ');
    return `<!doctype html>
<html><head><meta charset="utf-8">
<meta http-equiv="Content-Security-Policy" content="${csp}">
<link rel="stylesheet" href="${asset('panel.css')}">
</head><body data-assets="${asset('vendor')}/">
<div id="content"></div>
<script nonce="${nonce}" src="${asset('webview.js')}"></script>
</body></html>`;
  }

  async function handleMessage(message: unknown): Promise<void> {
    const m = message as { type?: string; line?: number } | undefined;
    if (m?.type === 'ready') {
      ready = true;
      if (pending) void panel?.webview.postMessage(pending);
      refreshNow();
    } else if (m?.type === 'goto' && typeof m.line === 'number' && followed) {
      const document = followed;
      const column = vscode.window.visibleTextEditors.find((e) => e.document === document)?.viewColumn;
      const editor = await vscode.window.showTextDocument(document, { viewColumn: column, preview: false });
      const position = new vscode.Position(Math.max(0, m.line - 1), 0);
      editor.selection = new vscode.Selection(position, position);
      editor.revealRange(new vscode.Range(position, position), vscode.TextEditorRevealType.InCenterIfOutsideViewport);
    }
  }

  function openPanel(): void {
    if (panel) {
      panel.reveal(undefined, true);
      refreshNow();
      return;
    }
    const dist = vscode.Uri.joinPath(context.extensionUri, 'dist');
    panel = vscode.window.createWebviewPanel(
      'hdlAutodoc', 'HDL AutoDoc', { viewColumn: vscode.ViewColumn.Beside, preserveFocus: true },
      { enableScripts: true, localResourceRoots: [dist], retainContextWhenHidden: true });
    ready = false;
    session = new Session({ run, post: send, delayMs: () => settings().get<number>('refreshDelayMs', 400) });
    panel.webview.html = shell(panel.webview, dist);
    panel.webview.onDidReceiveMessage((m) => void handleMessage(m), undefined, context.subscriptions);
    panel.onDidDispose(() => {
      session?.dispose();
      session = undefined;
      panel = undefined;
      ready = false;
    });
    refreshNow();                  // do not wait for the webview: its first message is kept until it is ready
  }

  context.subscriptions.push(
    vscode.commands.registerCommand('hdlAutodoc.showDocumentation', openPanel),
    vscode.window.onDidChangeActiveTextEditor((editor) => {
      if (!panel || !editor) return;                         // focusing the panel itself leaves no editor
      if (languageOf(snapshot(editor.document)) !== null) followed = editor.document;
      session?.flush(snapshot(editor.document));
    }),
    vscode.workspace.onDidChangeTextDocument((event) => {
      if (panel && followed && event.document === followed && event.contentChanges.length > 0) {
        session?.update(snapshot(event.document));
      }
    }),
    vscode.workspace.onDidSaveTextDocument((document) => {
      if (panel && followed && document === followed) session?.flush(snapshot(document));
    }),
    vscode.workspace.onDidChangeConfiguration((event) => {
      if (!event.affectsConfiguration('hdlAutodoc')) return;
      resetVersionCache();
      if (panel) refreshNow();
    }),
    { dispose: () => { session?.dispose(); } },
  );

  return {
    lastHtml: () => lastHtml,
    followedUri: () => followed?.uri.toString(),
    hasPanel: () => panel !== undefined,
    webviewReady: () => ready,
    handleMessage,
  };
}

export function deactivate(): void {}
