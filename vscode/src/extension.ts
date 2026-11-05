import * as fs from 'node:fs';
import * as os from 'node:os';
import * as path from 'node:path';
import * as vscode from 'vscode';
import { resetVersionCache, runAutodocJson } from './runner.ts';
import { exportPage } from './export.ts';
import { renderMarkdown } from './markdown.ts';
import { printToPdf, systemBrowser } from './pdf.ts';
import { languageOf, Session } from './session.ts';
import { shellHtml } from './shell.ts';
import type { RunRequest, Snapshot } from './session.ts';
import { SupportFinder } from './support.ts';
import type { Document } from './types.ts';

/** What the integration tests can observe; the webview itself cannot be inspected from here. */
export interface TestApi {
  lastHtml(): string;
  followedUri(): string | undefined;
  hasPanel(): boolean;
  /** True once the webview has loaded its script and said so (proves the CSP and asset URIs work). */
  webviewReady(): boolean;
  handleMessage(message: unknown): Promise<void>;
  /** Save exports here instead of asking (the dialog cannot be driven from a test). */
  exportTo(target: vscode.Uri | undefined): void;
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
  let lastDoc: Document | undefined;
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

  function send(message: { type: 'render'; html: string; doc?: Document }): void {
    lastHtml = message.html;
    if (message.doc) lastDoc = message.doc;
    pending = { type: 'render', html: message.html };           // the webview needs only the HTML
    if (ready) void panel?.webview.postMessage(pending);
  }

  function refreshNow(): void {
    const editor = vscode.window.activeTextEditor;
    if (editor && languageOf(snapshot(editor.document)) !== null) followed = editor.document;
    if (editor) session?.flush(snapshot(editor.document));
  }

  function shell(webview: vscode.Webview, dist: vscode.Uri): string {
    const nonce = Array.from({ length: 24 }, () => Math.floor(Math.random() * 36).toString(36)).join('');
    const asset = (...parts: string[]) => webview.asWebviewUri(vscode.Uri.joinPath(dist, ...parts)).toString();
    return shellHtml({ nonce, cspSource: webview.cspSource, panelCss: asset('panel.css'),
      webviewJs: asset('webview.js'), vendorBase: asset('vendor') });
  }

  let exportTarget: vscode.Uri | undefined;

  const exportName = (): string => followed ? path.basename(followed.fileName, path.extname(followed.fileName)) : 'documentation';

  async function chooseTarget(extension: string, filterName: string): Promise<vscode.Uri | undefined> {
    if (exportTarget) return exportTarget;
    const folder = followed ? path.dirname(followed.fileName) : vscode.workspace.workspaceFolders?.[0]?.uri.fsPath ?? '';
    return vscode.window.showSaveDialog({
      defaultUri: vscode.Uri.file(path.join(folder, `${exportName()}.${extension}`)), filters: { [filterName]: [extension] } });
  }

  function exported(target: vscode.Uri): void {
    void vscode.window.showInformationMessage(`Exported ${target.fsPath}`, 'Open').then((choice) => {
      if (choice === 'Open') void vscode.env.openExternal(target);
    });
  }

  async function saveExport(extension: 'html' | 'md', filterName: string, content: (name: string) => string): Promise<void> {
    const target = await chooseTarget(extension, filterName);
    if (!target) return;
    await vscode.workspace.fs.writeFile(target, Buffer.from(content(exportName()), 'utf8'));
    exported(target);
  }

  const saveHtml = (body: string) => saveExport('html', 'HTML', (name) =>
    exportPage(name, body, fs.readFileSync(path.join(context.extensionPath, 'dist', 'panel.css'), 'utf8')));

  async function savePdf(body: string): Promise<void> {
    const setting = settings().get<string>('browserPath', '').trim() || undefined;
    const browser = systemBrowser(setting);
    if (!browser) {
      const why = setting ? `The browser in hdlAutodoc.browserPath ("${setting}") does not exist.` : 'No Chrome, Edge, Brave or Chromium was found.';
      void vscode.window.showWarningMessage(`${why} Set hdlAutodoc.browserPath, or save the HTML and print it from any browser.`, 'Save HTML instead')
        .then((choice) => { if (choice) void saveHtml(body); });
      return;
    }
    const target = await chooseTarget('pdf', 'PDF');
    if (!target) return;
    const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'hdl-autodoc-pdf-'));
    try {
      const html = path.join(dir, 'page.html');
      fs.writeFileSync(html, exportPage(exportName(), body, fs.readFileSync(path.join(context.extensionPath, 'dist', 'panel.css'), 'utf8')));
      const result = await vscode.window.withProgress({ location: vscode.ProgressLocation.Window, title: 'HDL AutoDoc: exporting PDF…' },
        () => printToPdf({ browser, html, pdf: target.fsPath, timeoutMs: 60000 }));
      if (result.ok) exported(target);
      else void vscode.window.showErrorMessage(`HDL AutoDoc: PDF export failed. ${result.message}`);
    } finally {
      fs.rmSync(dir, { recursive: true, force: true });
    }
  }

  async function saveMarkdown(): Promise<void> {
    if (!lastDoc) {
      void vscode.window.showInformationMessage('HDL AutoDoc: there is no documentation to export yet. Open an HDL file and show the documentation first.');
      return;
    }
    const doc = lastDoc;
    await saveExport('md', 'Markdown', () => renderMarkdown(doc));
  }

  async function handleMessage(message: unknown): Promise<void> {
    const m = message as { type?: string; line?: number; format?: string; html?: string } | undefined;
    if (m?.type === 'ready') {
      ready = true;
      if (pending) void panel?.webview.postMessage(pending);
      refreshNow();
    } else if (m?.type === 'export' && m.format === 'html' && typeof m.html === 'string') {
      await saveHtml(m.html);
    } else if (m?.type === 'export' && m.format === 'pdf' && typeof m.html === 'string') {
      await savePdf(m.html);
    } else if (m?.type === 'export' && m.format === 'markdown') {
      await saveMarkdown();
    } else if (m?.type === 'goto' && typeof m.line === 'number' && followed) {
      const document = followed;
      const column = vscode.window.visibleTextEditors.find((e) => e.document === document)?.viewColumn;
      const editor = await vscode.window.showTextDocument(document, { viewColumn: column, preview: false });
      const position = new vscode.Position(Math.max(0, m.line - 1), 0);
      editor.selection = new vscode.Selection(position, position);
      editor.revealRange(new vscode.Range(position, position), vscode.TextEditorRevealType.InCenterIfOutsideViewport);
    }
  }

  function requestExport(format: string): void {
    if (!panel) openPanel();
    void panel?.webview.postMessage({ type: 'requestExport', format });
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
    vscode.commands.registerCommand('hdlAutodoc.exportMarkdown', () => void saveMarkdown()),
    vscode.commands.registerCommand('hdlAutodoc.exportHtml', () => requestExport('html')),
    vscode.commands.registerCommand('hdlAutodoc.exportPdf', () => requestExport('pdf')),
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
    exportTo: (target) => { exportTarget = target; },
  };
}

export function deactivate(): void {}
